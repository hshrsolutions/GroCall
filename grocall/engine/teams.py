"""CL Team rules: one manager, no duplicate members, members must hold a GroCall role."""

import frappe
from frappe import _

from grocall.engine.common import ALL_ROLES, roles


def team_validate(doc, method=None):
	seen = set()
	for row in doc.members:
		if row.user in seen:
			frappe.throw(_("{0} is listed twice in this team.").format(row.user))
		seen.add(row.user)
		if not roles(row.user) & set(ALL_ROLES):
			frappe.throw(_("{0} has no GroCall role. Give them CL Sales Rep (or Manager) first.").format(row.user))
	if doc.manager and not roles(doc.manager) & {"CL Sales Manager", "CL Admin", "System Manager"}:
		frappe.throw(_("The team manager {0} needs the CL Sales Manager role.").format(doc.manager))


def teams_of(user):
	"""Teams a user manages or belongs to (used by row-level access from Phase 1)."""
	managed = frappe.get_all("CL Team", filters={"manager": user, "disabled": 0}, pluck="name")
	member = frappe.get_all("CL Team Member", filters={"user": user, "parenttype": "CL Team"}, pluck="parent")
	return {"managed": managed, "member": sorted(set(member))}
