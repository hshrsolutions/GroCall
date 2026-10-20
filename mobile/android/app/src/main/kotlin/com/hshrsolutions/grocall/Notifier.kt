package com.hshrsolutions.grocall

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

object Notifier {
    private const val AFTER_CALL = "after_call"
    private const val MISSED = "missed"

    fun channels(context: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(AFTER_CALL, "After a call", NotificationManager.IMPORTANCE_HIGH)
            .apply { description = "Asks for the outcome of a company-SIM call" })
        nm.createNotificationChannel(NotificationChannel(MISSED, "Missed calls", NotificationManager.IMPORTANCE_HIGH)
            .apply { description = "Missed company-SIM calls to return" })
    }

    private fun allowed(context: Context) = Build.VERSION.SDK_INT < 33 ||
        context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun open(context: Context, localId: Long): PendingIntent {
        val i = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("open_call", localId)
        }
        return PendingIntent.getActivity(context, localId.toInt(), i, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    fun afterCall(context: Context, localId: Long, who: String, durationSec: Int) {
        if (!allowed(context)) return
        channels(context)
        val n = NotificationCompat.Builder(context, AFTER_CALL)
            .setSmallIcon(android.R.drawable.sym_action_call)
            .setContentTitle("How did the call go?")
            .setContentText("$who · ${fmt(durationSec)} — tap to add the outcome")
            .setContentIntent(open(context, localId))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        try { NotificationManagerCompat.from(context).notify(localId.toInt(), n) } catch (e: SecurityException) { }
    }

    fun missed(context: Context, localId: Long, who: String) {
        if (!allowed(context)) return
        channels(context)
        val n = NotificationCompat.Builder(context, MISSED)
            .setSmallIcon(android.R.drawable.sym_call_missed)
            .setContentTitle("Missed call — call back")
            .setContentText(who)
            .setContentIntent(open(context, localId))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        try { NotificationManagerCompat.from(context).notify(100000 + localId.toInt(), n) } catch (e: SecurityException) { }
    }

    fun fmt(sec: Int) = if (sec < 60) "${sec}s" else "${sec / 60}m ${sec % 60}s"
}
