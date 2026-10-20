package com.hshrsolutions.grocall

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import org.json.JSONArray
import java.io.File
import java.io.InputStream
import kotlin.math.abs

/** Finds the built-in recorder's file for a call, using the server's recorder profiles. */
object Recordings {
    data class Found(val name: String, val size: Long, val modified: Long, val ext: String, val open: () -> InputStream?)

    private val EXTS = setOf("m4a", "mp4", "aac", "mp3", "amr", "awb", "3gp", "wav", "ogg", "opus", "flac", "webm")

    /** Folders for this phone: the profile whose brands include the manufacturer, then the generic ones. */
    fun folders(profiles: JSONArray?): List<String> {
        val maker = Build.MANUFACTURER.lowercase()
        val mine = mutableListOf<String>(); val generic = mutableListOf<String>()
        if (profiles != null) for (i in 0 until profiles.length()) {
            val p = profiles.getJSONObject(i)
            val brands = p.optJSONArray("brands") ?: JSONArray()
            val fs = p.optJSONArray("folders") ?: JSONArray()
            val target = if (brands.length() == 0) generic else if ((0 until brands.length()).any {
                    maker.contains(brands.getString(it)) }) mine else null
            target?.let { for (j in 0 until fs.length()) it.add(fs.getString(j).trim('/')) }
        }
        return (mine + generic).distinct()
    }

    /** Best file for a call that started at `start` (ms) and lasted `durationSec`; null if none. */
    fun find(context: Context, start: Long, durationSec: Int, number: String, profiles: JSONArray?, taken: Set<String>): Found? {
        val from = start - 60_000L
        val to = start + durationSec * 1000L + 180_000L
        val digits = CallLogReader.last10(number).takeLast(7)
        val candidates = mutableListOf<Found>()
        val dirs = folders(profiles)

        // 1. Our own fallback recorder (Tier B), if it made a file.
        File(context.getExternalFilesDir(null), "fallback").listFiles()?.forEach { f -> add(candidates, f, from, to, taken) }
        // 2. All-files access: walk the profile folders directly (also sees .nomedia folders).
        if (Build.VERSION.SDK_INT >= 30 && Environment.isExternalStorageManager()) {
            val root = Environment.getExternalStorageDirectory()
            dirs.forEach { d -> File(root, d).listFiles()?.forEach { f -> add(candidates, f, from, to, taken) } }
        }
        // 3. MediaStore audio (READ_MEDIA_AUDIO / READ_EXTERNAL_STORAGE).
        if (candidates.isEmpty()) candidates.addAll(mediaStore(context, from, to, dirs, taken))

        return candidates.minByOrNull { f ->
            val bonus = if (digits.length >= 7 && f.name.filter { it.isDigit() }.contains(digits)) -600_000L else 0L
            abs(f.modified - (start + durationSec * 1000L)) + bonus
        }
    }

    private fun add(out: MutableList<Found>, f: File, from: Long, to: Long, taken: Set<String>) {
        val ext = f.extension.lowercase()
        if (!f.isFile || ext !in EXTS || f.length() == 0L || f.absolutePath in taken) return
        if (f.lastModified() in from..to) out.add(Found(f.absolutePath, f.length(), f.lastModified(), ext) { f.inputStream() })
    }

    private fun mediaStore(context: Context, from: Long, to: Long, dirs: List<String>, taken: Set<String>): List<Found> {
        val out = mutableListOf<Found>()
        val uri: Uri = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val pathCol = if (Build.VERSION.SDK_INT >= 29) MediaStore.MediaColumns.RELATIVE_PATH else MediaStore.MediaColumns.DATA
        val cols = arrayOf(MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.SIZE,
            MediaStore.MediaColumns.DATE_MODIFIED, pathCol)
        try {
            context.contentResolver.query(uri, cols, "${MediaStore.MediaColumns.DATE_MODIFIED} BETWEEN ? AND ?",
                arrayOf((from / 1000).toString(), (to / 1000).toString()), null)?.use { c ->
                while (c.moveToNext()) {
                    val id = c.getLong(0); val name = c.getString(1) ?: continue
                    val path = (c.getString(4) ?: "").trim('/')
                    val ext = name.substringAfterLast('.', "").lowercase()
                    if (ext !in EXTS) continue
                    val inFolder = dirs.any { path.contains(it, ignoreCase = true) } ||
                        path.contains("call", ignoreCase = true) || path.contains("record", ignoreCase = true)
                    val item = ContentUris.withAppendedId(uri, id)
                    if (!inFolder || item.toString() in taken) continue
                    out.add(Found(item.toString(), c.getLong(2), c.getLong(3) * 1000L, ext) {
                        context.contentResolver.openInputStream(item) })
                }
            }
        } catch (e: SecurityException) { }
        return out
    }

    /** For the diagnostics screen: which folders exist on this phone and how many audio files they hold. */
    fun probe(profiles: JSONArray?): JSONArray {
        val out = JSONArray()
        val root = Environment.getExternalStorageDirectory()
        val canList = Build.VERSION.SDK_INT >= 30 && Environment.isExternalStorageManager()
        for (d in folders(profiles)) {
            val f = File(root, d)
            out.put(org.json.JSONObject().apply {
                put("folder", d); put("exists", if (canList) f.isDirectory else org.json.JSONObject.NULL)
                put("files", if (canList) (f.listFiles()?.count { it.extension.lowercase() in EXTS } ?: 0) else -1)
            })
        }
        return out
    }
}
