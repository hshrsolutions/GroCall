package com.hshrsolutions.grocall

import android.content.Context
import android.provider.CallLog

/** Reads new call-log rows and keeps only those on the company SIM, minus excluded numbers. */
object CallLogReader {
    data class Row(val number: String, val direction: String, val startedAt: Long, val duration: Int)

    fun direction(type: Int): String? = when (type) {
        CallLog.Calls.INCOMING_TYPE -> "incoming"
        CallLog.Calls.OUTGOING_TYPE -> "outgoing"
        CallLog.Calls.MISSED_TYPE -> "missed"
        CallLog.Calls.REJECTED_TYPE -> "rejected"
        CallLog.Calls.BLOCKED_TYPE -> "blocked"
        else -> null  // voicemail, answered elsewhere: not a sales call on this phone
    }

    fun read(context: Context, since: Long, companySub: String, excludedLast10: Set<String>): List<Row> {
        val accounts = Sims.accountMap(context)
        val out = mutableListOf<Row>()
        val cols = arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION,
            CallLog.Calls.PHONE_ACCOUNT_ID)
        context.contentResolver.query(CallLog.Calls.CONTENT_URI, cols, "${CallLog.Calls.DATE} > ?",
            arrayOf(since.toString()), "${CallLog.Calls.DATE} ASC")?.use { c ->
            while (c.moveToNext()) {
                val number = c.getString(0) ?: ""
                val dir = direction(c.getInt(1)) ?: continue
                val account = c.getString(4) ?: ""
                val sub = accounts[account] ?: account
                if (sub != companySub) continue                       // personal SIM: never stored, never sent
                if (last10(number) in excludedLast10) continue          // personal number on the company SIM
                out.add(Row(number, dir, c.getLong(2), c.getInt(3)))
            }
        }
        return out
    }

    fun last10(n: String): String = n.filter { it.isDigit() }.takeLast(10)
}
