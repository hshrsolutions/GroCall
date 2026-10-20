"""The only writer of CL Call rows coming from phones (grocall-prd.md §5.2).

sync() is idempotent: the call key is (salesperson, start instant, number), so a batch
resent after a dropped connection, or after the phone is re-paired, reports duplicates
instead of creating them. Rows not on the company SIM, or to an excluded number, are
refused here too even though the phone already filters them (defence in depth)."""

import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_system_timezone, now_datetime

from grocall.engine.leads import excluded_numbers, match_lead
from grocall.engine.phone import last10, normalize

MAX_BATCH = 500
DIRECTION = {"incoming": "Incoming", "outgoing": "Outgoing", "missed": "Missed", "rejected": "Rejected",
	"blocked": "Blocked"}


def call_key(user, started_ms, number):
	ident = last10(normalize(number) or "") or (number or "").strip()
	return hashlib.sha1(f"{user}|{int(started_ms)}|{ident}".encode()).hexdigest()


def from_epoch_ms(ms):
	tz = ZoneInfo(get_system_timezone())
	return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).astimezone(tz).replace(tzinfo=None, microsecond=0)


def sync(device, calls, app_version=None):
	if not isinstance(calls, list):
		frappe.throw(_("calls must be a list"))
	if len(calls) > MAX_BATCH:
		frappe.throw(_("Send at most {0} calls per batch.").format(MAX_BATCH))
	user = device.user
	excluded = excluded_numbers(user)
	results, counts = [], {"created": 0, "duplicate": 0, "excluded": 0, "error": 0}
	for item in calls:
		item = frappe._dict(item or {})
		res = {"ref": item.get("ref")}
		frappe.db.savepoint("cl_row")
		try:
			res.update(_one(device, user, item, excluded))
		except Exception as e:
			frappe.db.rollback(save_point="cl_row")
			frappe.local.message_log = []
			res.update({"status": "error", "message": str(e)[:300]})
		counts[res["status"]] += 1
		results.append(res)
	frappe.get_doc({"doctype": "CL Sync Log", "device": device.name, "user": user, "app_version": app_version,
		"received": len(calls), "created_count": counts["created"], "duplicates": counts["duplicate"],
		"excluded": counts["excluded"], "errors": counts["error"],
		"details": frappe.as_json([r for r in results if r["status"] in ("error", "excluded")][:100])}).insert(
		ignore_permissions=True)
	upd = {"last_sync": now_datetime()}
	if app_version:
		upd["app_version"] = str(app_version)[:40]
	frappe.db.set_value("CL Device", device.name, upd, update_modified=False)
	return {"results": results, "counts": counts}


def _one(device, user, item, excluded):
	direction = DIRECTION.get(str(item.get("direction") or "").lower())
	if not direction:
		frappe.throw(_("Unknown direction {0}").format(item.get("direction")))
	if item.get("started_at") in (None, ""):
		frappe.throw(_("started_at (epoch milliseconds) is required"))
	started_ms = int(item.started_at)
	if str(item.get("sim_subscription_id") or "") != str(device.sim_subscription_id or ""):
		return {"status": "excluded", "message": "not the company SIM"}
	raw = (item.get("number") or "").strip()
	e164 = normalize(raw)
	if e164 and e164 in excluded:
		return {"status": "excluded", "message": "excluded number"}
	key = call_key(user, started_ms, raw)
	existing = frappe.db.get_value("CL Call", {"call_key": key}, ["name", "recording_status"], as_dict=True)
	if existing:
		return {"status": "duplicate", "call": existing.name, "call_key": key,
			"upload": existing.recording_status == "Pending"}
	duration = max(cint(item.get("duration_sec")), 0)
	if direction in ("Missed", "Rejected", "Blocked"):
		duration = 0
	connected = direction in ("Incoming", "Outgoing") and duration > 0
	lead = match_lead(e164, rep=user)
	doc = frappe.get_doc({"doctype": "CL Call", "call_key": key, "direction": direction, "phone": e164 or raw,
		"raw_number": raw[:140], "started_at": from_epoch_ms(started_ms), "duration_sec": duration, "rep": user,
		"device": device.name, "lead": lead, "source": "android", "connected": 1 if connected else 0,
		"recording_status": "Pending" if connected else ""})
	doc.title = _title(doc)
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		return {"status": "duplicate", "call": frappe.db.get_value("CL Call", {"call_key": key}), "call_key": key}
	if lead:
		_touch_lead(lead, doc.started_at)
	_run_hooks("grocall_call_created", doc)
	return {"status": "created", "call": doc.name, "call_key": key, "lead": lead,
		"lead_name": frappe.db.get_value("CL Lead", lead, "lead_name") if lead else None, "upload": bool(connected)}


def _title(doc):
	name = frappe.db.get_value("CL Lead", doc.lead, "lead_name") if doc.lead else None
	return f"{doc.direction}: {name or doc.phone or 'unknown'}"[:140]


def _touch_lead(lead, started_at):
	last = frappe.db.get_value("CL Lead", lead, "last_call_at")
	count = frappe.db.count("CL Call", {"lead": lead})
	upd = {"calls_count": count}
	if not last or get_datetime(started_at) > get_datetime(last):
		upd["last_call_at"] = started_at
	frappe.db.set_value("CL Lead", lead, upd, update_modified=False)


def set_disposition(call, disposition, notes=None, next_follow_up=None, user=None):
	"""Record the outcome of a call (phone after-call card or web). Moves the lead's stage."""
	user = user or frappe.session.user
	doc = frappe.get_doc("CL Call", call)
	if not frappe.has_permission("CL Call", "write", doc=doc, user=user):
		frappe.throw(_("You can only update your own calls."), frappe.PermissionError)
	d = frappe.get_cached_doc("CL Disposition", disposition)
	if not d.enabled:
		frappe.throw(_("Outcome {0} is disabled.").format(disposition))
	if d.needs_follow_up and not next_follow_up:
		next_follow_up = get_datetime(add_days(now_datetime(), cint(d.default_follow_up_days) or 1)).replace(
			hour=10, minute=0, second=0, microsecond=0)
	doc.disposition = disposition
	doc.notes = notes if notes is not None else doc.notes
	doc.next_follow_up = next_follow_up or None
	doc.dispositioned_on = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	if doc.lead:
		upd = {"last_disposition": disposition, "next_follow_up": doc.next_follow_up}
		if d.moves_stage_to:
			upd["stage"] = d.moves_stage_to
		frappe.db.set_value("CL Lead", doc.lead, upd)
	_run_hooks("grocall_call_dispositioned", doc)
	return doc


def _run_hooks(name, doc):
	for fn in frappe.get_hooks(name):
		try:
			frappe.get_attr(fn)(doc)
		except Exception:
			frappe.log_error(title=f"GroCall hook {name} failed", message=frappe.get_traceback())


# ---------------------------------------------------------------------------
# Recording upload (Phase 2): resumable, offset-based, checksum-verified
# ---------------------------------------------------------------------------

def _call_for_upload(device, call_key):
	row = frappe.db.get_value("CL Call", {"call_key": call_key}, ["name", "rep", "recording_status", "started_at",
		"connected"], as_dict=True)
	if not row or row.rep != device.user:
		frappe.throw(_("Call not found. Sync it first."), frappe.DoesNotExistError)
	return row


def upload_status(device, call_key):
	import os

	from grocall.engine import storage

	row = _call_for_upload(device, call_key)
	part = storage.partial_path(row.name)
	return {"call": row.name, "recording_status": row.recording_status,
		"received": os.path.getsize(part) if os.path.exists(part) else 0}


def receive_chunk(device, call_key, offset, total_size, sha256, ext, chunk, duration_sec=None):
	"""Append one chunk. If `offset` is not where the server is, nothing is written and the
	server's position comes back, so the phone resumes from there after a dropped connection."""
	import hashlib
	import os
	import shutil

	from grocall.engine import storage

	row = _call_for_upload(device, call_key)
	if row.recording_status == "Uploaded":
		return {"call": row.name, "status": "complete", "received": cint(total_size)}
	if row.recording_status in ("Purged", "Excluded"):
		frappe.throw(_("This call's recording is not accepted ({0}).").format(row.recording_status))
	ext = (ext or "").lower().lstrip(".")
	if ext not in storage.AUDIO_TYPES:
		frappe.throw(_("Unsupported audio type: {0}").format(ext))
	total_size, offset = cint(total_size), cint(offset)
	if total_size <= 0 or total_size > storage.MAX_BYTES:
		frappe.throw(_("Recording size must be between 1 byte and {0} MB.").format(storage.MAX_BYTES // 1048576))
	if not sha256 or len(sha256) != 64:
		frappe.throw(_("sha256 of the whole file is required"))
	data = chunk.read(storage.MAX_CHUNK + 1) if hasattr(chunk, "read") else (chunk or b"")
	if len(data) > storage.MAX_CHUNK:
		frappe.throw(_("Chunks may be at most {0} MB.").format(storage.MAX_CHUNK // 1048576))
	part = storage.partial_path(row.name)
	have = os.path.getsize(part) if os.path.exists(part) else 0
	if offset != have:
		return {"call": row.name, "status": "resume", "received": have}
	if have + len(data) > total_size:
		if os.path.exists(part):
			os.remove(part)
		frappe.throw(_("More data than the declared size; upload restarted."))
	with open(part, "ab") as f:
		f.write(data)
	have += len(data)
	if have < total_size:
		return {"call": row.name, "status": "partial", "received": have}

	h = hashlib.sha256()
	with open(part, "rb") as f:
		for block in iter(lambda: f.read(1048576), b""):
			h.update(block)
	if h.hexdigest() != sha256.lower():
		os.remove(part)
		frappe.throw(_("Checksum mismatch; the upload was discarded. Send it again from the start."))
	rel = storage.final_relpath(row.name, ext, get_datetime(row.started_at))
	dest = frappe.get_site_path("private", "files", rel)
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	shutil.move(part, dest)
	frappe.db.set_value("CL Call", row.name, {"recording": rel, "recording_status": "Uploaded", "recording_size": have,
		"recording_sha256": sha256.lower(), "recording_uploaded_on": now_datetime(),
		"recording_seconds": cint(duration_sec) or None})
	return {"call": row.name, "status": "complete", "received": have}


def mark_recording_missing(device, call_key, reason):
	"""The phone looked and found no file (Not found) or the phone can't reach recordings (Not available)."""
	row = _call_for_upload(device, call_key)
	status = "Not available" if reason == "not_available" else "Not found"
	if row.recording_status in ("", "Pending", "Not found", "Not available", None):
		frappe.db.set_value("CL Call", row.name, "recording_status", status)
	return {"call": row.name, "recording_status": status}


# What the phone reported is evidence: nobody edits it afterwards, whatever their role.
PROTECTED = ("direction", "phone", "raw_number", "started_at", "duration_sec", "rep", "device", "call_key", "source",
	"connected", "recording", "recording_status", "recording_size", "recording_sha256", "recording_uploaded_on",
	"recording_purged_on", "recording_seconds")


def call_validate(doc, method=None):
	if doc.is_new():
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	changed = [f for f in PROTECTED if str(doc.get(f) or "") != str(before.get(f) or "")]
	if changed:
		frappe.throw(_("These call details come from the phone and cannot be edited: {0}").format(", ".join(changed)),
			frappe.PermissionError)
