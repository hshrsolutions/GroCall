# GroCall — Sales Call Recording & Tracking — SPEC

> Seeded from `grocall-prd.md` at Phase 0 (2026-10-08). From here on this file is owned by the app
> and ships with it; the bench-root PRD stays the original contract.

| | |
|---|---|
| App | `grocall` (new, standalone) · doctype prefix `CL ` · custom-field prefix `cl_` (adapter only) · web app at `/calls` |
| Companion | Android app **GroCall** (`apps/grocall/mobile/`, **Flutter**, with small Kotlin platform channels) — the only thing that touches the phone |
| Depends on | **Frappe only.** ERPNext is optional: when it is installed, the Phase-8 adapter links calls to Lead / Customer / Opportunity / Contact |
| Not related to | HRMS / GroHR. Users are sales staff and sales managers, not employees-as-HR-records |
| Bench | **demo-bench only** (`demo.grohrms.cloud`) until a customer is named |
| Written | 2026-10-08 |
| Status | PRD written; revised 2026-10-08 (company SIM, Flutter, all-Android tiers) · Phase 0 not started · questions in §11 |
| Companion docs | `grocall-architecture.md` (status + decisions) · `apps/grocall/docs/SPEC.md` (seeded at Phase 0) |

---

## 1. What it is, and what it is not

GroCall gives a sales team's owner one answer to "**who called whom, what was said, and
what happens next**". Each salesperson carries an Android phone running the GroCall app.
The app reads the phone's call log and uploads the recording that the phone's own
recorder made. Frappe matches every call to a lead, prompts the rep for an outcome and
a follow-up, and raises an alert for any missed call nobody has returned. It also
transcribes and summarises the recording, and gives managers talk-time and response
reports.

**Decisions taken 2026-10-08 (user):**
- **The call source is the salesperson's Android phone.** There is no cloud telephony in v1. Manual upload remains as a fallback.
- **v1 scope:** call log + recordings + playback; follow-ups and missed-call alerts; manager dashboard and reports; AI transcription and summary.
- **Only the company SIM is tracked (2026-10-08).** Each salesperson's phone has a separate company SIM. GroCall syncs and uploads recordings **only for calls on that SIM**; calls on the personal SIM never leave the phone.
- **All Android brands (2026-10-08).** Call tracking works on every Android phone. Recording comes in tiers (§2.2) because of what each brand's dialer allows.
- **Phone app in Flutter (2026-10-08).** The app authenticates with a **per-device API key** issued when it pairs. AI provider keys stay on the server and never go in the app (§5.9).
- **Sales base (assumed, confirm in §11-Q1):** a standalone core with its own light `CL Lead`, plus an optional ERPNext adapter. This is the same standalone-first rule as GroBill and GroChit, so the app sells to customers with or without ERPNext.

**What it is not:**
- **It is not a dialer or telephony provider.** Calls go over the rep's normal SIM. A cloud-telephony source (Exotel, Knowlarity, MyOperator, Twilio) is a later *source adapter*, not v1.
- **It is not an HR or attendance tool.** It does not track location, working hours or employee discipline. Call data is sales data.
- **It is not a full CRM.** `CL Lead` is just enough pipeline to give a call context (name, stage, owner, next step). Customers who need more use ERPNext, through the adapter, or HSHR later.
- **It has no iPhone support.** iOS gives third-party apps no access to the call log or call audio. That is a platform limit, not a missing feature.

## 2. The hard platform facts (read before designing anything)

1. **Android 10+ blocks third-party apps from recording call audio.** GroCall therefore **does not record**. The phone's **built-in call recorder** records, and GroCall finds that file and uploads it. This is how every Indian sales-call product (Callyzer, TeleCRM and others) works today.
2. **Which built-in recorders work depends on the brand:**

   | Phone family | Built-in recorder | File reachable by GroCall? |
   |---|---|---|
   | Samsung (One UI) | Yes, with an "auto-record calls" setting | **Yes** (`Recordings/Call/`) |
   | Xiaomi / Redmi / POCO (MIUI / HyperOS, own dialer) | Yes | **Yes** (`MIUI/sound_recorder/call_rec/`) |
   | Oppo / Realme / OnePlus (ColorOS / OxygenOS 12+) | Yes | **Yes** (`Music/Recordings/Call Recordings/`, varies by version) |
   | Vivo / iQOO | Yes | **Yes** (`Recordings/Record/Call/`, varies) |
   | Phones on the **Google Phone** dialer (Pixel, Motorola, Nokia, newer Xiaomi/Realme models in some regions) | Some regions, with a spoken "this call is being recorded" announcement | **No.** The files stay in Google Phone's private storage |

   **Support tiers (for "all Android phones"):**
   - **Tier A, full:** the dialer stores recordings in shared storage (Samsung, Xiaomi/Redmi/POCO, Oppo/Realme/OnePlus, Vivo/iQOO, Tecno/Infinix/itel, Lava and most other own-dialer brands). Calls, recordings, AI and every other feature work.
   - **Tier B, tracking + best-effort recording:** phones on the Google Phone dialer. Calls, follow-ups, missed-call alerts and reports all work. GroCall offers an *optional* in-app fallback recorder (an accessibility service plus the microphone, the method Cube ACR uses). It works on many but not all models, often captures the customer's voice only faintly unless the speaker is on, and does not work at all on some devices. Calls with no recording still sync, marked `Not available`.
   - **Tip for the customer:** when buying company phones, pick a Tier A brand.

   The diagnostics screen tells each phone which tier it is in on first launch.

   Folder paths change between OS versions. They are **data** (`CL Recorder Profile` rows), not constants in the app, so a new path is a settings change, not an app release. A call whose recording cannot be found still syncs, with `recording_status = Not found`.
3. **Google Play restricts `READ_CALL_LOG` to default dialer apps.** GroCall is distributed as a **signed APK that we host** (`/calls/download`), or through the customer's MDM. It is not on the Play Store. The signing key is generated by us and backed up in two places from day one. (The Tracking app lost its key; that must not happen here.)
4. **Company-SIM filter.** Android's call log records which SIM each call used (`PHONE_ACCOUNT_ID` / subscription id). At pairing, the rep picks the company SIM; the app stores its subscription id and ICCID-derived fingerprint and filters **on the phone**. A recording is uploaded only when it matches, by time and number, a call that passed the filter. If the company SIM is removed or swapped, the app pauses syncing and the device shows a warning to the admin.
5. **Background limits.** Android delays background work. The app syncs right after each call ends (a phone-state listener) and also every 15 minutes through WorkManager, which is the minimum interval. "Real time" means within seconds of the call ending when the phone is online, otherwise at the next sync.
6. **Recording calls is legal in India; the other party should be told.** GroCall ships an announcement script, a per-site consent notice, retention limits, and a playback audit log so a customer can meet the DPDP Act 2023 (§7).

## 3. Users and roles

| Role | Who | Can |
|---|---|---|
| `CL Sales Rep` | A salesperson with the app | See **own** calls, recordings, leads and follow-ups; add outcomes and notes |
| `CL Sales Manager` | Team lead / sales head | Everything for **their team** (`CL Team`); dashboards; reassign leads; play any team recording |
| `CL Admin` | Owner / admin | Settings, devices, teams, recorder profiles, AI provider, retention, purge; all data |

Row-level access follows the owner (`rep`) and `CL Team` through `permission_query_conditions` and `has_permission`. Rules: a rep never sees another rep's recordings, and every playback is logged (`CL Playback Log`).

## 4. Data model (`CL ` doctypes)

| Doctype | Purpose | Key fields |
|---|---|---|
| `CL Settings` (single) | Site switches | consent text, retention days (recordings / transcripts / metadata), missed-call SLA minutes, business hours, sync scope (*company SIM only*, default and the only v1 option; later *company SIM + known leads*), allow fallback recorder (Tier B), auto-transcribe switch, AI provider + monthly budget, default country code |
| `CL Team` | Sales team | manager (User), members (child `CL Team Member`) |
| `CL Device` | A paired phone | user, device_uuid, model, OS, app version, token hash, company SIM (subscription id, carrier, last 4 digits of the number, SIM fingerprint), support tier (A / B), fallback recorder on, paired_on, last_sync, permissions snapshot (call log / storage / notifications), recorder profile, enabled |
| `CL Pairing Code` | One-time QR/code to pair a phone | user, code hash, expires_at (10 min), used |
| `CL Recorder Profile` | Where a phone brand stores recordings | brand/OS match, folder globs, filename pattern (number/time regex), timezone handling |
| `CL Lead` | Light sales record | lead_name, phones (child `CL Lead Phone`, normalized E.164), company, source, stage (`CL Stage` link), owner (rep), next_follow_up, last_call_at, erp_link (dynamic link, adapter-filled) |
| `CL Stage` | Pipeline stages (master) | label, order, is_won, is_lost |
| `CL Call` | One call (the core record) | call_key (unique dedupe key: device + start + number + duration), direction (Incoming / Outgoing / Missed / Rejected / Blocked), phone (E.164) + raw number, started_at, duration_sec, rep, device, lead, disposition, notes, follow_up (link), recording (private File), recording_status (Pending / Uploaded / Not found / Excluded / Purged), transcript_status, summary, sentiment, returned_by_call (for missed calls), source (`android` / `manual`; telephony later) |
| `CL Disposition` | Outcome master | label, connected (bool), needs_follow_up (bool), default_follow_up_days, moves_stage_to |
| `CL Follow Up` | A promised next action | lead, call, rep, due_at, type (Call / Visit / WhatsApp / Email), status (Open / Done / Missed / Cancelled), done_by_call |
| `CL Missed Call Alert` | A missed incoming call awaiting a return call | call, rep, sla_due_at, status (Open / Returned / Expired / Ignored), returned_call, escalated_to |
| `CL Transcript` | AI output | call, language, text, segments (JSON: speaker, start, end, text), summary, action items, sentiment, keywords, provider, model, audio seconds, cost |
| `CL Excluded Number` | Never track this number (personal) | phone, user (blank = everyone), reason |
| `CL Playback Log` | Who listened to what | call, user, at, ip |
| `CL Sync Log` | Per-batch device sync result | device, received, created, duplicates, errors (JSON) |

All phone numbers are normalized to E.164 in **one** function (`engine/phone.py`). Matching tries an exact E.164 match first, then the last 10 digits.

## 5. Engine and binding rules

1. **New, separate app.** Never modify `frappe`, `erpnext`, `hrms`, `hshr`, `gro_whatsapp` or any other app.
2. **Single writers:**
   - `engine/ingest.py` is the only code that creates or updates a `CL Call` from a device.
   - `engine/ai.py` is the only code that calls an external AI or speech API.
   - `engine/retention.py` is the only code that deletes recordings or transcripts.
   - `adapters/erpnext.py` is the only code that touches an ERPNext document.

   APIs and hooks are thin callers.
3. **Idempotent sync.** A device may resend the same batch any number of times. `call_key` is unique, and a resent batch reports duplicates instead of creating them.
4. **Privacy first.** Only company-SIM calls are synced; the filter runs on the phone, so personal-SIM calls are never uploaded.
   - Excluded numbers are dropped **on the phone**, before upload.
   - Recordings are private files, served only through a permission-checked streaming endpoint that writes a `CL Playback Log` row. There are never public URLs.
5. **An AI failure never blocks a call record.** The call saves; the transcript goes to `Failed` with a reason, and a retry job picks it up. AI spend stops at the monthly budget.
6. **Configuration over code.** Recorder paths, dispositions, stages, SLA and the AI provider are all data. There is no `if samsung:` branch in the server, and the app reads profiles from the server.
7. **Easy install.** `bench get-app` + `bench install-app grocall` on a plain Frappe site. Dual path: an idempotent `bootstrap_*.py` for a fresh install and exported doctype JSON for migrate, kept in sync. Seed dispositions, stages and recorder profiles ship as fixtures.
8. **Release gate.** `bench --site demo.grohrms.cloud execute grocall.selftest.run` must be green (dev/test sites only, because it writes rows), plus a browser walk-through, plus an Android check on at least one real phone of each supported brand.
9. **API keys.** The phone holds only its own device key (from pairing, kept in Android Keystore through `flutter_secure_storage`; revocable per device). AI and speech-to-text keys live in `CL Settings` as encrypted Password fields and are used only by `engine/ai.py`. A key compiled into an APK can be extracted by anyone who has the file, so no third-party key ever ships in the app.

## 6. Interfaces

**Device API** (token auth; the token is issued at pairing and stored hashed):
- `grocall.api.device.pair(code, device_info)`: returns a device token and the recorder profile.
- `grocall.api.device.sync(calls[])`: takes a batch of call-log rows and returns, per row, whether it was created, a duplicate or an error, plus which recordings to upload.
- `grocall.api.device.upload_recording(call_key, file)`: multipart, resumable for files over 5 MB. Checksum verified.
- `grocall.api.device.pull()`: returns open follow-ups, open missed-call alerts and a lead name lookup for caller ID (the rep's own leads only), plus settings.
- `grocall.api.device.disposition(call_key, disposition, notes, follow_up)`: sent from the after-call screen.

**Web app `/calls`** (Vue 3 + frappe-ui, the same stack as `/bill` and `/build`):
- Rep views: Today, My calls, Lead card (timeline of calls, notes and follow-ups), Follow-ups, Missed calls.
- Manager views: Team dashboard, Reports, Recordings with search.
- Admin views: Devices + pairing QR, Settings.

**Android app** (**Flutter** (Dart), minSdk 26 / Android 8, targetSdk 35). Plugins: `workmanager`, `flutter_secure_storage`, `dio` (upload), `sqflite` (offline queue), `mobile_scanner` (QR), `permission_handler`. A small **Kotlin platform channel** handles what no plugin does reliably: the call log with the SIM's `PHONE_ACCOUNT_ID`, the subscription list, the call-state listener, and the MediaStore/recordings folder scan. The Tier B fallback recorder (accessibility service) is native Kotlin.
- Pair by scanning a QR code, **then pick the company SIM**.
- A permission checklist with an OEM-specific "turn on auto call recording" guide.
- Call-end listener, then sync, then find the recording, then upload.
- An after-call card (disposition, note, follow-up) shown over the dialer as a notification.
- An offline queue (Room DB).
- Local missed-call reminders.
- Caller-ID name for known leads.
- A diagnostics screen (last sync, permissions, recorder folder found).

**Extension hooks** (for adapter apps): `grocall_call_created`, `grocall_call_dispositioned`, `grocall_missed_call_alert`, `grocall_lead_resolver`. For example, `gro_whatsapp` can send a "sorry we missed your call" message through its own adapter.

## 7. Compliance and data protection (DPDP Act 2023 aware)

- **Consent notice:** per-site text shown at pairing; the rep must accept before the phone pairs. There is also a recommended spoken line for customers ("this call may be recorded for quality").
- **Retention:** recordings default to 180 days, transcripts to 365 days, call metadata to 3 years. A nightly purge marks rows `Purged` and keeps the metadata.
- **Right to erasure:** an admin action deletes every recording and transcript for a phone number.
- **Audit:** `CL Playback Log` and the Frappe version log on `CL Call`.
- **AI providers:** audio leaves the server only when auto-transcribe is on. The provider and its data location are shown in Settings.
- **Personal calls:** company-SIM-only filtering on the phone, plus the excluded-number list (§5.4).

## 8. Reports (manager)

| Report | Answers |
|---|---|
| Rep activity | Calls (in / out / missed), connected calls, talk time, average duration, by rep and by day |
| Missed-call response | Missed calls, returned within SLA, average return time, never returned |
| Follow-up discipline | Due, done on time, overdue, by rep |
| Lead coverage | Leads not called in N days, leads called but with no disposition |
| Disposition funnel | Outcome mix and stage moves per rep and per source |
| Hour-of-day heatmap | When calls connect best |
| Device health | Last sync, missing permissions, recordings not found, by device |
| AI insights | Sentiment trend, top keywords and objections, AI spend this month |

The dashboard home shows today's KPIs, a leaderboard, overdue follow-ups, open missed calls and device warnings.

## 9. AI transcription and summary

- **Pluggable providers** (`CL Settings.stt_provider`):
  - Sarvam AI (best for Tamil, Hindi and Indian English)
  - OpenAI (Whisper / gpt-4o-transcribe)
  - Deepgram

  There is **no local model on this server**: it is shared with production, has 7 GB RAM and is 88% full.
- **Summary, action items, sentiment and objections:** Claude (`claude-sonnet-5-5`), using the official `anthropic` SDK, as HSHR does. The summary can be written into `CL Call.summary` and can propose a follow-up for the rep to confirm. It is never auto-created.
- **Queue:** the RQ `long` queue, one call per job. It honours the budget cap and runs only for calls longer than N seconds (default 20).
- Cost is stored per transcript and summed in the AI report.

## 10. Phased plan

### Phase 0: Foundation
App scaffold, roles, `CL Settings`, `CL Team`, the `/calls` shell (login, navigation, empty pages), Desk workspace, docs (SPEC, INSTALL, ADMIN, USER, CHANGELOG), selftest harness, git repo, and a fresh-site install test.

✓ `bench install-app grocall` works on demo **and** on a throwaway fresh site · ✓ the 3 roles exist · ✓ `/calls` loads for each role · ✓ selftest green · ✓ docs-index row present.

### Phase 1: Data model and sync API
`CL Lead` / `CL Stage` / `CL Call` / `CL Disposition` / `CL Device` / `CL Pairing Code` / `CL Excluded Number` / `CL Sync Log` / `CL Recorder Profile`, with seeds. Also `engine/phone.py`, `engine/ingest.py`, the device API (pair, sync, pull, disposition) and row-level permissions.

✓ The same batch sent twice gives 0 new calls · ✓ +91 / 0-prefixed / 10-digit forms all match the same lead · ✓ a rep cannot read another rep's call (API and Desk) · ✓ an expired or reused pairing code is refused · ✓ a revoked device token is refused.

### Phase 2: Recordings
Resumable upload, checksum, private storage, the streaming playback endpoint (HTTP range, permission check, `CL Playback Log`), `engine/retention.py` with a nightly purge, and a storage usage figure in Settings.

✓ A 30 MB file uploads in chunks after a dropped connection · ✓ playback seeks in the browser · ✓ a rep cannot stream another rep's recording · ✓ the purge removes the file and keeps the call row · ✓ every play is logged.

### Phase 3: Android app v1
Flutter app: pairing + company-SIM selection, tier detection, the permission checklist and OEM guide, call-log sync, recording discovery from server profiles, upload through WorkManager, the after-call card, the offline queue, caller ID, diagnostics, the company-SIM filter and the exclusion list, and a signed release APK with the key backed up. The build machine is decided in §11-Q4.

✓ A dual-SIM phone: personal-SIM calls never reach the server (server log), company-SIM calls do · ✓ the Tier B fallback recorder is tried on one Google-dialer phone and its result recorded honestly · ✓ On a real Samsung **and** a real Xiaomi/Realme/Vivo: 10 test calls (in, out, missed) appear in `/calls` within 1 minute online, with recordings · ✓ airplane-mode calls sync once back online · ✓ an excluded number never reaches the server (server log) · ✓ the APK installs over the previous version (same signature).

### Phase 4: Rep workflow (web)
The `/calls` rep screens: Today, My calls, Lead card with timeline and player, disposition and notes, create a lead from an unknown number, and stage moves from dispositions.

✓ A rep can complete every after-call step from the phone **or** the web · ✓ the lead timeline shows calls, notes and follow-ups in order · ✓ phone layout (390 px) works.

### Phase 5: Follow-ups and missed-call alerts
`CL Follow Up` and `CL Missed Call Alert`, an SLA engine on the scheduler, auto-close when the rep calls back, escalation to the manager after the SLA, Desk and Android notifications, a daily digest email, and the `grocall_missed_call_alert` hook.

✓ A missed call auto-closes when any call to that number connects within the SLA · ✓ an unreturned call escalates to the manager at SLA + grace · ✓ outside business hours the SLA clock pauses · ✓ an overdue follow-up shows on the rep's phone.

### Phase 6: Manager dashboard and reports
The §8 reports (Frappe script reports + `/calls` dashboard), team filters, and Excel/PDF export.

✓ Every report's totals reconcile with a direct count of `CL Call` rows on seeded data · ✓ a manager sees only their team · ✓ an admin sees all.

### Phase 7: AI transcription and summary
`engine/ai.py` with the provider adapters, `CL Transcript`, the job queue, the budget cap, transcript display with speaker turns and a click-to-seek player, summary and action items, proposed follow-ups, and the AI insights report.

✓ Tamil, English and mixed test recordings transcribe · ✓ a provider outage leaves the call intact and the transcript `Failed`, then retried · ✓ at the budget cap no new jobs start · ✓ a proposed follow-up needs rep confirmation.

### Phase 8: ERPNext adapter (optional)
When ERPNext is installed:
- resolve numbers against Lead / Contact / Customer;
- link `CL Call` to them, through `cl_` Custom Fields on Lead and Opportunity (fixture + bootstrap);
- show a "Calls" timeline section on Lead / Customer / Opportunity through additive `doctype_js`;
- optionally create a Lead from an unknown number;
- create a `ToDo` for a follow-up.

✓ Install and uninstall on a site **without** ERPNext still work · ✓ with ERPNext, a call to a Customer's contact number links to the Customer · ✓ no ERPNext controller is patched.

### Phase 9: Hardening and release
DPDP checklist review, load test (10k calls/day, 50 devices), a security review of the device API, a fresh-site install, UAT guide, versioned release notes, a first customer-bench rollout plan (approval required), and an APK update channel (`/calls/download` + an in-app "update available" prompt).

✓ Selftest, browser walk-through and Android check all green · ✓ fresh install on a clean site · ✓ USER, ADMIN and INSTALL docs complete.

## 11. Open questions (block the phase in brackets)

Answered 2026-10-08:
- **Company phones or personal phones:** a separate company SIM, and only that SIM is tracked.
- **Phone brands:** all Android phones, using the tiers in §2.2.
- **App technology:** Flutter, with a per-device API key.

Still open:

1. **Sales base [Phase 1].** Standalone `CL Lead` + optional ERPNext adapter is assumed. Is that right, or should calls attach only to ERPNext records?
2. **AI provider and budget [Phase 7].** Sarvam / OpenAI / Deepgram for speech, Claude for summaries. Which keys exist, and what monthly cap?
3. **Retention periods [Phase 2].** Defaults are 180 days for recordings, 365 for transcripts, 3 years for metadata.
4. **APK build machine [Phase 3].** This server is 88% full and has no Java. Flutter + Android SDK + Gradle need about 8 GB. Recommended: GitHub Actions or the developer's PC, not this shared production box.
5. **First customer [Phase 9].** Which business pilots it, and on which bench?
6. **Cloud telephony later?** If yes, Phase 1's `source` field and the ingest engine already allow it; a provider adapter becomes a Phase 10.

## 12. How we run it as a product

- **Versioning:** semantic versions. The server app and the APK are versioned separately, and the API carries a version number. The server supports the current APK and the previous one, and refuses older apps with an "update" message.
- **Changes:** every change goes in `apps/grocall/docs/CHANGELOG.md`, and each release gets a git tag.
- **Environments:** demo-bench (develop and test), then a customer bench (pilot, with approval), then a general release. Never production first.
- **Support:** each phone's diagnostics screen can send a report (device, permissions, last errors) to the admin, so most "calls not showing" tickets get answered without visiting the phone.
