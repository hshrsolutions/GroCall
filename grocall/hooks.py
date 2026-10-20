app_name = "grocall"
app_title = "GroCall"
app_publisher = "HSHR Solutions"
app_description = "Sales call recording & tracking: company-SIM call log, recordings, follow-ups, missed-call alerts, reports, AI summaries"
app_email = "support@hshrsolutions.com"
app_license = "mit"

# Tile on the /apps screen; shown only to people with a GroCall role (or System Manager).
add_to_apps_screen = [
	{
		"name": "grocall",
		"logo": "/assets/grocall/icon.svg",
		"title": "GroCall",
		"route": "/calls",
		"has_permission": "grocall.api.app.has_app_permission",
	}
]

website_route_rules = [
	{"from_route": "/calls", "to_route": "calls"},
	{"from_route": "/calls/<path:app_path>", "to_route": "calls"},
]

after_install = "grocall.install.after_install"
after_migrate = "grocall.install.after_migrate"
before_uninstall = "grocall.install.before_uninstall"

# Doctype controllers stay stubs; every rule lives in grocall.engine (grocall-prd.md §5).
doc_events = {
	"CL Team": {"validate": "grocall.engine.teams.team_validate"},
	"CL Lead": {"validate": "grocall.engine.leads.lead_validate"},
	"CL Call": {"validate": "grocall.engine.ingest.call_validate"},
	"CL Excluded Number": {"validate": "grocall.engine.leads.excluded_validate"},
}

# Row-level access (grocall-prd.md §3): rep = own, manager = team, admin = all.
_A = "grocall.engine.access"
permission_query_conditions = {
	"CL Call": f"{_A}.call_query",
	"CL Lead": f"{_A}.lead_query",
	"CL Device": f"{_A}.device_query",
	"CL Sync Log": f"{_A}.sync_log_query",
	"CL Excluded Number": f"{_A}.excluded_query",
}
has_permission = {dt: f"{_A}.has_permission" for dt in permission_query_conditions}

# Extension points other apps may declare (grocall-prd.md §6), wired from Phase 1 on:
#   grocall_call_created = ["myapp.crm.on_call"]            fn(call)         — errors logged, never block
#   grocall_call_dispositioned = [...]                      fn(call)
#   grocall_missed_call_alert = [...]                       fn(alert)
#   grocall_lead_resolver = ["myapp.crm.resolve_number"]    fn(e164) -> {"doctype", "name", "label"} | None

scheduler_events = {
	"daily": ["grocall.engine.devices.purge_codes", "grocall.engine.retention.run_nightly"],
}
