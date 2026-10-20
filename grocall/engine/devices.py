"""Phone pairing and device keys (grocall-prd.md §6).

A pairing code is 8 characters, shown as a QR code, valid for 10 minutes, usable once and
stored only as a hash. Pairing returns a per-device key; the server keeps only its hash.
The phone sends X-GroCall-Device + X-GroCall-Key on every call."""

import hashlib
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

from grocall.engine.common import ALL_ROLES, roles, settings

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_MINUTES = 10


def _h(value):
	return hashlib.sha256(value.encode()).hexdigest()


def new_pairing_code(user):
	if not roles(user) & set(ALL_ROLES):
		frappe.throw(_("{0} has no GroCall role, so their phone cannot be paired.").format(user))
	code = "".join(secrets.choice(ALPHABET) for _ in range(8))
	doc = frappe.get_doc({"doctype": "CL Pairing Code", "user": user, "code_hash": _h(code),
		"expires_at": add_to_date(now_datetime(), minutes=CODE_MINUTES)}).insert(ignore_permissions=True)
	return {"code": code, "expires_at": str(doc.expires_at), "user": user,
		"qr": frappe.as_json({"v": 1, "app": "grocall", "site": frappe.utils.get_url(), "code": code}, indent=None)}


def pair(code, info, consent_accepted):
	"""Exchange a code for a device key. `info` comes from the phone (model, SIM, ...)."""
	if not consent_accepted:
		frappe.throw(_("The consent notice must be accepted before pairing."))
	code = (code or "").strip().upper().replace("-", "").replace(" ", "")
	row = frappe.db.get_value("CL Pairing Code", {"code_hash": _h(code)}, ["name", "user", "expires_at", "used"], as_dict=True)
	if not row or row.used:
		frappe.throw(_("This pairing code is not valid or was already used. Ask for a new one."), frappe.PermissionError)
	if get_datetime(row.expires_at) < now_datetime():
		frappe.throw(_("This pairing code has expired. Ask for a new one."), frappe.PermissionError)
	info = frappe._dict(info or {})
	sim = frappe._dict(info.get("sim") or {})
	if not sim.get("subscription_id"):
		frappe.throw(_("Pick the company SIM on the phone before pairing."))
	key = secrets.token_urlsafe(32)
	existing = frappe.db.get_value("CL Device", {"device_uuid": info.get("device_uuid"), "user": row.user}) if info.get(
		"device_uuid") else None
	dev = frappe.get_doc("CL Device", existing) if existing else frappe.new_doc("CL Device")
	dev.update({"user": row.user, "enabled": 1, "revoked_on": None, "device_uuid": info.get("device_uuid"),
		"brand": (info.get("brand") or "")[:140], "model": (info.get("model") or "")[:140],
		"os_version": str(info.get("os_version") or "")[:40], "app_version": str(info.get("app_version") or "")[:40],
		"support_tier": info.get("support_tier") if info.get("support_tier") in ("A", "B") else "",
		"sim_subscription_id": str(sim.subscription_id), "sim_carrier": (sim.get("carrier") or "")[:140],
		"sim_last4": str(sim.get("last4") or "")[-4:], "sim_fingerprint": (sim.get("fingerprint") or "")[:140],
		"paired_on": now_datetime(), "consent_accepted_on": now_datetime(), "last_seen": now_datetime(),
		"token_hash": _h(key)})
	dev.save(ignore_permissions=True) if existing else dev.insert(ignore_permissions=True)
	frappe.db.set_value("CL Pairing Code", row.name, {"used": 1, "used_on": now_datetime(), "device": dev.name})
	return {"device": dev.name, "key": key, "user": row.user, "full_name": frappe.utils.get_fullname(row.user)}


def authenticate(device, key):
	"""The CL Device for a (device, key) pair, or raise. Also marks it seen."""
	if not device or not key:
		frappe.throw(_("This phone is not paired."), frappe.AuthenticationError)
	d = frappe.db.get_value("CL Device", device, ["name", "user", "enabled", "token_hash", "sim_subscription_id"], as_dict=True)
	if not d or not secrets.compare_digest(d.token_hash or "", _h(key)):
		frappe.throw(_("This phone is not paired."), frappe.AuthenticationError)
	if not d.enabled:
		frappe.throw(_("This phone was unpaired by the administrator."), frappe.AuthenticationError)
	if not frappe.db.get_value("User", d.user, "enabled"):
		frappe.throw(_("This salesperson's account is disabled."), frappe.AuthenticationError)
	frappe.db.set_value("CL Device", d.name, "last_seen", now_datetime(), update_modified=False)
	return d


def revoke(device):
	frappe.db.set_value("CL Device", device, {"enabled": 0, "revoked_on": now_datetime(), "token_hash": ""})


def device_settings():
	s = settings()
	return {"sync_scope": s.sync_scope, "allow_fallback_recorder": bool(s.allow_fallback_recorder),
		"consent_text": s.consent_text, "customer_announcement": s.customer_announcement,
		"default_country_code": s.default_country_code, "brand": {"name": s.brand_name, "accent": s.brand_accent}}


def recorder_profiles():
	rows = frappe.get_all("CL Recorder Profile", filters={"enabled": 1},
		fields=["profile_name", "priority", "brands", "folders", "filename_regex"], order_by="priority asc")
	return [{"name": r.profile_name, "priority": r.priority,
		"brands": [b.strip().lower() for b in (r.brands or "").splitlines() if b.strip()],
		"folders": [f.strip().strip("/") for f in (r.folders or "").splitlines() if f.strip()],
		"filename_regex": r.filename_regex or None} for r in rows]


def purge_codes():
	"""Daily: pairing codes older than a day are useless; drop them."""
	frappe.db.delete("CL Pairing Code", {"creation": ["<", add_to_date(now_datetime(), days=-1)]})
