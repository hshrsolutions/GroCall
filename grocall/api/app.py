"""Whitelisted endpoints for the /calls web app.

Every endpoint: role gate first, then the engine, then the {ok, ...} envelope.
Phase 0 has only the boot payload; data endpoints arrive with their phases."""

import frappe

import grocall
from grocall.engine import common
from grocall.engine.teams import teams_of


def brand():
	s = common.settings()
	return {"name": s.brand_name or "GroCall", "accent": s.brand_accent or "#0f766e"}


def boot_payload():
	user = frappe.session.user
	p = common.perms(user)
	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"perms": p,
		"has_access": p["rep"],
		"brand": brand(),
		"version": grocall.__version__,
		"teams": teams_of(user) if p["rep"] else {"managed": [], "member": []},
	}


def has_app_permission():
	"""/apps tile: visible to anyone who may use GroCall."""
	return common.perms()["rep"]


@frappe.whitelist()
def boot():
	if frappe.session.user == "Guest":
		frappe.throw("Please sign in.", frappe.AuthenticationError)
	return {"ok": True, **boot_payload()}


# ---------------------------------------------------------------------------
# Phones (Phase 1)
# ---------------------------------------------------------------------------

def _need(level):
	if not common.perms()[level]:
		frappe.throw("You are not allowed to do that.", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def pairing_code(user=None):
	"""A one-time code + QR payload. Reps pair their own phone; managers/admins any visible rep."""
	from grocall.engine import devices
	from grocall.engine.access import visible_users

	_need("rep")
	user = user or frappe.session.user
	if user != frappe.session.user:
		_need("manager")
		vis = visible_users()
		if vis is not None and user not in vis:
			frappe.throw("That salesperson is not in your team.", frappe.PermissionError)
	return {"ok": True, **devices.new_pairing_code(user)}


@frappe.whitelist()
def phones():
	_need("rep")
	rows = frappe.get_list("CL Device", fields=["name", "user", "full_name", "brand", "model", "os_version", "app_version",
		"support_tier", "sim_carrier", "sim_last4", "enabled", "paired_on", "last_seen", "last_sync", "revoked_on"],
		order_by="enabled desc, last_seen desc", limit=500)
	reps = []
	if common.perms()["manager"]:
		from grocall.engine.access import visible_users

		vis = visible_users()
		filters = {"enabled": 1, "user_type": ["in", ["System User", "Website User"]]}
		names = frappe.get_all("Has Role", filters={"role": ["in", list(common.ALL_ROLES)], "parenttype": "User"},
			pluck="parent", distinct=True)
		filters["name"] = ["in", [n for n in names if vis is None or n in vis] or ["-"]]
		reps = frappe.get_all("User", filters=filters, fields=["name", "full_name"], order_by="full_name asc")
	return {"ok": True, "phones": rows, "reps": reps}


@frappe.whitelist(methods=["POST"])
def revoke_phone(device):
	from grocall.engine import devices

	_need("admin")
	devices.revoke(device)
	return {"ok": True}


# ---------------------------------------------------------------------------
# Recordings (Phase 2)
# ---------------------------------------------------------------------------

@frappe.whitelist(methods=["GET"])
def recording(call):
	"""Stream a recording with HTTP Range (so the player can seek). Access = read on the call.
	A play is logged once per listen (the first request, or one starting at byte 0)."""
	import os

	from werkzeug.wrappers import Response

	from grocall.engine import storage

	doc = frappe.get_doc("CL Call", call)
	if not frappe.has_permission("CL Call", "read", doc=doc):
		frappe.throw("You cannot listen to this call.", frappe.PermissionError)
	if doc.recording_status != "Uploaded" or not doc.recording:
		frappe.throw("No recording for this call.", frappe.DoesNotExistError)
	path = storage.abspath(doc.recording)
	if not os.path.exists(path):
		frappe.throw("The recording file is missing.", frappe.DoesNotExistError)
	rng = frappe.get_request_header("Range") or ""
	if not rng or rng.replace(" ", "") in ("bytes=0-", "bytes=0-1"):
		frappe.get_doc({"doctype": "CL Playback Log", "call": doc.name, "user": frappe.session.user,
			"played_at": frappe.utils.now_datetime(), "ip": frappe.local.request_ip, "rep": doc.rep}).insert(
			ignore_permissions=True)
		frappe.db.commit()
	size = os.path.getsize(path)
	start, end, status = 0, size - 1, 200
	if rng.startswith("bytes="):
		a, _, b = rng[6:].split(",")[0].partition("-")
		try:
			if a:
				start, end = int(a), int(b) if b else size - 1
			else:
				start, end = size - int(b), size - 1
		except ValueError:
			start, end = 0, size - 1
		end = min(end, size - 1)
		if start > end or start >= size:
			r = Response(status=416)
			r.headers["Content-Range"] = f"bytes */{size}"
			return r
		status = 206
	f = open(path, "rb")
	f.seek(start)
	length = end - start + 1

	def body():
		left = length
		try:
			while left > 0:
				block = f.read(min(65536, left))
				if not block:
					break
				left -= len(block)
				yield block
		finally:
			f.close()

	r = Response(body(), status=status, mimetype=storage.mimetype(doc.recording), direct_passthrough=True)
	r.headers["Accept-Ranges"] = "bytes"
	r.headers["Content-Length"] = str(length)
	r.headers["Cache-Control"] = "private, no-store"
	if status == 206:
		r.headers["Content-Range"] = f"bytes {start}-{end}/{size}"
	return r


@frappe.whitelist()
def storage_usage():
	from grocall.engine import storage

	_need("admin")
	u = storage.usage()
	return {"ok": True, **u, "human": storage.human(u["bytes"])}


@frappe.whitelist(methods=["POST"])
def erase_number(phone):
	from grocall.engine import retention

	_need("admin")
	n = retention.erase_number(phone)
	return {"ok": True, "erased": n}
