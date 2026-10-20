package com.hshrsolutions.grocall

import org.json.JSONArray
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL

class ApiException(val status: Int, message: String) : Exception(message)

/** Minimal client for grocall.api.device (docs/DEVICE-API.md). No third-party HTTP library. */
class Api(private val store: Store) {
    private fun url(method: String) = "${store.site!!.trimEnd('/')}/api/method/grocall.api.device.$method"

    private fun open(method: String): HttpURLConnection {
        val c = URL(url(method)).openConnection() as HttpURLConnection
        c.connectTimeout = 15000
        c.readTimeout = 60000
        c.requestMethod = "POST"
        c.setRequestProperty("Accept", "application/json")
        store.device?.let { c.setRequestProperty("X-GroCall-Device", it) }
        store.key?.let { c.setRequestProperty("X-GroCall-Key", it) }
        c.doOutput = true
        return c
    }

    private fun read(c: HttpURLConnection): JSONObject {
        val code = c.responseCode
        val text = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
        c.disconnect()
        val body = try { JSONObject(text) } catch (e: Exception) { JSONObject() }
        if (code !in 200..299) throw ApiException(code, serverMessage(body) ?: "HTTP $code")
        return body.optJSONObject("message") ?: JSONObject()
    }

    fun post(method: String, payload: JSONObject): JSONObject {
        val c = open(method)
        c.setRequestProperty("Content-Type", "application/json")
        c.outputStream.use { it.write(payload.toString().toByteArray()) }
        return read(c)
    }

    /** One multipart chunk of a recording upload. The body is built in memory (a chunk is at most a
     *  few MB) so it is sent with a Content-Length rather than chunked transfer encoding. */
    fun uploadChunk(callKey: String, offset: Long, total: Long, sha256: String, ext: String, durationSec: Int,
                    bytes: ByteArray, len: Int): JSONObject {
        val boundary = "----grocall" + System.nanoTime()
        val crlf = "\r\n"
        val body = java.io.ByteArrayOutputStream(len + 2048)
        DataOutputStream(body).use { out ->
            fun field(name: String, value: String) {
                out.writeBytes("--$boundary$crlf" + "Content-Disposition: form-data; name=\"$name\"$crlf$crlf$value$crlf")
            }
            field("call_key", callKey); field("offset", offset.toString()); field("total_size", total.toString())
            field("sha256", sha256); field("ext", ext); field("duration_sec", durationSec.toString())
            out.writeBytes("--$boundary$crlf" + "Content-Disposition: form-data; name=\"chunk\"; filename=\"chunk.bin\"$crlf")
            out.writeBytes("Content-Type: application/octet-stream$crlf$crlf")
            out.write(bytes, 0, len)
            out.writeBytes("$crlf--$boundary--$crlf")
        }
        val c = open("upload_recording")
        c.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        c.setFixedLengthStreamingMode(body.size())
        c.outputStream.use { body.writeTo(it) }
        return read(c)
    }

    companion object {
        fun serverMessage(body: JSONObject): String? {
            body.optString("_server_messages").takeIf { it.isNotEmpty() }?.let {
                try {
                    val first = JSONArray(it).getString(0)
                    return JSONObject(first).optString("message").replace(Regex("<[^>]+>"), "")
                } catch (e: Exception) { }
            }
            body.optString("exception").takeIf { it.isNotEmpty() }?.let { return it.substringAfter(":").trim() }
            return null
        }
    }
}
