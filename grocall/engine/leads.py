"""CL Lead rules and number → lead matching."""

import frappe
from frappe import _

from grocall.engine.phone import last10, normalize


def lead_validate(doc, method=None):
	from grocall.engine.common import perms

	user = frappe.session.user
	if user not in ("Guest", "Administrator") and not perms(user)["manager"]:
		doc.lead_owner = user  # a rep's leads are always their own; managers assign
	elif not doc.lead_owner and user not in ("Guest", "Administrator"):
		doc.lead_owner = user
	if not doc.stage and frappe.db.exists("CL Stage", "New"):
		doc.stage = "New"
	seen = set()
	for row in doc.phones:
		row.e164 = normalize(row.phone)
		if not row.e164:
			frappe.throw(_("Row {0}: {1} is not a valid phone number.").format(row.idx, row.phone))
		if row.e164 in seen:
			frappe.throw(_("{0} is listed twice.").format(row.phone))
		seen.add(row.e164)
		other = frappe.db.sql("""select p.parent, l.lead_name from `tabCL Lead Phone` p
			join `tabCL Lead` l on l.name = p.parent where p.e164 = %s and p.parent != %s limit 1""",
			(row.e164, doc.name or ""), as_dict=True)
		if other:
			frappe.throw(_("{0} already belongs to lead {1} ({2}).").format(row.phone, other[0].parent, other[0].lead_name))
	doc.primary_phone = doc.phones[0].e164 if doc.phones else None


def match_lead(e164, rep=None):
	"""Lead for a number: exact E.164 first, then the last 10 digits; the rep's own lead wins a tie."""
	if not e164:
		return None
	rows = frappe.db.sql("""select p.parent, l.lead_owner from `tabCL Lead Phone` p join `tabCL Lead` l on l.name = p.parent
		where p.parenttype = 'CL Lead' and p.e164 = %s""", (e164,), as_dict=True)
	if not rows:
		tail = last10(e164)
		if len(tail) == 10:
			rows = frappe.db.sql("""select p.parent, l.lead_owner from `tabCL Lead Phone` p join `tabCL Lead` l
				on l.name = p.parent where p.parenttype = 'CL Lead' and p.e164 like %s""", ("%" + tail,), as_dict=True)
	if not rows:
		return None
	own = [r for r in rows if rep and r.lead_owner == rep]
	return (own or rows)[0].parent


def excluded_numbers(user):
	"""E.164 numbers never tracked for this user (their own list + everyone's)."""
	return set(frappe.db.sql_list("""select e164 from `tabCL Excluded Number`
		where ifnull(user, '') in ('', %s)""", (user,)))


def excluded_validate(doc, method=None):
	doc.e164 = normalize(doc.phone)
	if not doc.e164:
		frappe.throw(_("{0} is not a valid phone number.").format(doc.phone))
	from grocall.engine.common import perms

	if not perms()["admin"]:
		doc.user = frappe.session.user  # reps may only exclude numbers for themselves
