import frappe

ROLES = [
	{"role_name": "CL Sales Rep", "desk_access": 0,
		"description": "Salesperson: own calls, recordings, leads and follow-ups; pairs their own phone."},
	{"role_name": "CL Sales Manager", "desk_access": 1,
		"description": "Team lead: everything for their CL Team, dashboards, plays team recordings."},
	{"role_name": "CL Admin", "desk_access": 1,
		"description": "Owner/admin: settings, devices, teams, recorder profiles, AI, retention; all data."},
]


def after_install():
	create_roles()
	from grocall.bootstrap_schema import run as bootstrap

	bootstrap()
	seed()
	frappe.db.commit()


def after_migrate():
	create_roles()
	from grocall.bootstrap_schema import ensure_workspace_links

	if frappe.db.exists("Workspace", "GroCall"):
		ensure_workspace_links()
	seed()
	frappe.db.commit()


def create_roles():
	for r in ROLES:
		if not frappe.db.exists("Role", r["role_name"]):
			frappe.get_doc({"doctype": "Role", **r}).insert(ignore_permissions=True)


# Starter masters: inserted once if missing, never overwritten (customers edit them).
STAGES = [("New", 1, 0, 0), ("Contacted", 2, 0, 0), ("Interested", 3, 0, 0), ("Negotiation", 4, 0, 0),
	("Won", 5, 1, 0), ("Lost", 6, 0, 1)]
# label, connected, needs_follow_up, follow-up days, moves stage to
DISPOSITIONS = [
	("Interested", 1, 1, 2, "Interested"),
	("Call back later", 1, 1, 1, "Contacted"),
	("Sent details / quote", 1, 1, 2, "Negotiation"),
	("Order confirmed", 1, 0, 0, "Won"),
	("Not interested", 1, 0, 0, "Lost"),
	("Wrong number", 1, 0, 0, None),
	("No answer", 0, 1, 1, None),
	("Busy / switched off", 0, 1, 1, None),
]
# Folder paths differ between OS versions; they are data so a new path needs no app release.
# UNVERIFIED on real phones until the Phase 3 device check; adjust here when a phone reports otherwise.
RECORDER_PROFILES = [
	("Samsung", 10, "samsung", "Recordings/Call\nCall\nSounds/Call", None),
	("Xiaomi / Redmi / POCO", 10, "xiaomi\nredmi\npoco", "MIUI/sound_recorder/call_rec\nRecordings/Call\nRecordings/call_rec", None),
	("Oppo / Realme / OnePlus", 10, "oppo\nrealme\noneplus",
		"Music/Recordings/Call Recordings\nRecordings/Call Recordings\nRecord/PhoneRecord\nRecordings/PhoneRecord", None),
	("Vivo / iQOO", 10, "vivo\niqoo", "Recordings/Record/Call\nRecord/Call\nRecordings/Call", None),
	("Tecno / Infinix / itel", 10, "tecno\ninfinix\nitel", "Recordings/Call\nRecord/Call\nPhoneRecord", None),
	("Generic fallback", 90, "", "Recordings/Call\nRecordings/Call Recordings\nRecord/Call\nCall\nRecordings\nMusic/Recordings", None),
]


def seed():
	if not frappe.db.exists("DocType", "CL Settings"):
		return
	if not frappe.db.get_single_value("CL Settings", "brand_name"):
		# save the documented defaults once, so an unticked box later really means off
		s = frappe.get_single("CL Settings")
		for f in s.meta.fields:
			if f.default and s.get(f.fieldname) in (None, "", 0):
				s.set(f.fieldname, f.default)
		s.save(ignore_permissions=True)
	if frappe.db.exists("DocType", "CL Stage"):
		for name, seq, won, lost in STAGES:
			if not frappe.db.exists("CL Stage", name):
				frappe.get_doc({"doctype": "CL Stage", "stage_name": name, "sequence": seq, "is_won": won,
					"is_lost": lost}).insert(ignore_permissions=True)
	if frappe.db.exists("DocType", "CL Disposition"):
		for i, (label, conn, fu, days, stage) in enumerate(DISPOSITIONS, 1):
			if not frappe.db.exists("CL Disposition", label):
				frappe.get_doc({"doctype": "CL Disposition", "label": label, "sequence": i, "enabled": 1, "connected": conn,
					"needs_follow_up": fu, "default_follow_up_days": days, "moves_stage_to": stage}).insert(
					ignore_permissions=True)
	if frappe.db.exists("DocType", "CL Recorder Profile"):
		for name, prio, brands, folders, rx in RECORDER_PROFILES:
			if not frappe.db.exists("CL Recorder Profile", name):
				frappe.get_doc({"doctype": "CL Recorder Profile", "profile_name": name, "priority": prio, "enabled": 1,
					"brands": brands, "folders": folders, "filename_regex": rx,
					"notes": "Starter profile, not yet verified on a real phone."}).insert(ignore_permissions=True)


def before_uninstall():
	"""Roles are left in place (users may still hold them); the module's doctypes go with the app."""
	frappe.cache.delete_value("grocall_boot")
