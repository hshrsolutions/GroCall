# GroCall — Android app (Flutter)

The salesperson's phone app. It syncs **company-SIM** calls, uploads the phone's own call recording,
asks for the outcome after each call, reminds about missed calls and follow-ups, and shows a
diagnostics screen. Server contract: `../docs/DEVICE-API.md`.

| Part | Where |
|---|---|
| Screens (setup, Today, Calls, outcome, Leads, Follow-ups, Phone) | `lib/` (Dart) |
| Call log + company-SIM filter, recordings, upload, background sync, notifications, encrypted key | `android/app/src/main/kotlin/com/hshrsolutions/grocall/` (Kotlin) |
| Build + sign | `../.github/workflows/android.yml` (GitHub Actions) |

Why Kotlin for the phone work: it has to run when the app is closed (after every call and every
15 minutes through WorkManager), which is reliable only in native code. Flutter is the UI.

## Build

Builds run on GitHub Actions, never on the production server. Push to `mobile/` or run the workflow
by hand, then download the `grocall-apk` artifact. To release, push a tag like `mobile-v0.1.0`.
The workflow attaches the APK to a GitHub Release.

Local (a developer PC with Flutter 3.47.6 + Android SDK + JDK 21):

```bash
cd mobile && flutter pub get && flutter analyze && flutter test && flutter build apk --release
```

## Signing

The release key is **`grocall-release.p12`** (alias `grocall`, PKCS#12). It was created on 2026-10-08.

| Copy | Where |
|---|---|
| Server, root only | `/root/grocall-signing/` |
| Server, root only | `/home/frappe/site-archives/grocall-signing/` |
| GitHub secrets | `GROCALL_KEYSTORE_B64`, `GROCALL_KEYSTORE_PASSWORD` |
| Off-server | The owner keeps one |

**Never lose it.** An APK signed with any other key won't install over the existing app.

## Versions

`version:` in `pubspec.yaml` is the app version (semantic). The build number is the CI run number.
The server refuses apps older than `MIN_APP_VERSION` in `grocall/api/device.py`.
