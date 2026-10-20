# GroCall

Sales call recording & tracking for Frappe. A salesperson's Android phone (GroCall app,
Flutter) syncs the calls made on the **company SIM** and uploads the phone's own call
recording; GroCall matches each call to a lead, asks for an outcome and follow-up, alerts on
missed calls nobody returned, gives managers talk-time and response reports, and can
transcribe and summarise recordings.

- Depends on Frappe only (ERPNext optional, via an adapter).
- Web app: `/calls` · Desk module: **GroCall**
- Install: `bench get-app <repo>` then `bench --site <site> install-app grocall`
- Docs: `docs/` (SPEC, INSTALL, ADMIN, USER, CHANGELOG)

License: MIT
