package com.hshrsolutions.grocall

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager

/** A call just ended: sync a few seconds later (the dialer writes the call log and the recorder
 *  finishes its file after hang-up). Also drives the optional Tier-B fallback recorder. */
class CallStateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return
        val store = Store(context)
        if (!store.isPaired) return
        when (intent.getStringExtra(TelephonyManager.EXTRA_STATE)) {
            TelephonyManager.EXTRA_STATE_OFFHOOK -> if (store.fallbackRecorder) FallbackRecorderService.start()
            TelephonyManager.EXTRA_STATE_IDLE -> {
                if (store.fallbackRecorder) FallbackRecorderService.stop()
                SyncWorker.now(context, 8000)
            }
        }
    }
}

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Store(context).isPaired) SyncWorker.schedule(context)
    }
}
