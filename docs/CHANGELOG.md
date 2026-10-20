# Changelog

Server app and phone app are versioned separately (semantic versioning). Newest first.

## GroCall Android 0.1.0 (2026-10-08): Phase 3, code complete, **not yet built or tested on a phone**

- **Flutter 3.47.6 UI:**
  - setup: QR scan or typed code → the site's consent notice → company-SIM picker → pairing → permissions checklist → brand-specific "turn on automatic call recording" guide;
  - tabs: Today (KPIs, missed calls to return, calls needing an outcome), Calls (filters), outcome screen (outcome chips, note, follow-up date/time, call back), Leads (search, tap to call), Follow-ups (overdue first), Phone (status, Sync now, permission fixes, recorder folders found, fallback recorder switch, unpair).
- **Kotlin, so it runs with the app closed:**
  - **Call log:** the call log is read and filtered to the **company SIM only** (PHONE_ACCOUNT_ID → subscription id; personal-SIM calls are never stored or sent), and excluded numbers are dropped on the phone. A sync runs 8 s after every call ends and every 15 minutes through WorkManager.
  - **Recordings:** recordings are found through the server's recorder profiles (all-files walk, else MediaStore, plus the fallback recorder's own folder) and uploaded in resumable 1 MB chunks with SHA-256. "Not found" or "not available" is reported after 30 minutes.
  - **Notifications:** an after-call notification asks for the outcome, and a missed-call notification is posted.
  - **Device key:** encrypted with an Android Keystore AES key. App backup and device transfer are disabled.
  - **Tier B:** an opt-in accessibility-service microphone recorder for Google-dialer phones.
- **Build:** the GitHub Actions workflow (`.github/workflows/android.yml`) analyzes, tests, builds, signs, verifies the signature and uploads the APK. A `mobile-v*` tag makes a Release.
- **Signing key:** `grocall-release.p12`, created and backed up in two root-only server folders.
- **Verified so far:**
  - `flutter analyze`: no issues;
  - 3 unit tests pass.
- **Not yet:**
  - the Kotlin part has not been compiled (that happens in CI);
  - no APK has been built yet;
  - no real-phone test (PRD Phase 3 ✓ list).

## grocall 0.3.1 (2026-10-08): server support for the app

- Sync results now carry `call_key` and `lead_name`, and duplicates report whether a recording is still wanted.
- Added a public `grocall.api.device.consent` (rate-limited), so the phone can show the site's notice before pairing.
- `pull` leads now include `next_follow_up` and `last_call_at`.

## grocall 0.3.0 (2026-10-08): Phase 2, recordings

- **/apps tile:** GroCall now appears on the Frappe `/apps` screen and opens `/calls`. It's shown only to users with a GroCall role (or System Manager). Checked in a browser for admin and manager (shown) and a user with no role (hidden). Selftest 99/99.

- **Upload:** resumable, offset-based chunks, up to 8 MB each and 150 MB per file. The whole-file SHA-256 is verified, and a bad upload is discarded. `upload_status` and `recording_missing` endpoints were added. Sync now says which calls to upload, and `pull` lists `pending_recordings`.
- **Storage:** files live at `private/files/grocall/YYYY/MM/<call>.<ext>`, so they're in `--with-files` backups. **No File document** points at them, so Frappe's `/private/files` URL refuses them (403).
- **Playback:** `grocall.api.app.recording`.
  - It checks read access on the call and supports HTTP Range (200/206/416), so players can seek.
  - Each listen writes one **CL Playback Log** row (admin-only).
  - A player sits on the CL Call form.
- **Retention:** a nightly job (`engine/retention.py`) does the following:
  - deletes recordings older than the setting and marks the call `Purged`;
  - deletes call rows past their limit;
  - removes upload leftovers older than 2 days;
  - refreshes **Recordings stored** in settings.
- **Right to erasure:** the admin action in `/calls` → Settings deletes every recording for one number.
- **Evidence protection:** phone-reported call details (direction, number, time, duration, salesperson, recording fields) are read-only on the form and refused on save, even for admins.
- **Model upkeep:** the bootstrap now syncs changed or added fields on existing doctypes (it never deletes any), so one `run` updates old sites.
- **Fix:** an over-long first chunk crashed instead of returning a clear error.
- **Checks:**
  - selftest 97/97 (demo and a fresh site);
  - HTTPS upload of a 3.9 MB WAV in chunks with a simulated drop and resume (byte-identical);
  - Range seek, 416 and access checks (another rep 403, guest 403, direct URL 403);
  - browser player plays and seeks to 60 s;
  - walk-through 48/48.

## grocall 0.2.0 (2026-10-08): Phase 1, data model and device sync

- **New doctypes:** CL Lead (+ CL Lead Phone), CL Stage, CL Disposition, CL Call, CL Device, CL Pairing Code, CL Excluded Number, CL Sync Log and CL Recorder Profile.
- **Starter data:** 6 stages, 8 outcomes, and 6 recorder-folder profiles (Samsung, Xiaomi, Oppo/Realme/OnePlus, Vivo, Tecno/Infinix, and a generic one). The profiles are **not yet verified on real phones**.
- **Phone numbers:** one normaliser (`engine/phone.py`). Lead matching tries the exact E.164 number first, then the last 10 digits. Two leads can't share a number.
- **Pairing:** one-time 8-character codes with a QR code (10 minutes, stored hashed), a consent check and a required company SIM. Each device gets its own key (only its hash is stored). Re-pairing rotates the key. Unpair (revoke) is available, and a daily job purges old codes.
- **Device API** (`grocall.api.device`): pair, sync (idempotent, up to 500 per batch, company-SIM and exclusion checks), pull, disposition and heartbeat. See `docs/DEVICE-API.md`.
- **Row-level access:** a rep sees their own calls, leads, phones and logs; a manager sees their team's (plus unassigned leads); an admin sees everything. A rep's new lead is always their own.
- **Outcomes:** the lead's stage moves and the next follow-up is set automatically.
- **Web:** a Phones screen (pair your own phone, or a team member's as a manager or admin, with a QR code and countdown; list with company SIM and tier; admin unpair) and toasts.
- **Checks:** selftest 73/73 (demo and a fresh site), browser walk-through 46/46, and an HTTPS smoke test of every device endpoint.

## grocall 0.1.0 (2026-10-08): Phase 0, foundation

- New standalone app `grocall` (Frappe only), doctype prefix `CL `.
- Roles: CL Sales Rep, CL Sales Manager, CL Admin.
- `CL Settings`, covering company-SIM scope, consent text, missed-call SLA, business hours, retention, and AI keys (encrypted Password fields; AI off by default).
- `CL Team` + `CL Team Member`. Validation rejects duplicate members, members without a GroCall role, and a manager without the manager role.
- Desk workspace **GroCall**.
- `/calls` web app shell (Vue 3 + Tailwind). Role-aware navigation, a desktop sidebar, a phone bottom bar with More, a No-access page, and placeholders naming the phase that fills each screen.
- `grocall.selftest.run` 28/28. Fresh-site install verified.
