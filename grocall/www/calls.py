import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/calls"
		raise frappe.Redirect
	from grocall.api.app import boot_payload

	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep — persist the csrf token for this session
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	context.boot = boot_payload()
	context.brand = context.boot["brand"]
	return context
