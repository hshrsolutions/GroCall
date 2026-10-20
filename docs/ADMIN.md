# GroCall — admin guide

Status: Phase 0 (foundation). Sections marked *(Phase N)* describe screens that are not built yet.

## 1. Give people access

| Person | Role to give (User → Roles) |
|---|---|
| Salesperson | **CL Sales Rep** (a Website User is enough, as they don't need Desk) |
| Team lead | **CL Sales Manager** |
| Owner / admin | **CL Admin** |

A signed-in user without any of these sees "No access to GroCall" at `/calls`.

## 2. Make teams

Desk → GroCall → **CL Team** → New. Pick the manager (must hold CL Sales Manager), then add the members
(each must hold a GroCall role, and nobody can be listed twice). A manager sees the calls of their team members.

## 3. Settings

Desk → GroCall → **CL Settings** (or `/calls` → Settings):

| Setting | Default | Meaning |
|---|---|---|
| Sync scope | Company SIM only | Only calls on the company SIM ever leave the phone |
| Allow fallback recorder | Off | Tier B (Google-dialer) phones: best-effort in-app recorder |
| Consent notice | provided | Shown to the salesperson before their phone pairs |
| Return a missed call within | 30 min | After that it is overdue; after the grace period it goes to the manager |
| Business hours / days | 09:30–19:00, Mon–Sat | The missed-call clock pauses outside these |
| Keep recordings / transcripts / call records | 180 / 365 / 1095 days | A nightly job deletes older files |
| AI keys | empty | Stored encrypted on the server and never sent to the phone app |
| Monthly AI budget | 0 (AI off) | New transcriptions stop when this month's spend reaches it |

## 4. Phones *(server side live; phone app in Phase 3)*

`/calls` → **Phones** → *Pair a phone*. Managers and admins can choose a team member; reps pair their own phone.
The code works once and expires after 10 minutes. The salesperson installs the GroCall APK, scans the code,
accepts the consent notice, and picks the **company SIM**. You can revoke a phone at any time.

**Phone support tiers:**
- **Tier A (full):** brands with their own dialer, such as Samsung, Xiaomi/Redmi/POCO, Oppo/Realme/OnePlus, Vivo/iQOO, Tecno/Infinix and Lava.
- **Tier B (tracking only, best-effort recording):** phones on the Google Phone dialer, such as Pixel, Motorola and Nokia.

When buying company phones, pick a Tier A brand.

## 5. Outcomes, stages and recorder folders

- **CL Disposition** sets the choices a rep picks after a call. Each one can need a follow-up (with a default number of days) and can move the lead to a stage.
- **CL Stage** is the lead pipeline (New → Contacted → Interested → Negotiation → Won / Lost).
- **CL Recorder Profile** lists where each phone brand saves its call recordings. If a phone's diagnostics screen reports a different folder, add it here. There is no app update needed.

## 6. Personal numbers

**CL Excluded Number**: a number listed here is never sent by the phone and is refused by the server.
Leave *Only for this salesperson* empty to exclude it for everyone. Reps can add their own entries.

## 7. Recordings, retention and privacy

- **Where:** `<site>/private/files/grocall/`. They are included in `bench backup --with-files`. No link points at them; they can only be played from a call (Desk form, or the web app from Phase 4), and only by someone who may see that call.
- **Who listened:** Desk → **CL Playback Log** (admins only). It has one row per listen. Seeking within a listen isn't logged again.
- **Retention:** the nightly job deletes recordings after *Keep Recordings (Days)*. The call stays, marked **Purged**. Call entries themselves go after *Keep Call Records (Days)*. The current disk use is shown in `/calls` → Settings.
- **A customer asks to be forgotten:** `/calls` → Settings → *Erase one person's recordings*. A note of who did it is kept on CL Settings.
- **Call details can't be edited:** the number, time, duration, direction and salesperson come from the phone and are locked for everyone, so reports can be trusted. Outcome, notes, follow-up and lead can still be changed.
