"""
GroCall release gate — grocall-prd.md §10 checklists (Phase 0 so far).

    bench --site demo.grohrms.cloud execute grocall.selftest.run

DEV/TEST SITES ONLY: it creates throw-away users and a team named ZZCL-* and deletes
them afterwards. Refuses to run unless the site has developer_mode or allow_tests.
"""

import frappe

P = "zzcl"
USERS = {"rep": f"{P}-rep@example.com", "rep2": f"{P}-rep2@example.com", "manager": f"{P}-manager@example.com",
	"manager2": f"{P}-manager2@example.com", "admin": f"{P}-admin@example.com", "outsider": f"{P}-outsider@example.com"}
ROLE = {"rep": "CL Sales Rep", "rep2": "CL Sales Rep", "manager": "CL Sales Manager", "manager2": "CL Sales Manager",
	"admin": "CL Admin"}
NUM = "+919990001111"  # test numbers live in the +91999000xxxx block
NUM2 = "+919990002222"
NUM_X = "+919990003333"
TEAM = "ZZCL Team"


class Results:
	def __init__(self):
		self.passed, self.failed = 0, []

	def check(self, name, ok, detail=""):
		if ok:
			self.passed += 1
			print(f"  PASS  {name}")
		else:
			self.failed.append(name)
			print(f"  FAIL  {name}  {detail}")


def raises(fn, needle=None):
	frappe.db.savepoint("zzcl_sp")
	try:
		fn()
	except Exception as e:
		frappe.db.rollback(save_point="zzcl_sp")
		frappe.local.message_log = []
		return needle is None or needle.lower() in str(e).lower()
	return False


def run():
	if not (frappe.conf.get("developer_mode") or frappe.conf.get("allow_tests")):
		print("Refusing to run: not a developer/test site.")
		return
	frappe.set_user("Administrator")
	r = Results()
	cleanup()
	try:
		make_users()
		phase0(r)
		phase1(r)
		phase2(r)
	finally:
		frappe.set_user("Administrator")
		cleanup()
		frappe.db.commit()
	print(f"\nGroCall selftest: {r.passed} passed, {len(r.failed)} failed")
	if r.failed:
		print("FAILED: " + "; ".join(r.failed))
	return {"passed": r.passed, "failed": r.failed}


def make_users():
	for key, email in USERS.items():
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": f"ZZCL {key}", "send_welcome_email": 0,
			"user_type": "System User" if key in ("manager", "manager2", "admin") else "Website User"})
		u.insert(ignore_permissions=True)
		if key in ROLE:
			u.add_roles(ROLE[key])


def phase0(r):
	from grocall.api.app import boot_payload
	from grocall.engine.common import perms

	print("Phase 0 — foundation")
	for role in ("CL Sales Rep", "CL Sales Manager", "CL Admin"):
		r.check(f"role exists: {role}", frappe.db.exists("Role", role))
	for dt in ("CL Settings", "CL Team", "CL Team Member"):
		r.check(f"doctype exists: {dt}", frappe.db.exists("DocType", dt))
	r.check("workspace GroCall exists", frappe.db.exists("Workspace", "GroCall"))
	s = frappe.get_single("CL Settings")
	r.check("settings defaults seeded", s.brand_name and s.missed_call_sla_minutes == 30
		and s.sync_scope == "Company SIM only" and s.retain_recordings_days == 180, s.as_dict().get("brand_name"))
	r.check("AI is off by default", not s.auto_transcribe and not s.monthly_ai_budget)
	r.check("API keys are Password fields", all(s.meta.get_field(f).fieldtype == "Password"
		for f in ("stt_api_key", "summary_api_key")))

	expect = {"rep": (True, False, False), "manager": (True, True, False), "admin": (True, True, True),
		"outsider": (False, False, False)}
	for key, (rep, mgr, adm) in expect.items():
		p = perms(USERS[key])
		r.check(f"perms for {key}", (p["rep"], p["manager"], p["admin"]) == (rep, mgr, adm), p)
	r.check("Administrator counts as admin", perms("Administrator")["admin"])

	frappe.set_user(USERS["outsider"])
	r.check("outsider boot has no access", boot_payload()["has_access"] is False)
	frappe.set_user(USERS["rep"])
	b = boot_payload()
	r.check("rep boot has access + brand + version", b["has_access"] and b["brand"]["name"] and b["version"])
	r.check("rep cannot write settings", not frappe.has_permission("CL Settings", "write"))
	r.check("rep cannot create a team", not frappe.has_permission("CL Team", "create"))
	frappe.set_user(USERS["manager"])
	r.check("manager can read settings, not write", frappe.has_permission("CL Settings", "read")
		and not frappe.has_permission("CL Settings", "write"))
	frappe.set_user(USERS["admin"])
	r.check("admin can write settings and create teams", frappe.has_permission("CL Settings", "write")
		and frappe.has_permission("CL Team", "create"))
	frappe.set_user("Administrator")

	def team(members, manager="manager"):
		return frappe.get_doc({"doctype": "CL Team", "team_name": TEAM, "manager": USERS[manager],
			"members": [{"user": USERS[m]} for m in members]})

	r.check("team: duplicate member refused", raises(lambda: team(["rep", "rep"]).insert(), "twice"))
	r.check("team: member without a GroCall role refused", raises(lambda: team(["outsider"]).insert(), "no GroCall role"))
	r.check("team: rep as manager refused", raises(lambda: team(["rep2"], manager="rep").insert(), "Sales Manager role"))
	team(["rep", "rep2"]).insert()
	from grocall.engine.teams import teams_of

	r.check("team saved; teams_of(manager) lists it", TEAM in teams_of(USERS["manager"])["managed"])
	r.check("teams_of(rep) lists membership", TEAM in teams_of(USERS["rep"])["member"])

	from grocall.api.app import has_app_permission

	frappe.set_user(USERS["rep"])
	rep_tile = has_app_permission()
	frappe.set_user(USERS["outsider"])
	out_tile = has_app_permission()
	frappe.set_user("Administrator")
	r.check("/apps tile: shown to a rep, hidden from an outsider", rep_tile and not out_tile)
	r.check("/apps tile registered", any(a.get("route") == "/calls" for a in frappe.get_hooks("add_to_apps_screen")))
	r.check("/calls route rule present", any(x["from_route"] == "/calls" for x in frappe.get_hooks("website_route_rules")))
	import os

	html = frappe.get_app_path("grocall", "www", "calls.html")
	r.check("/calls page built (www/calls.html)", os.path.exists(html))


def phase1(r):
	from frappe.utils import add_to_date, now_datetime

	from grocall.engine import devices, ingest
	from grocall.engine.phone import normalize

	print("Phase 1 — data model + device sync")
	r.check("seed: 6 stages", frappe.db.count("CL Stage") >= 6)
	r.check("seed: 8 outcomes", frappe.db.count("CL Disposition") >= 8)
	r.check("seed: recorder profiles incl. generic", frappe.db.exists("CL Recorder Profile", "Generic fallback")
		and frappe.db.count("CL Recorder Profile") >= 6)

	forms = ["+91 99900 01111", "09990001111", "9990001111", "919990001111", "0091-9990001111", "(999) 000-1111"]
	r.check("phone: +91 / 0 / 10-digit / 91 / 0091 forms normalise the same", {normalize(f) for f in forms} == {NUM},
		{f: normalize(f) for f in forms})
	r.check("phone: short code is not a number", normalize("121") is None)

	# leads
	frappe.set_user(USERS["rep"])
	lead = frappe.get_doc({"doctype": "CL Lead", "lead_name": "ZZCL Lead One", "lead_owner": USERS["rep2"],
		"phones": [{"phone": "09990001111"}]}).insert()
	r.check("lead: rep's lead is forced to be their own", lead.lead_owner == USERS["rep"], lead.lead_owner)
	r.check("lead: phone stored normalised + primary", lead.phones[0].e164 == NUM and lead.primary_phone == NUM)
	r.check("lead: stage defaults to New", lead.stage == "New")
	r.check("lead: same number on a second lead refused", raises(lambda: frappe.get_doc({"doctype": "CL Lead",
		"lead_name": "ZZCL Dup", "phones": [{"phone": "+91 99900 01111"}]}).insert(), "already belongs"))
	r.check("lead: invalid number refused", raises(lambda: frappe.get_doc({"doctype": "CL Lead",
		"lead_name": "ZZCL Bad", "phones": [{"phone": "12"}]}).insert(), "not a valid"))
	frappe.set_user(USERS["rep2"])
	lead2 = frappe.get_doc({"doctype": "CL Lead", "lead_name": "ZZCL Lead Two", "phones": [{"phone": NUM2}]}).insert()
	frappe.set_user("Administrator")

	# pairing
	c = devices.new_pairing_code(USERS["rep"])
	r.check("pairing: code is 8 chars + QR payload names the site", len(c["code"]) == 8 and '"code"' in c["qr"])
	r.check("pairing: stored only as a hash", not frappe.db.exists("CL Pairing Code", {"code_hash": c["code"]}))
	info = {"device_uuid": "zzcl-uuid-1", "brand": "samsung", "model": "SM-ZZ", "os_version": "14", "app_version": "0.1.0",
		"support_tier": "A", "sim": {"subscription_id": "2", "carrier": "Jio", "last4": "4321", "fingerprint": "fp"}}
	r.check("pairing: refused without consent", raises(lambda: devices.pair(c["code"], info, False), "consent"))
	r.check("pairing: refused without a company SIM", raises(lambda: devices.pair(c["code"], {**info, "sim": {}}, True),
		"company SIM"))
	r.check("pairing: user without a GroCall role refused", raises(lambda: devices.new_pairing_code(USERS["outsider"]),
		"no GroCall role"))
	p = devices.pair(c["code"].lower()[:4] + "-" + c["code"].lower()[4:], info, True)
	r.check("pairing: works (code case/dash-insensitive), returns a key", p["key"] and p["device"])
	dev = frappe.get_doc("CL Device", p["device"])
	r.check("pairing: device records company SIM + tier", dev.sim_subscription_id == "2" and dev.support_tier == "A"
		and dev.consent_accepted_on)
	r.check("pairing: a used code is refused", raises(lambda: devices.pair(c["code"], info, True), "already used"))
	c2 = devices.new_pairing_code(USERS["rep"])
	frappe.db.set_value("CL Pairing Code", {"code_hash": devices._h(c2["code"])}, "expires_at",
		add_to_date(now_datetime(), minutes=-1))
	r.check("pairing: an expired code is refused", raises(lambda: devices.pair(c2["code"], info, True), "expired"))
	r.check("auth: right key accepted", devices.authenticate(p["device"], p["key"]).user == USERS["rep"])
	r.check("auth: wrong key refused", raises(lambda: devices.authenticate(p["device"], "nope"), "not paired"))
	c3 = devices.new_pairing_code(USERS["rep"])
	p2 = devices.pair(c3["code"], info, True)
	r.check("re-pair: same phone keeps its record, old key stops working", p2["device"] == p["device"]
		and raises(lambda: devices.authenticate(p["device"], p["key"]), "not paired"))
	key = p2["key"]

	# sync
	frappe.get_doc({"doctype": "CL Excluded Number", "phone": NUM_X, "user": USERS["rep"], "reason": "test"}).insert(
		ignore_permissions=True)
	t0 = 1_780_000_000_000
	batch = [
		{"ref": "a", "direction": "outgoing", "number": "09990001111", "started_at": t0, "duration_sec": 65, "sim_subscription_id": "2"},
		{"ref": "b", "direction": "incoming", "number": "+919990001111", "started_at": t0 + 600000, "duration_sec": 30, "sim_subscription_id": "2"},
		{"ref": "c", "direction": "missed", "number": "9990009999", "started_at": t0 + 900000, "duration_sec": 12, "sim_subscription_id": "2"},
		{"ref": "d", "direction": "outgoing", "number": "9990004444", "started_at": t0 + 1000000, "duration_sec": 40, "sim_subscription_id": "1"},
		{"ref": "e", "direction": "outgoing", "number": NUM_X, "started_at": t0 + 1100000, "duration_sec": 40, "sim_subscription_id": "2"},
		{"ref": "f", "direction": "sideways", "number": "9990005555", "started_at": t0 + 1200000, "sim_subscription_id": "2"},
	]
	d = devices.authenticate(p["device"], key)
	frappe.set_user(d.user)
	res = ingest.sync(d, batch, "0.1.0")
	frappe.set_user("Administrator")
	by = {x["ref"]: x for x in res["results"]}
	r.check("sync: 3 created, 2 excluded, 1 error", res["counts"] == {"created": 3, "duplicate": 0, "excluded": 2, "error": 1},
		res["counts"])
	r.check("sync: personal-SIM call refused", by["d"]["status"] == "excluded" and "SIM" in by["d"]["message"])
	r.check("sync: excluded number refused", by["e"]["status"] == "excluded")
	r.check("sync: 0-prefixed and +91 numbers both matched the lead", by["a"].get("lead") == lead.name
		and by["b"].get("lead") == lead.name)
	again = ingest.sync(d, batch, "0.1.0")
	r.check("sync: same batch twice gives 0 new calls", again["counts"]["created"] == 0 and again["counts"]["duplicate"] == 3,
		again["counts"])
	ca, cc = frappe.get_doc("CL Call", by["a"]["call"]), frappe.get_doc("CL Call", by["c"]["call"])
	r.check("call: connected outgoing awaits its recording", ca.connected and ca.recording_status == "Pending"
		and ca.duration_sec == 65 and ca.phone == NUM)
	r.check("call: missed call has 0 s, no recording expected", not cc.connected and cc.duration_sec == 0
		and not cc.recording_status and not cc.lead)
	r.check("call: lead activity updated", frappe.db.get_value("CL Lead", lead.name, "calls_count") == 2)
	r.check("sync log written", frappe.db.count("CL Sync Log", {"device": d.name}) == 2)

	# row-level access
	frappe.get_doc({"doctype": "CL Team", "team_name": TEAM + " P1", "manager": USERS["manager2"],
		"members": [{"user": USERS["rep2"]}]}).insert()
	call_a = by["a"]["call"]
	r.check("access: owner rep can read their call", frappe.has_permission("CL Call", "read", doc=ca, user=USERS["rep"]))
	r.check("access: another rep cannot read it", not frappe.has_permission("CL Call", "read", doc=ca, user=USERS["rep2"]))
	frappe.set_user(USERS["rep2"])
	r.check("access: another rep's list excludes it", call_a not in frappe.get_list("CL Call", pluck="name"))
	r.check("access: rep2 cannot see rep's lead", lead.name not in frappe.get_list("CL Lead", pluck="name")
		and lead2.name in frappe.get_list("CL Lead", pluck="name"))
	frappe.set_user(USERS["manager"])
	r.check("access: rep's team manager sees the call", call_a in frappe.get_list("CL Call", pluck="name"))
	frappe.set_user(USERS["manager2"])
	r.check("access: a different team's manager does not", call_a not in frappe.get_list("CL Call", pluck="name")
		and lead2.name in frappe.get_list("CL Lead", pluck="name"))
	frappe.set_user(USERS["admin"])
	r.check("access: admin sees everything", call_a in frappe.get_list("CL Call", pluck="name"))
	frappe.set_user("Administrator")

	# outcomes
	frappe.set_user(USERS["rep2"])
	r.check("outcome: another rep cannot set it", raises(lambda: ingest.set_disposition(call_a, "Interested"), "own calls"))
	frappe.set_user(USERS["rep"])
	doc = ingest.set_disposition(call_a, "Interested", "wants a quote")
	frappe.set_user("Administrator")
	r.check("outcome: saved with notes + automatic follow-up", doc.disposition == "Interested" and doc.next_follow_up
		and doc.notes == "wants a quote")
	lv = frappe.db.get_value("CL Lead", lead.name, ["stage", "last_disposition", "next_follow_up"], as_dict=True)
	r.check("outcome: lead moved to Interested with next step", lv.stage == "Interested" and lv.last_disposition == "Interested"
		and lv.next_follow_up)

	# exclusions
	frappe.set_user(USERS["rep"])
	ex = frappe.get_doc({"doctype": "CL Excluded Number", "phone": "9990006666", "user": USERS["rep2"]}).insert()
	r.check("exclusion: a rep's entry is always their own", ex.user == USERS["rep"])
	frappe.set_user("Administrator")
	g = frappe.get_doc({"doctype": "CL Excluded Number", "phone": "9990007777"}).insert()
	r.check("exclusion: rep can read a global entry but not change it",
		frappe.has_permission("CL Excluded Number", "read", doc=g, user=USERS["rep"])
		and not frappe.has_permission("CL Excluded Number", "write", doc=g, user=USERS["rep"]))

	# revoke
	devices.revoke(p["device"])
	r.check("revoke: a revoked phone's key is refused", raises(lambda: devices.authenticate(p["device"], key)))
	r.check("payload: recorder profiles list folders", any("Recordings/Call" in x["folders"] for x in devices.recorder_profiles()))


def phase2(r):
	import hashlib
	import io
	import os

	from frappe.utils import add_days, now_datetime

	from grocall.engine import devices, ingest, retention, storage

	print("Phase 2 — recordings")
	c = devices.new_pairing_code(USERS["rep"])
	info = {"device_uuid": "zzcl-uuid-2", "brand": "samsung", "model": "SM-ZZ2",
		"sim": {"subscription_id": "5", "carrier": "Jio", "last4": "1111"}}
	p = devices.pair(c["code"], info, True)
	d = devices.authenticate(p["device"], p["key"])
	t0 = 1_781_000_000_000
	res = ingest.sync(d, [
		{"ref": "r1", "direction": "outgoing", "number": "9990001212", "started_at": t0, "duration_sec": 300, "sim_subscription_id": "5"},
		{"ref": "r2", "direction": "incoming", "number": "9990001313", "started_at": t0 + 60000, "duration_sec": 20, "sim_subscription_id": "5"},
		{"ref": "r3", "direction": "missed", "number": "9990001414", "started_at": t0 + 120000, "sim_subscription_id": "5"},
		{"ref": "r4", "direction": "outgoing", "number": "9990001515", "started_at": t0 + 180000, "duration_sec": 33, "sim_subscription_id": "5"},
	])
	by = {x["ref"]: x for x in res["results"]}
	r.check("sync tells the phone which calls to upload", by["r1"]["upload"] and not by["r3"]["upload"])
	key1 = frappe.db.get_value("CL Call", by["r1"]["call"], "call_key")
	key2 = frappe.db.get_value("CL Call", by["r2"]["call"], "call_key")

	blob = os.urandom(30 * 1024 * 1024)
	sha = hashlib.sha256(blob).hexdigest()
	MB4 = 4 * 1024 * 1024

	def send(key, off, data, total=len(blob), digest=sha, ext="m4a", dev=d):
		return ingest.receive_chunk(dev, key, off, total, digest, ext, io.BytesIO(data), 300)

	a = send(key1, 0, blob[:MB4])
	r.check("upload: first 4 MB chunk accepted", a["status"] == "partial" and a["received"] == MB4)
	half = send(key1, MB4, blob[MB4:MB4 + MB4 // 2])  # connection drops half-way through chunk 2
	again = send(key1, MB4, blob[MB4:2 * MB4])         # phone retries the whole chunk from its own offset
	r.check("upload: after a dropped connection the server says where to resume",
		again["status"] == "resume" and again["received"] == MB4 + MB4 // 2, again)
	r.check("upload: status call reports the same position",
		ingest.upload_status(d, key1)["received"] == MB4 + MB4 // 2)
	off = again["received"]
	out = None
	while off < len(blob):
		out = send(key1, off, blob[off:off + MB4])
		off = out["received"]
	r.check("upload: 30 MB completes after resuming", out["status"] == "complete" and out["received"] == len(blob))
	call = frappe.get_doc("CL Call", by["r1"]["call"])
	path = storage.abspath(call.recording)
	r.check("upload: call marked Uploaded with size, checksum, length", call.recording_status == "Uploaded"
		and call.recording_size == len(blob) and call.recording_sha256 == sha and call.recording_seconds == 300)
	r.check("upload: file stored privately and intact", os.path.exists(path) and "/private/files/grocall/" in path
		and hashlib.sha256(open(path, "rb").read()).hexdigest() == sha)
	r.check("upload: no File document exposes it", not frappe.db.exists("File", {"file_url": ["like", "%" + call.name + "%"]}))
	r.check("upload: resending a finished upload is harmless", send(key1, 0, blob[:MB4])["status"] == "complete")

	small = os.urandom(1000)
	r.check("upload: checksum mismatch is discarded", raises(lambda: send(key2, 0, small, 1000, "0" * 64), "Checksum"))
	r.check("upload: nothing kept after a bad checksum", ingest.upload_status(d, key2)["received"] == 0)
	r.check("upload: unsupported file type refused", raises(lambda: send(key2, 0, small, 1000, sha, "exe"), "Unsupported"))
	r.check("upload: chunk bigger than declared size refused", raises(lambda: send(key2, 0, small, 10, sha), "declared"))
	send(key2, 0, small, 1000, hashlib.sha256(small).hexdigest())
	r.check("upload: small one-chunk file", frappe.db.get_value("CL Call", by["r2"]["call"], "recording_status") == "Uploaded")

	c2 = devices.new_pairing_code(USERS["rep2"])
	p2 = devices.pair(c2["code"], {**info, "device_uuid": "zzcl-uuid-3"}, True)
	d2 = devices.authenticate(p2["device"], p2["key"])
	r.check("upload: another rep's phone cannot upload to this call", raises(lambda: send(key1, 0, small, dev=d2), "not found"))
	key4 = frappe.db.get_value("CL Call", by["r4"]["call"], "call_key")
	ingest.mark_recording_missing(d, key4, "not_found")
	r.check("phone can report a recording it could not find",
		frappe.db.get_value("CL Call", by["r4"]["call"], "recording_status") == "Not found")

	frappe.set_user(USERS["rep2"])
	r.check("playback: another rep has no read access to the call",
		not frappe.has_permission("CL Call", "read", doc=call, user=USERS["rep2"]))
	frappe.set_user("Administrator")

	# retention
	frappe.db.set_value("CL Call", call.name, "started_at", add_days(now_datetime(), -200))
	old = by["r3"]["call"]
	frappe.db.set_value("CL Call", old, "started_at", add_days(now_datetime(), -1200))
	out = retention.run_nightly(rep=USERS["rep"])
	r.check("retention: old recording deleted, call kept as Purged", not os.path.exists(path)
		and frappe.db.get_value("CL Call", call.name, "recording_status") == "Purged", out)
	r.check("retention: call records past their limit are deleted", not frappe.db.exists("CL Call", old))
	r.check("retention: newer recording untouched", frappe.db.get_value("CL Call", by["r2"]["call"], "recording_status") == "Uploaded")
	r.check("retention: storage figure refreshed", "recordings" in (frappe.db.get_single_value("CL Settings", "storage_used") or ""))
	n = retention.erase_number("09990001313")
	r.check("erasure: one number's recordings removed on request", n == 1
		and frappe.db.get_value("CL Call", by["r2"]["call"], "recording_status") == "Purged")
	def tamper():
		frappe.set_user(USERS["admin"])
		try:
			doc = frappe.get_doc("CL Call", by["r2"]["call"])
			doc.duration_sec = 999
			doc.save()
		finally:
			frappe.set_user("Administrator")
	r.check("evidence: even an admin cannot edit a call's phone-reported details", raises(tamper, "cannot be edited"))
	r.check("purged call refuses a new upload", raises(lambda: send(key1, 0, blob[:MB4]), "not accepted"))


def cleanup():
	frappe.set_user("Administrator")
	for t in (TEAM, TEAM + " P1"):
		if frappe.db.exists("CL Team", t):
			frappe.delete_doc("CL Team", t, force=1, ignore_permissions=True)
	users = list(USERS.values())
	if frappe.db.exists("DocType", "CL Call"):
		from grocall.engine import retention

		for c in frappe.get_all("CL Call", filters={"rep": ["in", users]}, fields=["name", "recording"]):
			retention._delete_file(c.recording)
			frappe.db.delete("CL Playback Log", {"call": c.name})
		for dt, field in (("CL Call", "rep"), ("CL Sync Log", "user"), ("CL Pairing Code", "user"), ("CL Device", "user"),
				("CL Lead", "lead_owner")):
			for n in frappe.get_all(dt, filters={field: ["in", users]}, pluck="name"):
				frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
		for n in frappe.get_all("CL Lead", filters={"lead_name": ["like", "ZZCL%"]}, pluck="name"):
			frappe.delete_doc("CL Lead", n, force=1, ignore_permissions=True)
		for n in frappe.get_all("CL Excluded Number", filters={"e164": ["like", "+91999000%"]}, pluck="name"):
			frappe.delete_doc("CL Excluded Number", n, force=1, ignore_permissions=True)
	for email in USERS.values():
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=1, ignore_permissions=True)
