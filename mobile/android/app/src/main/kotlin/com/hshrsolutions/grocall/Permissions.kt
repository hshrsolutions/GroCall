package com.hshrsolutions.grocall

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Environment
import android.os.PowerManager
import android.provider.Settings
import org.json.JSONObject

object Permissions {
    /** Runtime permissions by the names the Flutter side uses. */
    fun runtime(name: String): List<String> = when (name) {
        "call_log" -> listOf(Manifest.permission.READ_CALL_LOG)
        "phone" -> listOf(Manifest.permission.READ_PHONE_STATE) +
            (if (Build.VERSION.SDK_INT >= 26) listOf(Manifest.permission.READ_PHONE_NUMBERS) else emptyList())
        "notifications" -> if (Build.VERSION.SDK_INT >= 33) listOf(Manifest.permission.POST_NOTIFICATIONS) else emptyList()
        "audio" -> if (Build.VERSION.SDK_INT >= 33) listOf(Manifest.permission.READ_MEDIA_AUDIO)
            else listOf(Manifest.permission.READ_EXTERNAL_STORAGE)
        "microphone" -> listOf(Manifest.permission.RECORD_AUDIO)
        else -> emptyList()
    }

    private fun granted(ctx: Context, perms: List<String>) =
        perms.all { ctx.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }

    fun status(ctx: Context): JSONObject {
        val o = JSONObject()
        for (n in listOf("call_log", "phone", "notifications", "audio", "microphone")) o.put(n, granted(ctx, runtime(n)))
        o.put("all_files", Build.VERSION.SDK_INT >= 30 && Environment.isExternalStorageManager())
        o.put("battery", ctx.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(ctx.packageName))
        o.put("accessibility", accessibilityOn(ctx))
        return o
    }

    fun accessibilityOn(ctx: Context): Boolean {
        val enabled = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        val me = ComponentName(ctx, FallbackRecorderService::class.java).flattenToString()
        return enabled.split(':').any { it.equals(me, ignoreCase = true) }
    }
}
