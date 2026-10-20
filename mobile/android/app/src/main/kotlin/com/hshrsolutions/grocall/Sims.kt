package com.hshrsolutions.grocall

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.telecom.TelecomManager
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import org.json.JSONArray
import org.json.JSONObject

/** Which SIMs the phone has, and which call-log PHONE_ACCOUNT_ID belongs to which SIM. */
object Sims {
    @SuppressLint("MissingPermission", "HardwareIds")
    fun list(context: Context): JSONArray {
        val out = JSONArray()
        val sm = context.getSystemService(SubscriptionManager::class.java) ?: return out
        val subs = try { sm.activeSubscriptionInfoList } catch (e: SecurityException) { null } ?: return out
        for (s in subs) {
            val number = try {
                if (Build.VERSION.SDK_INT >= 33) sm.getPhoneNumber(s.subscriptionId) else @Suppress("DEPRECATION") s.number
            } catch (e: Exception) { "" } ?: ""
            out.put(JSONObject().apply {
                put("subscription_id", s.subscriptionId.toString())
                put("slot", s.simSlotIndex + 1)
                put("carrier", (s.carrierName ?: s.displayName ?: "").toString())
                put("display_name", (s.displayName ?: "").toString())
                put("last4", number.filter { it.isDigit() }.takeLast(4))
                put("fingerprint", "${s.subscriptionId}:${s.simSlotIndex}:${s.mcc}${s.mnc}")
            })
        }
        return out
    }

    /** Map every call-log account id to a subscription id (as strings). */
    @SuppressLint("MissingPermission")
    fun accountMap(context: Context): Map<String, String> {
        val map = HashMap<String, String>()
        try {
            val tm = context.getSystemService(TelecomManager::class.java)
            val tel = context.getSystemService(TelephonyManager::class.java)
            for (h in tm.callCapablePhoneAccounts) {
                if (Build.VERSION.SDK_INT >= 30) {
                    val sub = tel.getSubscriptionId(h)
                    if (sub != SubscriptionManager.INVALID_SUBSCRIPTION_ID) map[h.id] = sub.toString()
                }
            }
        } catch (e: Exception) { }
        // Older phones: the account id is usually the subscription id itself, or the ICCID.
        try {
            val sm = context.getSystemService(SubscriptionManager::class.java)
            for (s in sm.activeSubscriptionInfoList ?: emptyList()) {
                map.putIfAbsent(s.subscriptionId.toString(), s.subscriptionId.toString())
                try { s.iccId?.takeIf { it.isNotEmpty() }?.let { map.putIfAbsent(it, s.subscriptionId.toString()) } } catch (e: Exception) { }
            }
        } catch (e: Exception) { }
        return map
    }

    /** Tier A: the dialer stores reachable recordings. Tier B: Google Phone keeps them private. */
    fun tier(context: Context): String {
        val dialer = try { context.getSystemService(TelecomManager::class.java).defaultDialerPackage } catch (e: Exception) { null }
        return if (dialer == "com.google.android.dialer") "B" else "A"
    }

    fun dialer(context: Context): String =
        try { context.getSystemService(TelecomManager::class.java).defaultDialerPackage ?: "" } catch (e: Exception) { "" }
}
