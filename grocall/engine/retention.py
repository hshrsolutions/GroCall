"""The only code that deletes recordings (grocall-prd.md §5.2, §7).

Nightly: recordings older than CL Settings.retain_recordings_days are deleted and the call
is marked Purged (the call row stays); call rows older than retain_calls_days are deleted;
half-finished uploads older than 2 days are removed; the storage figure is refreshed.
erase_number() is the admin "right to erasure" action for one phone number."""

import os
import time

import frappe
from frappe.utils import add_days, cint, now_datetime

from grocall.engine import storage
from grocall.engine.phone import normalize

BATCH = 2000


def _delete_file(rel):
	if rel:
		try:
			os.remove(storage.abspath(rel))
		except FileNotFoundError:
			pass


def purge_recording(call, rel):
	_delete_file(rel)
	frappe.db.set_value("CL Call", call, {"recording": "", "recording_status": "Purged",
		"recording_purged_on": now_datetime(), "recording_sha256": ""}, update_modified=False)


def run_nightly(rep=None):
	"""`rep` limits the run to one salesperson's calls (used by the selftest)."""
	s = frappe.get_single("CL Settings")
	out = {"recordings": 0, "calls": 0, "partials": 0}
	only = {"rep": rep} if rep else {}
	days = cint(s.retain_recordings_days)
	if days > 0:
		for c in frappe.get_all("CL Call", filters={**only, "recording_status": "Uploaded",
				"started_at": ["<", add_days(now_datetime(), -days)]}, fields=["name", "recording"], limit=BATCH):
			purge_recording(c.name, c.recording)
			out["recordings"] += 1
	days = cint(s.retain_calls_days)
	if days > 0:
		for c in frappe.get_all("CL Call", filters={**only, "started_at": ["<", add_days(now_datetime(), -days)]},
				fields=["name", "recording"], limit=BATCH):
			_delete_file(c.recording)
			frappe.db.delete("CL Playback Log", {"call": c.name})
			frappe.delete_doc("CL Call", c.name, force=1, ignore_permissions=True)
			out["calls"] += 1
	pdir = os.path.join(storage.base_dir(), storage.PARTIAL)
	if os.path.isdir(pdir):
		for f in os.listdir(pdir):
			p = os.path.join(pdir, f)
			if time.time() - os.path.getmtime(p) > 2 * 86400:
				os.remove(p)
				out["partials"] += 1
	u = storage.usage()
	frappe.db.set_single_value("CL Settings", "storage_used", f"{storage.human(u['bytes'])} in {u['files']} recordings")
	frappe.db.commit()
	return out


def erase_number(phone):
	"""Delete every recording (and later transcript) for one number. Call rows stay, marked Purged."""
	e164 = normalize(phone) or phone
	n = 0
	for c in frappe.get_all("CL Call", filters={"phone": e164, "recording_status": ["in", ["Uploaded", "Pending"]]},
			fields=["name", "recording"]):
		purge_recording(c.name, c.recording)
		n += 1
	frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "CL Settings",
		"reference_name": "CL Settings", "content": f"Erased {n} recordings for {e164} by {frappe.session.user}"}).insert(
		ignore_permissions=True)
	return n
