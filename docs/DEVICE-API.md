# GroCall device API (for the phone app)

Server version 0.3.0. Base URL: `https://<site>/api/method/grocall.api.device.<method>`.
All calls are **POST** with a JSON body, and every reply is `{"message": {"ok": true, ...}}`.
Errors use HTTP status codes and Frappe's `_server_messages`:

| Code | Meaning |
|---|---|
| 401 | Missing, wrong or revoked device key, or the user is disabled |
| 403 | Bad or used pairing code, or GET instead of POST |
| 404 | Call not synced yet |
| 417 | Validation error (message text) |
| 429 | Too many pairing attempts |

## Auth

`pair` is the only call without a key. Every other call sends two headers:

```
X-GroCall-Device: CLD-00001
X-GroCall-Key:    <key from pair>
```

The app keeps the key in Android Keystore (`flutter_secure_storage`). The server stores only its SHA-256 hash.
Re-pairing the same `device_uuid` rotates the key and keeps the same `CL Device`.
The app must never hold any other key (AI, SMS, …).

## consent (no key)

Request: `{}`. Reply: `{"settings": {...}, "server_version", "min_app_version"}`. The phone shows `settings.consent_text`
before pairing. Rate limit: 30 per 10 minutes per IP.

## pair

Rate limit: 10 attempts per 10 minutes per IP. The code is 8 characters (`A–Z` without `O`/`I`, digits `2–9`).
Case, spaces and dashes are ignored. A code is valid for 10 minutes and works once. The QR code holds:

```json
{"v": 1, "app": "grocall", "site": "https://demo.grohrms.cloud", "code": "K4T5HXSW"}
```

Request:

```json
{"code": "K4T5HXSW", "consent_accepted": true,
 "device_info": {"device_uuid": "…", "brand": "samsung", "model": "SM-A546E", "os_version": "14",
   "app_version": "0.1.0", "support_tier": "A",
   "sim": {"subscription_id": "2", "carrier": "Jio", "last4": "4321", "fingerprint": "…"}}}
```

`sim.subscription_id` (Android `SubscriptionInfo.getSubscriptionId()`, which matches `CallLog.Calls.PHONE_ACCOUNT_ID` on most phones) is **required**.
The reply has `device`, `key`, `user`, `full_name`, plus the common block below.

## sync

Request: `{"app_version": "0.1.0", "calls": [ … up to 500 … ]}`. Each call looks like this:

```json
{"ref": "local-row-id", "direction": "incoming|outgoing|missed|rejected|blocked",
 "number": "09876543210", "started_at": 1780000000000, "duration_sec": 42, "sim_subscription_id": "2"}
```

- `started_at` is epoch **milliseconds** (`CallLog.Calls.DATE`).
- The phone sends company-SIM rows only. The server re-checks this and answers `excluded` for any other SIM.
- The server ignores the duration of missed, rejected and blocked calls (stored as 0).
- **Idempotent:** the key is (salesperson, `started_at`, number), so resending a batch is always safe.

Reply: `{"counts": {"created", "duplicate", "excluded", "error"}, "results": [{"ref", "status", "call", "call_key", "lead", "lead_name", "upload", "message"}]}`.
The phone marks a row as sent when its status is `created`, `duplicate` or `excluded`, and retries an `error` on the next sync.

## pull

Request: `{}`. The reply contains:

| Field | Contents |
|---|---|
| `leads` | The salesperson's own leads, at most 3000: `name`, `lead_name`, `company_name`, `stage`, `phones` (E.164). Used for caller-ID names |
| `excluded_numbers` | E.164 numbers the phone must never send |
| `dispositions` | The outcome choices for the after-call card |
| `follow_ups`, `missed_alerts` | Empty until Phase 5 |
| common block | See below |

## disposition

Request: `{"call": "CALL-2610-00005"}` or `{"call_key": "…"}`, plus `"disposition": "Call back later"`, `"notes": "…"` and optionally `"next_follow_up": "2026-10-09 10:00:00"`.
If the outcome needs a follow-up and none is given, the server sets one at 10:00 after the outcome's default number of days. The lead's stage moves as the outcome says.

## heartbeat

Request: `{"permissions": {"call_log": true, "audio": true, …}, "app_version": "…", "support_tier": "A|B", "fallback_recorder": 0|1}`.
It keeps the admin's Phones screen current.

## Common block (pair, pull, heartbeat)

| Field | Contents |
|---|---|
| `settings` | `sync_scope`, `allow_fallback_recorder`, `consent_text`, `customer_announcement`, `default_country_code` and `brand` |
| `recorder_profiles` | `[{name, priority, brands[], folders[], filename_regex}]`. The phone tries the profile whose `brands` contains `Build.MANUFACTURER` (lower case), then the generic one (empty `brands`) |
| `server_time`, `server_version`, `min_app_version` | Version and clock information |

## Recordings

**Which recordings to send:**
- A `sync` result row has `"upload": true` for connected calls.
- `pull` also lists `pending_recordings`: the salesperson's calls from the last 7 days still at `Pending`, so a reinstalled app catches up.

**Finding the file:**
1. Search the recorder profile's folders.
2. Fall back to MediaStore audio created within about 2 minutes of the call's end.
3. Match on the time first, and on the number in the file name when the profile's `filename_regex` finds one.

### upload_recording (multipart/form-data)

| Field | Meaning |
|---|---|
| `call_key` | From the sync result's `call`, via `upload_status`, or computed the same way as the server |
| `offset` | Byte position this chunk starts at |
| `total_size` | Size of the whole file (at most 150 MB) |
| `sha256` | Hex SHA-256 of the **whole** file |
| `ext` | `m4a`, `mp4`, `aac`, `mp3`, `amr`, `awb`, `3gp`, `wav`, `ogg`, `opus`, `flac` or `webm` |
| `duration_sec` | Optional |
| `chunk` | The bytes, at most 8 MB. 1–4 MB is recommended on mobile data |

The reply's `status` is one of:

| Status | Meaning |
|---|---|
| `partial` | Keep going from `received` |
| `resume` | The server is at `received` and nothing was written. Continue from there; this is what you get after a dropped connection |
| `complete` | Done. Sending again is harmless |

Errors:
- Checksum mismatch (417): the partial file is discarded, so start again from 0.
- Unsupported type, or more bytes than `total_size`: refused.
- Another salesperson's call: 404.

### upload_status

Request: `{"call_key"}`. Reply: `{"received", "recording_status"}`. Call it before resuming after an app restart.

### recording_missing

Request: `{"call_key", "reason": "not_found" | "not_available"}`. Use `not_available` on Tier B phones where recordings can't be read at all.
