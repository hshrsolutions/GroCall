package com.hshrsolutions.grocall

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/** The whole phone → server loop: call log → sync → pull → recordings → heartbeat.
 *  Runs right after each call (CallStateReceiver) and every 15 minutes. */
class SyncWorker(context: Context, params: WorkerParameters) : Worker(context, params) {

    override fun doWork(): Result {
        val ctx = applicationContext
        val store = Store(ctx)
        if (!store.isPaired) return Result.success()
        val api = Api(store)
        val db = LocalDb(ctx)
        return try {
            readCallLog(ctx, store, db)
            sendPending(ctx, store, api, db)
            pull(store, api)
            uploadRecordings(ctx, store, api, db)
            heartbeat(ctx, store, api)
            store.lastSync = System.currentTimeMillis()
            store.lastError = null
            Result.success()
        } catch (e: ApiException) {
            store.lastError = if (e.status == 401) "unpaired: ${e.message}" else e.message
            Result.success()  // a server-side refusal will not fix itself by retrying now
        } catch (e: IOException) {
            store.lastError = "offline: ${e.message}"
            Result.retry()
        } catch (e: Exception) {
            store.lastError = e.toString()
            Result.success()
        }
    }

    private fun excluded(store: Store): Set<String> {
        val arr = store.cache().optJSONArray("excluded_numbers") ?: JSONArray()
        return (0 until arr.length()).map { CallLogReader.last10(arr.getString(it)) }.toSet()
    }

    private fun readCallLog(ctx: Context, store: Store, db: LocalDb) {
        // Re-read the last 10 minutes each time: some phones write the call-log row late.
        val since = maxOf(store.watermark - 600_000L, store.pairedAt)
        var max = store.watermark
        for (r in CallLogReader.read(ctx, since, store.simSubId!!, excluded(store))) {
            db.insert(r.number, r.direction, r.startedAt, r.duration)
            if (r.startedAt > max) max = r.startedAt
        }
        store.watermark = max
    }

    private fun sendPending(ctx: Context, store: Store, api: Api, db: LocalDb) {
        val rows = db.query("sync_state = 'pending'", null, 200, asc = true)
        if (rows.isEmpty()) return
        val calls = JSONArray()
        for (r in rows) calls.put(JSONObject().apply {
            put("ref", r.getLong("id").toString()); put("direction", r.getString("direction"))
            put("number", r.optString("number")); put("started_at", r.getLong("started_at"))
            put("duration_sec", r.getLong("duration")); put("sim_subscription_id", store.simSubId)
        })
        val res = api.post("sync", JSONObject().put("app_version", BuildConfig.VERSION_NAME).put("calls", calls))
        val results = res.optJSONArray("results") ?: JSONArray()
        val byId = rows.associateBy { it.getLong("id") }
        val recent = System.currentTimeMillis() - 2 * 3600_000L
        for (i in 0 until results.length()) {
            val x = results.getJSONObject(i)
            val id = x.optString("ref").toLongOrNull() ?: continue
            val row = byId[id] ?: continue
            when (x.optString("status")) {
                "created", "duplicate" -> {
                    val lead = x.optString("lead_name").takeIf { it.isNotEmpty() && it != "null" }
                    db.update(id, mapOf("sync_state" to "sent", "call" to x.optString("call"),
                        "call_key" to x.optString("call_key"), "lead_name" to lead,
                        "rec_state" to if (x.optBoolean("upload")) "wanted" else "none"))
                    val started = row.getLong("started_at")
                    if (x.optString("status") == "created" && started > recent && row.optLong("notified") == 0L) {
                        val who = lead ?: row.optString("number")
                        val dir = row.getString("direction")
                        if (dir == "missed") Notifier.missed(ctx, id, who)
                        else if (row.getLong("duration") > 0) Notifier.afterCall(ctx, id, who, row.getLong("duration").toInt())
                        db.update(id, mapOf("notified" to 1))
                    }
                }
                "excluded" -> db.update(id, mapOf("sync_state" to "excluded"))
                else -> db.update(id, mapOf("rec_error" to x.optString("message")))
            }
        }
    }

    private fun pull(store: Store, api: Api) {
        store.pullCache = api.post("pull", JSONObject()).toString()
    }

    private fun uploadRecordings(ctx: Context, store: Store, api: Api, db: LocalDb) {
        val profiles = store.cache().optJSONArray("recorder_profiles")
        val taken = db.query("rec_state = 'done'", null, 500).mapNotNull { it.optString("rec_path").takeIf { p -> p.isNotEmpty() } }.toMutableSet()
        val tierB = Sims.tier(ctx) == "B"
        for (row in db.query("sync_state = 'sent' AND rec_state IN ('wanted', 'uploading')", null, 20, asc = true)) {
            val id = row.getLong("id")
            val start = row.getLong("started_at"); val dur = row.getLong("duration").toInt()
            val ended = start + dur * 1000L
            val age = System.currentTimeMillis() - ended
            if (age > 7 * 86400_000L) { db.update(id, mapOf("rec_state" to "missing")); continue }
            val found = Recordings.find(ctx, start, dur, row.optString("number"), profiles, taken)
            if (found == null) {
                if (age > 30 * 60_000L) {
                    val reason = if (tierB && !store.fallbackRecorder) "not_available" else "not_found"
                    api.post("recording_missing", JSONObject().put("call_key", row.getString("call_key")).put("reason", reason))
                    db.update(id, mapOf("rec_state" to "missing", "rec_error" to reason))
                }
                continue
            }
            db.update(id, mapOf("rec_state" to "uploading", "rec_path" to found.name))
            upload(api, row.getString("call_key"), found, dur)
            db.update(id, mapOf("rec_state" to "done", "rec_error" to null))
            taken.add(found.name)
        }
    }

    private fun upload(api: Api, callKey: String, f: Recordings.Found, dur: Int) {
        val sha = sha256(f.open() ?: throw IOException("cannot open ${f.name}"))
        var offset = api.post("upload_status", JSONObject().put("call_key", callKey)).optLong("received", 0L)
        val buf = ByteArray(CHUNK)
        var stream = f.open() ?: throw IOException("cannot open ${f.name}")
        try {
            skipFully(stream, offset)
            while (offset < f.size) {
                val n = readFully(stream, buf)
                if (n <= 0) break
                val r = api.uploadChunk(callKey, offset, f.size, sha, f.ext, dur, buf, n)
                when (r.optString("status")) {
                    "complete" -> return
                    "resume" -> {  // server is elsewhere (an earlier attempt half-arrived): reopen and seek
                        offset = r.optLong("received"); stream.close()
                        stream = f.open() ?: throw IOException("cannot reopen ${f.name}"); skipFully(stream, offset)
                    }
                    else -> offset = r.optLong("received", offset + n)
                }
            }
        } finally { stream.close() }
    }

    private fun heartbeat(ctx: Context, store: Store, api: Api) {
        val p = Permissions.status(ctx)
        api.post("heartbeat", JSONObject().put("permissions", p).put("app_version", BuildConfig.VERSION_NAME)
            .put("support_tier", Sims.tier(ctx)).put("fallback_recorder", if (store.fallbackRecorder) 1 else 0))
    }

    companion object {
        const val CHUNK = 1024 * 1024
        private const val PERIODIC = "grocall-periodic"
        private const val NOW = "grocall-now"

        private val net = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

        fun schedule(ctx: Context) {
            val req = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES).setConstraints(net).build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP, req)
        }

        fun now(ctx: Context, delayMs: Long = 0) {
            val req = OneTimeWorkRequestBuilder<SyncWorker>().setConstraints(net)
                .setInitialDelay(delayMs, TimeUnit.MILLISECONDS).build()
            WorkManager.getInstance(ctx).enqueueUniqueWork(NOW, ExistingWorkPolicy.REPLACE, req)
        }

        fun cancel(ctx: Context) = WorkManager.getInstance(ctx).cancelAllWork()

        fun sha256(input: InputStream): String = input.use { s ->
            val md = MessageDigest.getInstance("SHA-256"); val b = ByteArray(65536)
            while (true) { val n = s.read(b); if (n < 0) break; md.update(b, 0, n) }
            md.digest().joinToString("") { "%02x".format(it) }
        }

        fun readFully(s: InputStream, buf: ByteArray): Int {
            var total = 0
            while (total < buf.size) { val n = s.read(buf, total, buf.size - total); if (n < 0) break; total += n }
            return total
        }

        fun skipFully(s: InputStream, n: Long) {
            var left = n
            while (left > 0) {
                val k = s.skip(left)
                if (k <= 0) { if (s.read() < 0) break; left -= 1 } else left -= k
            }
        }
    }
}
