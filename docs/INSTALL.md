# Installing GroCall

GroCall needs **Frappe v15 only**. ERPNext is optional (it adds the Lead/Customer link later).

## Server

```bash
cd ~/frappe-bench
bench get-app <grocall repo URL>
bench --site <site> install-app grocall
bench build --app grocall
sudo supervisorctl restart <bench>-web:      # only your bench's web group
```

Nothing else: no SQL, no config edits. The install creates:

- roles **CL Sales Rep**, **CL Sales Manager**, **CL Admin**
- **CL Settings** with safe defaults (AI off, company-SIM-only sync, 30-minute missed-call limit, 180-day recordings)
- **CL Team**, the Desk workspace **GroCall**, and the web app at **`/calls`**

Updating: `bench update --apps grocall` (or `git pull` + `bench --site <site> migrate` + `bench build --app grocall`).

## Building the web app (developers)

```bash
sudo -u frappe bash -lc 'cd apps/grocall/frontend && yarn install && yarn build'
```

Always build as the bench user (`frappe`), never root.

## Checking an install

```bash
bench --site <test site> set-config allow_tests 1
bench --site <test site> execute grocall.selftest.run      # TEST SITES ONLY — writes and removes rows
```

## Phone app

The Android app (Flutter) arrives in Phase 3, distributed as a signed APK from `/calls/download`. See `ADMIN.md`.
