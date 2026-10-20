"""
Bootstrap for the GroCall data layer (fresh installs).

    bench --site <site> execute grocall.bootstrap_schema.run

Idempotent. Dual path as in grobill/grotex: inserting a DocType on a developer_mode
site exports its JSON to grocall/grocall/doctype/, which `bench migrate` reads
everywhere else. Change the model HERE, then re-export (`sync`).

The model is grocall-prd.md §4. Every doctype is prefixed `CL `. Phase 0 ships the
settings and teams; later phases add their doctypes below.
"""

import frappe

MODULE = "GroCall"

FULL = ["read", "write", "create", "delete", "report", "export", "print", "email", "share"]
EDIT = ["read", "write", "create", "report", "print", "email", "share"]
READ = ["read", "report", "print"]

REP, MANAGER, ADMIN = "CL Sales Rep", "CL Sales Manager", "CL Admin"


def F(fieldname, fieldtype, label=None, **kw):
	d = {"fieldname": fieldname, "fieldtype": fieldtype, "label": label or fieldname.replace("_", " ").title()}
	d.update(kw)
	return d


def sel(*o):
	return "\n".join(o)


class B:
	def __init__(self):
		self.n = 0

	def sb(self, label=None, **kw):
		self.n += 1
		return {"fieldname": f"sb_{self.n}", "fieldtype": "Section Break", **({"label": label} if label else {}), **kw}

	def cb(self):
		self.n += 1
		return {"fieldname": f"cb_{self.n}", "fieldtype": "Column Break"}


RIGHTS = ["read", "write", "create", "delete", "report", "export", "print", "email", "share", "import"]


def perm(role, rights):
	# every right explicit: a DocPerm row defaults write/create/delete to 1
	d = {"role": role, "permlevel": 0}
	for r in RIGHTS:
		d[r] = 1 if r in rights else 0
	return d


def perms(admin=FULL, manager=READ, rep=None):
	rows = [perm("System Manager", FULL), perm(ADMIN, admin)]
	if manager:
		rows.append(perm(MANAGER, manager))
	if rep:
		rows.append(perm(REP, rep))
	return rows


def make_doctype(name, fields, autoname=None, istable=0, issingle=0, permissions=None, title_field=None,
		search_fields=None, description=None):
	if not istable:
		PERMS[name] = permissions or []
	if frappe.db.exists("DocType", name):
		sync_fields(name, fields)
		return
	doc = frappe.new_doc("DocType")
	doc.update({"name": name, "module": MODULE, "custom": 0, "istable": istable, "issingle": issingle,
		"editable_grid": 1 if istable else 0, "track_changes": 0 if istable else 1, "fields": fields,
		"field_order": [f["fieldname"] for f in fields], "permissions": [] if istable else (permissions or []),
		"sort_field": "modified", "sort_order": "DESC"})
	for k, v in (("autoname", autoname), ("title_field", title_field), ("search_fields", search_fields),
			("description", description)):
		if v:
			doc.set(k, v)
	doc.insert(ignore_permissions=True)
	print(f"  created: {name}")


SYNCED_PROPS = ("fieldtype", "label", "options", "read_only", "hidden", "description", "default", "depends_on",
	"in_list_view", "in_standard_filter", "search_index", "unique", "reqd", "collapsible", "fetch_from")


def _norm(v):
	# Frappe stores a Check's empty default as "0"; 0 / "0" / None / "" all mean "not set"
	return "" if v in (None, "", 0, "0") else str(v)


def sync_fields(name, fields):
	"""Bring an existing DocType in line with its definition here: add missing fields in place,
	update changed properties. Never deletes a field (data safety); remove by hand if ever needed."""
	doc = frappe.get_doc("DocType", name)
	by_name = {df.fieldname: df for df in doc.fields}
	ordered, changed, notes = [], False, []
	for f in fields:
		df = by_name.pop(f["fieldname"], None)
		if df is None:
			df = frappe.new_doc("DocField")
			df.update(f)
			changed = True
			notes.append(f"+{f['fieldname']}")
		else:
			for k in SYNCED_PROPS:
				want = f.get(k, 0 if k in ("read_only", "hidden", "in_list_view", "in_standard_filter", "search_index",
					"unique", "reqd", "collapsible") else None)
				have = df.get(k)
				if _norm(want) != _norm(have):
					df.set(k, want)
					changed = True
					notes.append(f"{f['fieldname']}.{k}: {have!r} -> {want!r}")
		ordered.append(df)
	ordered += list(by_name.values())  # fields no longer defined stay, at the end
	if not changed:
		print(f"  up to date: {name}")
		return
	doc.set("fields", [])
	for i, df in enumerate(ordered, 1):
		df.idx = i
		doc.append("fields", df)
	doc.field_order = [df.fieldname for df in ordered]
	doc.save(ignore_permissions=True)
	print(f"  fields synced: {name}: " + "; ".join(notes))


# ---------------------------------------------------------------------------
# Phase 0: settings + teams
# ---------------------------------------------------------------------------

PERMS = {}  # doctype -> permission rows, filled by make_doctype; reset_permissions() re-applies them


def make_settings():
	b = B()
	make_doctype("CL Settings", [
		F("brand_name", "Data", "App Name", default="GroCall"),
		F("brand_accent", "Color", "Brand Colour", default="#0f766e"),
		b.cb(),
		F("default_country_code", "Data", "Default Country Code", default="+91",
			description="Used to turn a 10-digit local number into +91XXXXXXXXXX."),
		b.sb("What the phone syncs", description="Only calls on the company SIM ever leave the phone (grocall-prd.md §2.4)."),
		F("sync_scope", "Select", "Sync Scope", options=sel("Company SIM only"), default="Company SIM only"),
		F("allow_fallback_recorder", "Check", "Allow Fallback Recorder On Google-Dialer Phones", default="0",
			description="Tier B phones: best-effort in-app recorder. Often catches the customer's voice faintly."),
		b.cb(),
		F("consent_text", "Small Text", "Consent Notice Shown At Pairing",
			default="Calls on this company SIM are logged and recorded for sales quality and follow-up. "
			"Recordings are visible to you, your sales manager and the administrator, and are deleted "
			"automatically after the retention period. Personal-SIM calls are never collected."),
		F("customer_announcement", "Small Text", "Suggested Line For Customers",
			default="This call may be recorded for quality and follow-up."),
		b.sb("Missed calls and working hours"),
		F("missed_call_sla_minutes", "Int", "Return A Missed Call Within (Minutes)", default="30"),
		F("escalation_grace_minutes", "Int", "Escalate To Manager After A Further (Minutes)", default="30"),
		b.cb(),
		F("business_start", "Time", "Business Hours From", default="09:30:00"),
		F("business_end", "Time", "Business Hours To", default="19:00:00"),
		F("business_days", "Data", "Business Days", default="Mon,Tue,Wed,Thu,Fri,Sat"),
		b.sb("Retention", description="A nightly job deletes older files and keeps the call row (marked Purged)."),
		F("retain_recordings_days", "Int", "Keep Recordings (Days)", default="180"),
		F("retain_transcripts_days", "Int", "Keep Transcripts (Days)", default="365"),
		b.cb(),
		F("retain_calls_days", "Int", "Keep Call Records (Days)", default="1095"),
		F("storage_used", "Data", "Recordings Stored", read_only=1, description="Updated by the nightly retention job."),
		b.sb("AI transcription and summary", collapsible=1,
			description="Keys stay on the server (encrypted) and are never sent to the phone app."),
		F("auto_transcribe", "Check", "Transcribe New Recordings Automatically", default="0"),
		F("stt_provider", "Select", "Speech-To-Text Provider", options=sel("", "Sarvam AI", "OpenAI", "Deepgram")),
		F("stt_api_key", "Password", "Speech-To-Text API Key"),
		F("min_seconds_to_transcribe", "Int", "Only Calls Longer Than (Seconds)", default="20"),
		b.cb(),
		F("summary_provider", "Select", "Summary Provider", options=sel("", "Anthropic Claude"), default="Anthropic Claude"),
		F("summary_api_key", "Password", "Summary API Key"),
		F("monthly_ai_budget", "Currency", "Monthly AI Budget (INR)", default="0",
			description="0 = AI off. New jobs stop when this month's spend reaches the budget."),
	], issingle=1, permissions=perms(admin=["read", "write", "print", "email", "share"],
		manager=["read", "print"]), description="GroCall site settings")


def make_teams():
	make_doctype("CL Team Member", [
		F("user", "Link", "User", options="User", reqd=1, in_list_view=1),
		F("full_name", "Data", "Name", fetch_from="user.full_name", read_only=1, in_list_view=1),
	], istable=1)
	b = B()
	make_doctype("CL Team", [
		F("team_name", "Data", "Team Name", reqd=1, unique=1),
		F("manager", "Link", "Manager", options="User", reqd=1, in_list_view=1, in_standard_filter=1),
		b.cb(),
		F("disabled", "Check", "Disabled", default="0"),
		b.sb("Members"),
		F("members", "Table", "Members", options="CL Team Member"),
	], autoname="field:team_name", permissions=perms(admin=FULL, manager=READ, rep=["read"]),
		title_field="team_name", search_fields="manager")


# ---------------------------------------------------------------------------
# Phase 1: leads, calls, devices, pairing, exclusions, sync log, recorder profiles
# ---------------------------------------------------------------------------

LEAD_SOURCES = sel("", "Inbound call", "Walk-in", "Website", "Referral", "Advertisement", "Social media", "Cold call",
	"Existing customer", "Other")
DIRECTIONS = sel("Incoming", "Outgoing", "Missed", "Rejected", "Blocked")
RECORDING_STATUS = sel("", "Pending", "Uploaded", "Not found", "Not available", "Excluded", "Purged")


def make_masters():
	make_doctype("CL Stage", [
		F("stage_name", "Data", "Stage", reqd=1, unique=1, in_list_view=1),
		F("sequence", "Int", "Order", in_list_view=1),
		F("is_won", "Check", "Counts As Won", in_list_view=1),
		F("is_lost", "Check", "Counts As Lost", in_list_view=1),
	], autoname="field:stage_name", permissions=perms(admin=FULL, manager=READ, rep=["read"]))
	make_doctype("CL Disposition", [
		F("label", "Data", "Outcome", reqd=1, unique=1, in_list_view=1),
		F("sequence", "Int", "Order"),
		F("enabled", "Check", "Enabled", default="1", in_list_view=1),
		F("connected", "Check", "The Customer Was Reached", in_list_view=1),
		F("needs_follow_up", "Check", "Needs A Follow-up", in_list_view=1),
		F("default_follow_up_days", "Int", "Default Follow-up In (Days)", depends_on="needs_follow_up"),
		F("moves_stage_to", "Link", "Moves The Lead To Stage", options="CL Stage"),
	], autoname="field:label", permissions=perms(admin=FULL, manager=READ, rep=["read"]))
	make_doctype("CL Recorder Profile", [
		F("profile_name", "Data", "Profile", reqd=1, unique=1, in_list_view=1),
		F("enabled", "Check", "Enabled", default="1", in_list_view=1),
		F("priority", "Int", "Priority", default="10", description="Lower is tried first."),
		F("brands", "Small Text", "Brands", description="Android manufacturer names, one per line (lower case), e.g. samsung. "
			"Leave empty for the generic fallback profile."),
		F("folders", "Small Text", "Recording Folders", reqd=1,
			description="Paths under internal storage, one per line, e.g. Recordings/Call. Tried in order."),
		F("filename_regex", "Data", "File Name Pattern (Optional)",
			description="Regex to pull the phone number out of a file name; time matching is always used."),
		F("notes", "Small Text", "Notes"),
	], autoname="field:profile_name", permissions=perms(admin=FULL, manager=READ, rep=["read"]))


def make_leads():
	make_doctype("CL Lead Phone", [
		F("phone", "Data", "Phone", reqd=1, in_list_view=1),
		F("e164", "Data", "Normalised", read_only=1, in_list_view=1, search_index=1),
		F("label", "Select", "Type", options=sel("Mobile", "Office", "WhatsApp", "Other"), default="Mobile", in_list_view=1),
	], istable=1)
	b = B()
	make_doctype("CL Lead", [
		F("lead_name", "Data", "Name", reqd=1, in_list_view=1),
		F("company_name", "Data", "Company"),
		F("primary_phone", "Data", "Primary Phone", read_only=1, in_list_view=1, search_index=1),
		F("email", "Data", "Email", options="Email"),
		F("city", "Data", "City"),
		b.cb(),
		F("stage", "Link", "Stage", options="CL Stage", in_list_view=1, in_standard_filter=1),
		F("source", "Select", "Source", options=LEAD_SOURCES, in_standard_filter=1),
		F("lead_owner", "Link", "Salesperson", options="User", in_standard_filter=1, search_index=1),
		F("next_follow_up", "Datetime", "Next Follow-up"),
		b.sb("Phones"),
		F("phones", "Table", "Phones", options="CL Lead Phone", reqd=1),
		b.sb("Activity"),
		F("last_call_at", "Datetime", "Last Call", read_only=1),
		F("calls_count", "Int", "Calls", read_only=1),
		b.cb(),
		F("last_disposition", "Link", "Last Outcome", options="CL Disposition", read_only=1),
		b.sb("Notes"),
		F("notes", "Text", "Notes"),
	], autoname="CLL-.#####", permissions=perms(admin=FULL, manager=EDIT, rep=EDIT), title_field="lead_name",
		search_fields="primary_phone,company_name,stage")


def make_devices():
	b = B()
	make_doctype("CL Device", [
		F("user", "Link", "Salesperson", options="User", reqd=1, in_list_view=1, in_standard_filter=1, search_index=1),
		F("full_name", "Data", "Name", fetch_from="user.full_name", read_only=1),
		F("enabled", "Check", "Enabled", default="1", in_list_view=1),
		F("support_tier", "Select", "Support Tier", options=sel("", "A", "B"), in_list_view=1,
			description="A = built-in recorder files are reachable; B = Google Phone dialer (tracking, best-effort recording)."),
		b.cb(),
		F("brand", "Data", "Brand", read_only=1),
		F("model", "Data", "Model", read_only=1, in_list_view=1),
		F("os_version", "Data", "Android Version", read_only=1),
		F("app_version", "Data", "App Version", read_only=1),
		F("device_uuid", "Data", "Device ID", read_only=1, search_index=1),
		b.sb("Company SIM", description="Only calls on this SIM are synced. Set by the phone at pairing."),
		F("sim_subscription_id", "Data", "SIM Subscription ID", read_only=1),
		F("sim_carrier", "Data", "Carrier", read_only=1),
		b.cb(),
		F("sim_last4", "Data", "Number (Last 4)", read_only=1),
		F("sim_fingerprint", "Data", "SIM Fingerprint", read_only=1),
		b.sb("Status"),
		F("paired_on", "Datetime", "Paired On", read_only=1),
		F("consent_accepted_on", "Datetime", "Consent Accepted On", read_only=1),
		F("last_seen", "Datetime", "Last Seen", read_only=1),
		F("last_sync", "Datetime", "Last Sync", read_only=1),
		b.cb(),
		F("revoked_on", "Datetime", "Revoked On", read_only=1),
		F("fallback_recorder", "Check", "Fallback Recorder On", read_only=1),
		F("permissions_json", "Small Text", "Phone Permissions", read_only=1),
		F("token_hash", "Data", "Key Hash", read_only=1, hidden=1),
	], autoname="CLD-.#####", permissions=perms(admin=["read", "write", "report", "print"], manager=READ, rep=["read"]),
		title_field="model", search_fields="user,model")
	make_doctype("CL Pairing Code", [
		F("user", "Link", "Salesperson", options="User", reqd=1, in_list_view=1),
		F("code_hash", "Data", "Code Hash", read_only=1),
		F("expires_at", "Datetime", "Expires At", read_only=1, in_list_view=1),
		F("used", "Check", "Used", read_only=1, in_list_view=1),
		F("used_on", "Datetime", "Used On", read_only=1),
		F("device", "Link", "Device", options="CL Device", read_only=1),
	], autoname="hash", permissions=perms(admin=["read", "delete", "report"], manager=None))


def make_calls():
	b = B()
	make_doctype("CL Call", [
		F("title", "Data", "Title", read_only=1, hidden=1),
		F("direction", "Select", "Direction", options=DIRECTIONS, reqd=1, read_only=1, in_list_view=1, in_standard_filter=1),
		F("phone", "Data", "Number", read_only=1, in_list_view=1, search_index=1),
		F("raw_number", "Data", "Number As Dialled", read_only=1),
		F("lead", "Link", "Lead", options="CL Lead", in_standard_filter=1, search_index=1),
		F("lead_name", "Data", "Lead Name", fetch_from="lead.lead_name", read_only=1, in_list_view=1),
		b.cb(),
		F("started_at", "Datetime", "Started At", reqd=1, read_only=1, in_list_view=1, search_index=1),
		F("duration_sec", "Int", "Duration (Seconds)", read_only=1, in_list_view=1),
		F("rep", "Link", "Salesperson", options="User", reqd=1, read_only=1, in_standard_filter=1, search_index=1),
		F("rep_name", "Data", "Salesperson Name", fetch_from="rep.full_name", read_only=1),
		F("device", "Link", "Phone", options="CL Device", read_only=1),
		F("source", "Select", "Source", options=sel("android", "manual"), default="android", read_only=1),
		F("call_key", "Data", "Call Key", unique=1, read_only=1, hidden=1),
		b.sb("Outcome"),
		F("disposition", "Link", "Outcome", options="CL Disposition", in_standard_filter=1),
		F("connected", "Check", "Connected", read_only=1),
		F("next_follow_up", "Datetime", "Next Follow-up"),
		b.cb(),
		F("notes", "Small Text", "Notes"),
		F("dispositioned_on", "Datetime", "Outcome Recorded On", read_only=1),
		b.sb("Recording"),
		F("recording_status", "Select", "Recording", options=RECORDING_STATUS, read_only=1, in_standard_filter=1),
		F("recording_uploaded_on", "Datetime", "Uploaded On", read_only=1),
		F("recording_purged_on", "Datetime", "Deleted On (Retention)", read_only=1),
		b.cb(),
		F("recording_seconds", "Int", "Recording Length (Seconds)", read_only=1),
		F("recording_size", "Int", "Recording Size (Bytes)", read_only=1),
		F("recording", "Data", "Stored File", read_only=1, hidden=1,
			description="Path under the site's private files. Never served directly: play it from the call."),
		F("recording_sha256", "Data", "Recording Checksum", read_only=1, hidden=1),
		b.sb("AI", collapsible=1),
		F("transcript_status", "Select", "Transcript", options=sel("", "Queued", "Done", "Failed", "Skipped"), read_only=1),
		F("sentiment", "Select", "Sentiment", options=sel("", "Positive", "Neutral", "Negative"), read_only=1),
		F("summary", "Text", "Summary", read_only=1),
	], autoname="CALL-.YY.MM.-.#####", permissions=perms(admin=FULL, manager=["read", "write", "report", "print", "export"],
		rep=["read", "write", "report", "print"]), title_field="title", search_fields="phone,lead_name,rep")


def make_support():
	make_doctype("CL Excluded Number", [
		F("phone", "Data", "Phone", reqd=1, in_list_view=1),
		F("e164", "Data", "Normalised", read_only=1, search_index=1),
		F("user", "Link", "Only For This Salesperson", options="User", in_list_view=1,
			description="Leave empty to exclude the number for everyone."),
		F("reason", "Data", "Reason", in_list_view=1),
	], autoname="hash", permissions=perms(admin=FULL, manager=READ, rep=["read", "write", "create", "delete"]))
	make_doctype("CL Playback Log", [
		F("call", "Link", "Call", options="CL Call", reqd=1, in_list_view=1, search_index=1),
		F("user", "Link", "Listened By", options="User", in_list_view=1, in_standard_filter=1),
		F("played_at", "Datetime", "When", in_list_view=1),
		F("ip", "Data", "IP Address"),
		F("rep", "Link", "Call Belongs To", options="User", in_standard_filter=1),
	], autoname="hash", permissions=perms(admin=["read", "report", "export"], manager=None))
	make_doctype("CL Sync Log", [
		F("device", "Link", "Phone", options="CL Device", in_list_view=1, in_standard_filter=1),
		F("user", "Link", "Salesperson", options="User", in_list_view=1, in_standard_filter=1),
		F("app_version", "Data", "App Version"),
		F("received", "Int", "Received", in_list_view=1),
		F("created_count", "Int", "Created", in_list_view=1),
		F("duplicates", "Int", "Duplicates", in_list_view=1),
		F("excluded", "Int", "Excluded", in_list_view=1),
		F("errors", "Int", "Errors", in_list_view=1),
		F("details", "Long Text", "Details (JSON)"),
	], autoname="hash", permissions=perms(admin=["read", "delete", "report", "export"], manager=READ))


def make_workspace():
	if frappe.db.exists("Workspace", "GroCall"):
		return
	ws = frappe.new_doc("Workspace")
	ws.update({"label": "GroCall", "title": "GroCall", "module": MODULE, "public": 1, "icon": "call",
		"content": frappe.as_json([
			{"id": "gc-h", "type": "header", "data": {"text": "<span class=\"h4\"><b>GroCall</b></span>", "col": 12}},
			{"id": "gc-s1", "type": "shortcut", "data": {"shortcut_name": "Open GroCall", "col": 3}},
			{"id": "gc-s2", "type": "shortcut", "data": {"shortcut_name": "CL Team", "col": 3}},
			{"id": "gc-s3", "type": "shortcut", "data": {"shortcut_name": "CL Settings", "col": 3}},
		]),
		"shortcuts": [
			{"label": "Open GroCall", "type": "URL", "url": "/calls", "color": "Green"},
			{"label": "CL Team", "type": "DocType", "link_to": "CL Team"},
			{"label": "CL Settings", "type": "DocType", "link_to": "CL Settings"},
		],
		"roles": [{"role": r} for r in ("CL Admin", "CL Sales Manager", "System Manager")]})
	ws.insert(ignore_permissions=True)
	print("  created: Workspace GroCall")


def run():
	make_settings()
	make_teams()
	make_masters()
	make_leads()
	make_devices()
	make_calls()
	make_support()
	make_workspace()
	ensure_workspace_links()
	frappe.db.commit()


WORKSPACE_LINKS = ["CL Call", "CL Lead", "CL Device", "CL Disposition", "CL Stage", "CL Recorder Profile",
	"CL Excluded Number", "CL Sync Log", "CL Playback Log"]


def ensure_workspace_links():
	"""Add a shortcut per doctype introduced after Phase 0 (idempotent)."""
	ws = frappe.get_doc("Workspace", "GroCall")
	have = {s.link_to for s in ws.shortcuts}
	content = frappe.parse_json(ws.content or "[]")
	changed = False
	for dt in WORKSPACE_LINKS:
		if dt in have or not frappe.db.exists("DocType", dt):
			continue
		ws.append("shortcuts", {"label": dt, "type": "DocType", "link_to": dt})
		content.append({"id": "gc-" + frappe.scrub(dt), "type": "shortcut", "data": {"shortcut_name": dt, "col": 3}})
		changed = True
	if changed:
		ws.content = frappe.as_json(content)
		ws.save(ignore_permissions=True)
		print("  workspace shortcuts updated")


def reset_permissions():
	"""Re-apply the permission rows defined above to existing doctypes (then run sync to export)."""
	PERMS.clear()
	make_settings()
	make_teams()
	make_masters()
	make_leads()
	make_devices()
	make_calls()
	make_support()
	for name, rows in PERMS.items():
		doc = frappe.get_doc("DocType", name)
		doc.set("permissions", rows)
		doc.save(ignore_permissions=True)
		print(f"  permissions reset: {name}")
	frappe.db.commit()


def sync():
	"""Re-export every CL doctype's JSON after a model change (developer_mode sites)."""
	from frappe.modules.export_file import export_to_files

	names = frappe.get_all("DocType", filters={"module": MODULE}, pluck="name")
	export_to_files(record_list=[["DocType", n] for n in names] + [["Workspace", "GroCall"]], record_module=MODULE)
	print(f"exported {len(names)} doctypes + workspace")
