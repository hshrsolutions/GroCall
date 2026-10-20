"""Roles and small helpers shared by the engine and the API."""

import frappe

REP, MANAGER, ADMIN = "CL Sales Rep", "CL Sales Manager", "CL Admin"
ALL_ROLES = (REP, MANAGER, ADMIN)


def roles(user=None):
	return set(frappe.get_roles(user or frappe.session.user))


def perms(user=None):
	"""What the signed-in user may do in GroCall. System Manager counts as admin."""
	r = roles(user)
	admin = ADMIN in r or "System Manager" in r
	manager = admin or MANAGER in r
	rep = manager or REP in r
	return {"rep": rep, "manager": manager, "admin": admin}


def settings():
	return frappe.get_cached_doc("CL Settings")
