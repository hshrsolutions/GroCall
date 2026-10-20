"""Row-level access (grocall-prd.md §3): a rep sees their own rows, a manager their team's,
an admin everything. Wired through permission_query_conditions / has_permission."""

import frappe

from grocall.engine.common import perms

# doctype -> the field holding the owning salesperson
OWNER_FIELD = {"CL Call": "rep", "CL Lead": "lead_owner", "CL Device": "user", "CL Sync Log": "user"}


def visible_users(user=None):
	"""None = everyone (admin). Otherwise the set of salespeople whose rows `user` may see."""
	user = user or frappe.session.user
	p = perms(user)
	if p["admin"]:
		return None
	users = {user}
	if p["manager"]:
		teams = frappe.get_all("CL Team", filters={"manager": user, "disabled": 0}, pluck="name")
		if teams:
			users |= set(frappe.get_all("CL Team Member", filters={"parent": ["in", teams], "parenttype": "CL Team"},
				pluck="user"))
	return users


def _cond(doctype, user):
	users = visible_users(user)
	if users is None:
		return ""
	field = OWNER_FIELD[doctype]
	inlist = ", ".join(frappe.db.escape(u) for u in sorted(users))
	cond = f"`tab{doctype}`.`{field}` in ({inlist})"
	if doctype == "CL Lead" and perms(user)["manager"]:
		cond = f"({cond} or ifnull(`tabCL Lead`.`lead_owner`, '') = '')"  # managers also see unassigned leads
	return cond


def call_query(user=None):
	return _cond("CL Call", user or frappe.session.user)


def lead_query(user=None):
	return _cond("CL Lead", user or frappe.session.user)


def device_query(user=None):
	return _cond("CL Device", user or frappe.session.user)


def sync_log_query(user=None):
	return _cond("CL Sync Log", user or frappe.session.user)


def excluded_query(user=None):
	user = user or frappe.session.user
	if perms(user)["manager"]:
		return ""
	return f"ifnull(`tabCL Excluded Number`.`user`, '') in ('', {frappe.db.escape(user)})"


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	users = visible_users(user)
	if users is None:
		return True
	if doc.doctype == "CL Excluded Number":
		if ptype == "create":
			return True  # excluded_validate pins a rep's entry to themselves
		if not doc.get("user"):
			return ptype in (None, "read", "print", "report") or perms(user)["admin"]
		return doc.user == user or (perms(user)["manager"] and ptype in (None, "read", "report"))
	owner = doc.get(OWNER_FIELD[doc.doctype])
	if doc.doctype == "CL Lead" and not owner:
		return perms(user)["manager"] or (ptype == "create")
	if doc.doctype == "CL Lead" and ptype == "create":
		return True
	return owner in users
