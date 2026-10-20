package com.hshrsolutions.grocall

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject

/** Bridge for the Flutter UI ("grocall/native"). All phone-level work lives in Kotlin so it also
 *  runs in the background without the Flutter engine. */
class MainActivity : FlutterActivity() {
    private lateinit var channel: MethodChannel
    private var pendingPerm: MethodChannel.Result? = null
    private var launchCall: Long = -1

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        Notifier.channels(this)
        launchCall = intent?.getLongExtra("open_call", -1L) ?: -1L
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "grocall/native")
        channel.setMethodCallHandler { call, result ->
            try { handle(call, result) } catch (e: Exception) { result.error("native", e.message, null) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        val id = intent.getLongExtra("open_call", -1L)
        if (id > 0 && ::channel.isInitialized) channel.invokeMethod("openCall", id)
    }

    private fun handle(call: MethodCall, result: MethodChannel.Result) {
        val store = Store(this)
        val db = LocalDb(this)
        when (call.method) {
            "state" -> result.success(JSONObject().apply {
                put("paired", store.isPaired); put("site", store.site); put("device", store.device)
                put("user", store.user); put("full_name", store.fullName); put("sim_sub_id", store.simSubId)
                put("sim_label", store.simLabel); put("last_sync", store.lastSync); put("last_error", store.lastError)
                put("tier", Sims.tier(this@MainActivity)); put("dialer", Sims.dialer(this@MainActivity))
                put("fallback", store.fallbackRecorder); put("fallback_running", FallbackRecorderService.running)
                put("version", BuildConfig.VERSION_NAME)
            }.toString())
            "deviceInfo" -> result.success(JSONObject().apply {
                put("device_uuid", Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID))
                put("brand", Build.MANUFACTURER.lowercase()); put("model", Build.MODEL)
                put("os_version", Build.VERSION.RELEASE); put("app_version", BuildConfig.VERSION_NAME)
                put("support_tier", Sims.tier(this@MainActivity))
            }.toString())
            "sims" -> result.success(Sims.list(this).toString())
            "savePairing" -> {
                store.site = call.argument<String>("site"); store.device = call.argument<String>("device")
                store.key = call.argument<String>("key"); store.user = call.argument<String>("user")
                store.fullName = call.argument<String>("full_name"); store.simSubId = call.argument<String>("sim_sub_id")
                store.simLabel = call.argument<String>("sim_label")
                call.argument<String>("cache")?.let { store.pullCache = it }
                val now = System.currentTimeMillis()
                store.pairedAt = now; store.watermark = now  // only calls after pairing (and consent) are tracked
                SyncWorker.schedule(this); SyncWorker.now(this)
                result.success(true)
            }
            "credentials" -> result.success(JSONObject().apply {
                put("site", store.site); put("device", store.device); put("key", store.key)
            }.toString())
            "unpair" -> { SyncWorker.cancel(this); store.clear(); db.clear(); result.success(true) }
            "syncNow" -> { SyncWorker.now(this); result.success(true) }
            "cache" -> result.success(store.pullCache)
            "calls" -> result.success(db.recentJson(call.argument<Int>("limit") ?: 200))
            "setOutcome" -> {
                db.update((call.argument<Number>("id") ?: 0).toLong(), mapOf("outcome" to call.argument<String>("outcome")))
                result.success(true)
            }
            "launchCall" -> { result.success(launchCall); launchCall = -1 }
            "permissions" -> result.success(Permissions.status(this).toString())
            "requestPermission" -> {
                val perms = Permissions.runtime(call.argument<String>("name") ?: "")
                if (perms.isEmpty()) { result.success(true); return }
                pendingPerm = result
                requestPermissions(perms.toTypedArray(), 4711)
            }
            "openSettings" -> { openSettings(call.argument<String>("kind") ?: "app"); result.success(true) }
            "setFallback" -> { store.fallbackRecorder = call.argument<Boolean>("on") == true; result.success(true) }
            "probe" -> result.success(Recordings.probe(store.cache().optJSONArray("recorder_profiles")).toString())
            "dial" -> {
                startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + (call.argument<String>("number") ?: ""))))
                result.success(true)
            }
            "openDialer" -> {
                val pkg = Sims.dialer(this)
                packageManager.getLaunchIntentForPackage(pkg)?.let { startActivity(it) }
                result.success(pkg)
            }
            else -> result.notImplemented()
        }
    }

    private fun openSettings(kind: String) {
        val pkg = Uri.parse("package:$packageName")
        val i = when (kind) {
            "all_files" -> if (Build.VERSION.SDK_INT >= 30)
                Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, pkg) else Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, pkg)
            "battery" -> Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, pkg)
            "accessibility" -> Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            else -> Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, pkg)
        }
        try { startActivity(i) } catch (e: Exception) { startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, pkg)) }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 4711) {
            pendingPerm?.success(grantResults.isNotEmpty() && grantResults.all { it == android.content.pm.PackageManager.PERMISSION_GRANTED })
            pendingPerm = null
        }
    }
}
