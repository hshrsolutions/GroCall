"""Device API for the GroCall phone app (grocall-prd.md §6).

Pairing is the only call without a device key. Every other call sends the headers
X-GroCall-Device and X-GroCall-Key; the request then runs as that salesperson, so the
normal row-level rules apply. Bodies are JSON; replies are {ok: true, ...}."""

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

import grocall
from grocall.engine import devices, ingest
from grocall.engine.leads import excluded_numbers

MIN_APP_VERSION = "0.1.0"


def _arg(v, default=None):
	if v in (None, ""):
		return default
	return frappe.parse_json(v) if isinstance(v, str) and v[:1] in "[{" else v


def _device():
	h = frappe.get_request_header
	d = devices.authenticate(h("X-GroCall-Device"), h("X-GroCall-Key"))
	frappe.set_user(d.user)
	return d


def _common():
	return {"settings": devices.device_settings(), "recorder_profiles": devices.recorder_profiles(),
		"server_time": str(now_datetime()), "server_version": grocall.__version__, "min_app_version": MIN_APP_VERSION}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def consent():
	"""Before pairing the phone shows this site's notice; nothing secret here."""
	return {"ok": True, "settings": devices.device_settings(), "server_version": grocall.__version__,
		"min_app_version": MIN_APP_VERSION}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def pair(code=None, device_info=None, consent_accepted=None):
	res = devices.pair(code, _arg(device_info, {}), frappe.utils.cint(consent_accepted) or consent_accepted is True)
	frappe.db.commit()
	return {"ok": True, **res, **_common()}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sync(calls=None, app_version=None):
	d = _device()
	res = ingest.sync(d, _arg(calls, []), app_version)
	return {"ok": True, **res}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def pull():
	d = _device()
	leads = frappe.get_all("CL Lead", filters={"lead_owner": d.user}, fields=["name", "lead_name", "company_name", "stage",
		"next_follow_up", "last_call_at"],
		order_by="modified desc", limit=3000)
	phones = {}
	if leads:
		for r in frappe.get_all("CL Lead Phone", filters={"parent": ["in", [l.name for l in leads]], "parenttype": "CL Lead"},
				fields=["parent", "e164"]):
			phones.setdefault(r.parent, []).append(r.e164)
	for l in leads:
		l["phones"] = phones.get(l.name, [])
		l["next_follow_up"] = str(l.next_follow_up) if l.next_follow_up else None
		l["last_call_at"] = str(l.last_call_at) if l.last_call_at else None
	dispositions = frappe.get_all("CL Disposition", filters={"enabled": 1},
		fields=["label", "connected", "needs_follow_up", "default_follow_up_days"], order_by="sequence asc")
	pending = frappe.get_all("CL Call", filters={"rep": d.user, "recording_status": "Pending",
		"started_at": [">", frappe.utils.add_days(now_datetime(), -7)]}, fields=["call_key", "started_at", "phone",
		"duration_sec"], order_by="started_at desc", limit=500)
	return {"ok": True, "user": d.user, "full_name": frappe.utils.get_fullname(d.user), "leads": leads,
		"pending_recordings": [{**p, "started_at": str(p.started_at)} for p in pending],
		"excluded_numbers": sorted(n for n in excluded_numbers(d.user) if n), "dispositions": dispositions,
		"follow_ups": [], "missed_alerts": [], **_common()}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def disposition(call=None, call_key=None, disposition=None, notes=None, next_follow_up=None):
	_device()
	name = call or frappe.db.get_value("CL Call", {"call_key": call_key})
	if not name:
		frappe.throw("Call not found. Sync it first.", frappe.DoesNotExistError)
	doc = ingest.set_disposition(name, disposition, notes, next_follow_up)
	return {"ok": True, "call": doc.name, "next_follow_up": str(doc.next_follow_up or "")}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def heartbeat(permissions=None, app_version=None, support_tier=None, fallback_recorder=None):
	d = _device()
	upd = {"permissions_json": frappe.as_json(_arg(permissions, {}), indent=None)[:2000]}
	if app_version:
		upd["app_version"] = str(app_version)[:40]
	if support_tier in ("A", "B"):
		upd["support_tier"] = support_tier
	if fallback_recorder is not None:
		upd["fallback_recorder"] = 1 if frappe.utils.cint(fallback_recorder) else 0
	frappe.db.set_value("CL Device", d.name, upd, update_modified=False)
	return {"ok": True, **_common()}


# ---------------------------------------------------------------------------
# Recordings (Phase 2)
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload_recording(call_key=None, offset=0, total_size=None, sha256=None, ext=None, duration_sec=None):
	"""multipart/form-data with the fields above and the bytes in a part named `chunk`."""
	d = _device()
	chunk = frappe.request.files.get("chunk") if frappe.request and frappe.request.files else None
	if chunk is None:
		frappe.throw("Send the bytes in a multipart part named 'chunk'.")
	res = ingest.receive_chunk(d, call_key, offset, total_size, sha256, ext, chunk.stream, duration_sec)
	return {"ok": True, **res}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload_status(call_key=None):
	d = _device()
	return {"ok": True, **ingest.upload_status(d, call_key)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def recording_missing(call_key=None, reason=None):
	d = _device()
	return {"ok": True, **ingest.mark_recording_missing(d, call_key, reason)}
