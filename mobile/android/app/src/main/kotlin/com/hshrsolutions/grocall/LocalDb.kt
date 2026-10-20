package com.hshrsolutions.grocall

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject

/** Company-SIM calls only. Personal-SIM calls are never written here.
 *  sync_state: pending | sent | excluded ;  rec_state: none | wanted | uploading | done | missing */
class LocalDb(context: Context) : SQLiteOpenHelper(context, "grocall.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE calls (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, direction TEXT,
            started_at INTEGER, duration INTEGER, sync_state TEXT DEFAULT 'pending', call TEXT, call_key TEXT,
            lead_name TEXT, rec_state TEXT DEFAULT 'none', rec_path TEXT, rec_error TEXT, outcome TEXT,
            notified INTEGER DEFAULT 0, UNIQUE(started_at, number))""")
        db.execSQL("CREATE INDEX calls_started ON calls(started_at)")
    }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) {}

    fun insert(number: String, direction: String, startedAt: Long, duration: Int): Boolean {
        val v = ContentValues().apply {
            put("number", number); put("direction", direction); put("started_at", startedAt); put("duration", duration)
        }
        return writableDatabase.insertWithOnConflict("calls", null, v, SQLiteDatabase.CONFLICT_IGNORE) != -1L
    }

    fun update(id: Long, values: Map<String, Any?>) {
        val v = ContentValues()
        values.forEach { (k, x) ->
            when (x) { null -> v.putNull(k); is Int -> v.put(k, x); is Long -> v.put(k, x); else -> v.put(k, x.toString()) }
        }
        writableDatabase.update("calls", v, "id = ?", arrayOf(id.toString()))
    }

    fun query(where: String? = null, args: Array<String>? = null, limit: Int = 200, asc: Boolean = false): List<JSONObject> {
        val out = mutableListOf<JSONObject>()
        readableDatabase.query("calls", null, where, args, null, null,
            "started_at " + (if (asc) "ASC" else "DESC"), limit.toString()).use { c ->
            while (c.moveToNext()) {
                val o = JSONObject()
                for (i in 0 until c.columnCount) {
                    when (c.getType(i)) {
                        android.database.Cursor.FIELD_TYPE_INTEGER -> o.put(c.getColumnName(i), c.getLong(i))
                        android.database.Cursor.FIELD_TYPE_NULL -> o.put(c.getColumnName(i), JSONObject.NULL)
                        else -> o.put(c.getColumnName(i), c.getString(i))
                    }
                }
                out.add(o)
            }
        }
        return out
    }

    fun recentJson(limit: Int): String = JSONArray(query(limit = limit)).toString()

    fun clear() { writableDatabase.delete("calls", null, null) }
}
