# Business Class Flight Concierge

A monorepo for a Business Class travel concierge:

- **Search** Business Class fares (cabin `C`) and book **directly on the airline** through deep links.
- **Intercept the booking code** (PNR) inside the in-app airline WebView and offer to auto check-in.
- **Automatically check in exactly 24 hours before departure**, first through the Flyo AI Web Check-in API and, if that is unavailable, through a Playwright browser bot. The boarding pass is delivered to the app.

```
business-concierge/
├── backend/    FastAPI · SQLAlchemy (async) · APScheduler · Playwright · HTTPX
└── frontend/   Flutter · Riverpod · flutter_inappwebview
```

```mermaid
flowchart LR
  App[Flutter app] -->|search| Search["GET /api/flights/search"]
  Search --> Provider{Provider}
  Provider --> Tequila & Amadeus & Mock
  App -->|deep_link| WebView[Airline WebView]
  WebView -->|PNR detected| Register["POST /api/bookings/register-checkin"]
  Register --> DB[(DB)] & Scheduler[APScheduler]
  Scheduler -->|departure - 24h| Engine[CheckInEngine]
  Engine --> Flyo[Flyo API] -->|webhook| Webhook["POST /api/webhooks/checkin-complete"]
  Engine -->|fallback| Bot[Playwright bot] --> Static["/static/boarding_passes"]
```

---

## 1. Backend

Requires Python 3.11+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Tests: `pytest` (from `backend/`, with the venv active)

The server works without any API keys. Search returns realistic demo data, and every result links to a simulated airline checkout page at `/demo/checkout` that shows a confirmation code, so you can try the whole PNR-detection flow end to end.

### Configuration (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `FLIGHT_PROVIDER` | `auto` (default), `tequila`, `amadeus` or `mock` |
| `TEQUILA_API_KEY` | Kiwi.com Tequila metasearch key (returns native `deep_link`s) |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | Amadeus Self-Service credentials; deep links go to the carrier's booking page |
| `FLYO_API_KEY` / `FLYO_BASE_URL` | Flyo AI Web Check-in API. Leave the key blank to use only the Playwright bot |
| `FLYO_WEBHOOK_SECRET` | If set, webhooks must carry `X-Flyo-Signature: sha256=<HMAC-SHA256 of body>` |
| `PUBLIC_BASE_URL` | Public URL of this API, used for the Flyo `callback_url` and boarding-pass links |
| `DATABASE_URL` | `sqlite+aiosqlite:///./concierge.db` locally; `postgresql+asyncpg://user:pass@host/db` in production (`postgres://` URLs are normalised automatically) |
| `CHECKIN_LEAD_HOURS` | Defaults to `24` |
| `PLAYWRIGHT_HEADLESS` | `true` produces a PDF boarding pass; `false` shows the browser and saves a PNG |

In `auto` mode the backend uses Tequila if its key is set, then Amadeus, then mock data. If a real provider errors, the search falls back to mock data and logs a warning.

> Kiwi.com stopped onboarding new Tequila partners in 2024. If you can't get a key, use Amadeus Self-Service.

### API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/flights/search?origin=JFK&destination=LHR&date=2026-12-15` | Business Class offers with `deep_link` |
| `POST` | `/api/bookings/register-checkin` | Save a booking + PNR and schedule check-in at `departure_time - 24h` |
| `POST` | `/api/bookings/{id}/trigger-checkin-now` | Run check-in immediately (returns `202`) |
| `GET` | `/api/bookings` | All tracked bookings with status and boarding-pass links (`?email=` to filter) |
| `GET` / `DELETE` | `/api/bookings/{id}` | Fetch a booking, or stop tracking it |
| `POST` | `/api/webhooks/checkin-complete` | Flyo callback carrying the boarding-pass URL |

```bash
# Search
curl "http://localhost:8000/api/flights/search?origin=JFK&destination=DOH&date=2026-12-15"

# Register a booking for check-in (departure_time must include a UTC offset)
curl -X POST http://localhost:8000/api/bookings/register-checkin \
  -H 'Content-Type: application/json' \
  -d '{"user_email":"ada@example.com","passenger_first_name":"Ada","passenger_last_name":"Lovelace",
       "airline_iata":"DL","flight_number":"DL1","departure_time":"2026-12-15T22:10:00Z","pnr_code":"ABC123"}'

# Force check-in now, then inspect the result
curl -X POST http://localhost:8000/api/bookings/1/trigger-checkin-now
curl http://localhost:8000/api/bookings/1

# Simulate the Flyo webhook
curl -X POST "http://localhost:8000/api/webhooks/checkin-complete?booking_id=1" \
  -H 'Content-Type: application/json' \
  -d '{"status":"completed","boarding_pass_url":"https://example.com/bp.pdf"}'
```

### How check-in works

1. When a booking is registered, a one-off APScheduler job is set for `departure_time - CHECKIN_LEAD_HOURS`. If the window is already open, the job runs right away. The database is the source of truth: on startup, every booking still waiting for check-in is rescheduled, so restarts don't lose jobs.
2. **Primary strategy:** `POST {FLYO_BASE_URL}/v1/checkin` with `pnr_code`, `airline_iata`, `passenger_last_name` and a `callback_url`. A response that includes a boarding pass URL completes the booking immediately. A `pending` or `202` response leaves it `SCHEDULED` until the webhook arrives.
3. **Fallback strategy:** if Flyo is not configured, errors or times out, the airline's bot is used. Bots are listed in `app/services/bots/__init__.py`. The bot runs a stealth-configured headless Chromium through four steps: open, look up the trip, confirm seats and capture the boarding pass. It saves a PDF and PNG to `backend/static/boarding_passes/`, served at `/static/boarding_passes/...`.
4. A failure sets `FAILED` and records the reason in `last_error`, with a link to a screenshot when one exists. The app displays this error.

To add an airline, subclass `AirlineCheckInBot` (see `app/services/bots/delta.py`), implement `fill_lookup`, `confirm_seats` and `capture_boarding_pass`, and register it in `BOT_REGISTRY`.

> Airline websites change their markup often and use bot protection such as Akamai. In local testing, delta.com returned "Access Denied" to headless Chromium. The bot detects block pages and reports `Blocked by DL bot protection` rather than failing silently. Treat the bot as a best-effort fallback, keep its selectors (`SELECTORS` in `delta.py`) up to date, and check each airline's terms of use before automating it.

### Receiving Flyo webhooks locally

Flyo must be able to reach your machine:

```bash
ngrok http 8000
# then in backend/.env
PUBLIC_BASE_URL=https://<your-subdomain>.ngrok-free.app
```

Restart uvicorn after editing `.env`.

---

## 2. Frontend (Flutter)

Requires Flutter 3.27+ (Dart 3.6+). To run on a device you also need one of:

- **iOS Simulator:** the full Xcode app from the App Store, then `sudo xcodebuild -runFirstLaunch`, and CocoaPods (`brew install cocoapods`).
- **Android emulator:** Android Studio, with an emulator created in its Device Manager.

`flutter doctor` shows what is missing.

Android can also be set up entirely from the terminal without Android Studio and without admin rights. This is how the project was verified:

```bash
brew install --cask flutter android-commandlinetools
brew install openjdk@17
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses
$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platform-tools" "emulator" \
  "platforms;android-36" "build-tools;36.0.0" "system-images;android-36;google_apis;arm64-v8a"
flutter config --android-sdk $ANDROID_HOME --jdk-dir $JAVA_HOME
echo no | $ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd \
  -n concierge_pixel -k "system-images;android-36;google_apis;arm64-v8a" -d pixel_8
$ANDROID_HOME/emulator/emulator -avd concierge_pixel &
```

`flutter_inappwebview` is pinned to the 6.2.0 beta because 6.1.x fails to build with Android Gradle Plugin 9, which current Flutter templates use.

```bash
cd frontend
flutter pub get
```

The `android/` and `ios/` projects are already configured for the WebView:

- **Android** (`android/app/src/main/AndroidManifest.xml`): the `INTERNET` permission, `usesCleartextTraffic` so the app can reach the local HTTP backend, and `<queries>` so `url_launcher` can open https links, PDFs, mail and phone links.
- **iOS** (`ios/Runner/Info.plist`): `NSAllowsLocalNetworking` and `NSAllowsArbitraryLoadsInWebContent` under `NSAppTransportSecurity`, and `LSApplicationQueriesSchemes`. The deployment target is iOS 15.

For production builds, remove `usesCleartextTraffic` and `NSAllowsLocalNetworking` and serve the API over HTTPS.

### Run

```bash
# Android emulator (talks to the host via 10.0.2.2 by default)
flutter run

# iOS simulator (localhost by default)
flutter run -d ios

# Physical device or remote backend
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000

# Unit tests
flutter test
```

Backend links that point at `localhost`, such as demo checkout pages and locally stored boarding passes, are rewritten to `API_BASE_URL` on the device. For a physical device, run uvicorn with `--host 0.0.0.0`.

### App tour

- **Search:** IATA autocomplete for origin and destination, a date picker, and Business Class flight cards showing carrier, times, layovers and price. Each card has a **Book Direct on Airline** button.
- **Airline booking WebView:** opens the `deep_link`. On every `onLoadStop`, JavaScript is injected that scans the page text for `PNR / Confirmation / Record Locator / Booking Reference` followed by a 6-character code. A `MutationObserver` rescans pages that render the confirmation later. When a code is found, a native bottom sheet asks *"We detected your booking code [XXXXXX]. Auto-check you in 24h before departure?"*, with flight details prefilled. You can also tap the ticket icon to enter a code by hand.
- **My Trips:** shows a live countdown to the check-in window, status chips, **Check in now**, a form for adding a PNR booked elsewhere, and **View Boarding Pass**. Boarding passes render in-app on iOS; on Android, PDFs open in the system viewer.

### Try the full flow offline

1. Start the backend (no keys needed) and run the app.
2. Search **JFK → LHR** and tap **Book Direct on Airline** on any card.
3. Fill in the demo checkout and tap **Confirm & Pay**. A confirmation code appears, and the app's bottom sheet detects it.
4. Confirm. The trip shows up in **My Trips** with a countdown to check-in.
