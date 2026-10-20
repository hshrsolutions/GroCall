package com.hshrsolutions.grocall

import android.accessibilityservice.AccessibilityService
import android.media.MediaRecorder
import android.os.Build
import android.view.accessibility.AccessibilityEvent
import java.io.File

/** Tier B only, opt-in, best effort (grocall-prd.md §2.2). Phones on the Google Phone dialer keep
 *  their recordings private, so this records the microphone during a call from inside an
 *  accessibility service (the only context Android lets record during a call). It usually
 *  captures the salesperson clearly and the customer faintly unless the speaker is on. */
class FallbackRecorderService : AccessibilityService() {
    private var recorder: MediaRecorder? = null

    override fun onServiceConnected() { instance = this }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}
    override fun onDestroy() { stopRec(); instance = null; super.onDestroy() }

    private fun startRec() {
        if (recorder != null) return
        val dir = File(getExternalFilesDir(null), "fallback").apply { mkdirs() }
        val file = File(dir, "call_${System.currentTimeMillis()}.m4a")
        val r = if (Build.VERSION.SDK_INT >= 31) MediaRecorder(this) else @Suppress("DEPRECATION") MediaRecorder()
        try {
            r.setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
            r.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            r.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            r.setAudioEncodingBitRate(64000)
            r.setAudioSamplingRate(22050)
            r.setOutputFile(file.absolutePath)
            r.prepare(); r.start()
            recorder = r
        } catch (e: Exception) { r.release(); file.delete() }
    }

    private fun stopRec() {
        recorder?.let { try { it.stop() } catch (e: Exception) { }; it.release() }
        recorder = null
    }

    companion object {
        @Volatile private var instance: FallbackRecorderService? = null
        val running: Boolean get() = instance != null
        fun start() { instance?.startRec() }
        fun stop() { instance?.stopRec() }
    }
}
