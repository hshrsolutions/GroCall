package com.hshrsolutions.grocall

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Settings + pairing credentials. The device key is AES-GCM encrypted with a key held in the
 *  Android Keystore, so it never sits in plain text on the phone (grocall-prd.md §5.9). */
class Store(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("grocall", Context.MODE_PRIVATE)

    var site: String? get() = prefs.getString("site", null); set(v) = prefs.edit().putString("site", v).apply()
    var device: String? get() = prefs.getString("device", null); set(v) = prefs.edit().putString("device", v).apply()
    var user: String? get() = prefs.getString("user", null); set(v) = prefs.edit().putString("user", v).apply()
    var fullName: String? get() = prefs.getString("full_name", null); set(v) = prefs.edit().putString("full_name", v).apply()
    var simSubId: String? get() = prefs.getString("sim_sub_id", null); set(v) = prefs.edit().putString("sim_sub_id", v).apply()
    var simLabel: String? get() = prefs.getString("sim_label", null); set(v) = prefs.edit().putString("sim_label", v).apply()
    var watermark: Long get() = prefs.getLong("watermark", 0L); set(v) = prefs.edit().putLong("watermark", v).apply()
    var lastSync: Long get() = prefs.getLong("last_sync", 0L); set(v) = prefs.edit().putLong("last_sync", v).apply()
    var lastError: String? get() = prefs.getString("last_error", null); set(v) = prefs.edit().putString("last_error", v).apply()
    var pullCache: String get() = prefs.getString("pull_cache", "{}") ?: "{}"; set(v) = prefs.edit().putString("pull_cache", v).apply()
    var fallbackRecorder: Boolean get() = prefs.getBoolean("fallback_recorder", false); set(v) = prefs.edit().putBoolean("fallback_recorder", v).apply()
    var pairedAt: Long get() = prefs.getLong("paired_at", 0L); set(v) = prefs.edit().putLong("paired_at", v).apply()

    var key: String?
        get() = prefs.getString("key_enc", null)?.let { decrypt(it) }
        set(v) { prefs.edit().putString("key_enc", v?.let { encrypt(it) }).apply() }

    val isPaired: Boolean get() = !site.isNullOrEmpty() && !device.isNullOrEmpty() && !simSubId.isNullOrEmpty() && key != null

    fun cache(): JSONObject = try { JSONObject(pullCache) } catch (e: Exception) { JSONObject() }

    fun clear() { prefs.edit().clear().apply() }

    private fun secretKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .build())
        return gen.generateKey()
    }

    private fun encrypt(plain: String): String {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, secretKey())
        val out = c.iv + c.doFinal(plain.toByteArray())
        return Base64.encodeToString(out, Base64.NO_WRAP)
    }

    private fun decrypt(enc: String): String? = try {
        val raw = Base64.decode(enc, Base64.NO_WRAP)
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, raw.copyOfRange(0, 12)))
        String(c.doFinal(raw.copyOfRange(12, raw.size)))
    } catch (e: Exception) { null }

    companion object { private const val ALIAS = "grocall_device_key" }
}
