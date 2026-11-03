# Elsewhere: implementation and operating guide

The new application is in `web/`; FastAPI serves `/api/v1`. Flutter and the old HTML app are retained as prototypes. The old `/api/bookings/place` always returns 410. Legacy routes exist only in the explicit test configuration; public boarding-pass paths are disabled.

## Run locally

```sh
cd backend
.venv/bin/pip install -r requirements.lock
ENVIRONMENT=development DATABASE_URL=sqlite+aiosqlite:////tmp/elsewhere-preview.db .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --reload-dir app
```

In a second terminal:

```sh
cd web
npm ci
npm run dev
```

Open http://127.0.0.1:5173 and choose **Explore the private preview**. Demo accounts, fares, trips, and purchases are fictional and isolated per session. No email connection, external airline purchase, or card collection is allowed in demo mode. The preview database is separate from the existing app database.

For the private pilot, sign in with **Continue with Google**. Configure Supabase’s Google provider separately for staging and production. Set `AUTH_GOOGLE_ENABLED=true`, `AUTH_EMAIL_OTP_ENABLED=false`, `ALLOWED_EMAILS`, and a unique `TOKEN_ENCRYPTION_KEY` for each environment. Email-code sign-in is disabled. The frontend stores only an opaque HTTP-only application session; the backend exchanges PKCE codes and verifies the Google identity and allowlist. Login does not authorize Gmail.

Set up a Google Auth Platform application named **Federico’s Travel Desk**, with external testing access limited to the two invited Google accounts. Create two web OAuth clients, one for each Supabase project, and register each project’s exact `https://<project-ref>.supabase.co/auth/v1/callback` in Google. In each Supabase Auth redirect allowlist, add only that environment’s exact frontend callback: `https://<frontend-host>/api/v1/auth/google/callback`. Enable only the Google provider for this pilot. Request only `openid email profile`; do not request offline Google access or Gmail scopes. Provider verification/branding requirements may affect activation.

Create Google OAuth client secrets and database passwords through secure provider setup. Never paste them into chat, commit them, or put them in `VITE_` variables. The two invite addresses must be verified Google identities; a non-Gmail address can be associated with a Google account.

## Environment and deployment

1. Approve the costs in `docs/COSTS.md` before provisioning. No hosted resources have been created by this implementation.
2. Create separate staging and production Supabase projects in the EU. Use a direct/session-pool PostgreSQL connection for the durable worker; transaction pooling is unsuitable for worker session/advisory locks. Keep database credentials in the deployment secret store.
3. Set `ENVIRONMENT=staging` or `production`, `DEMO_ENABLED=false`, `LEGACY_API_ENABLED=false`, `AUTO_CHECKIN_ENABLED=false`, `LIVE_CHECKOUT_ENABLED=false`, `ALLOWED_EMAILS`, `APP_URL`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY`. Use an HTTPS public app URL.
4. Run `python scripts/initialize_release.py` using the dedicated application database role. It serializes migrations, table restrictions, private document storage, queue initialization and preflight under a PostgreSQL advisory lock. Browser roles cannot access application tables. The storage bucket is created through the backend service identity. The additive initial migration supports existing legacy tables and refuses destructive downgrade.
5. Deploy the staging and production API/worker pairs with `render.yaml`. Use a separate Supabase organization for this app so the existing unrelated project remains unchanged. Both need the same database, Duffel and integration secrets. `python scripts/init_queue.py` initializes the pinned Procrastinate schema once in a private `jobs` schema; repeat deployments skip initialization. Apply the package's documented schema migrations before upgrading Procrastinate.
6. Prepare isolated frontend source using `python backend/scripts/prepare_web_release.py --api-origin https://<api-host> --destination /tmp/<new-release-directory> --project-id <travel-project-id> --org-id <vercel-team-id>`. Deploy from that directory, using Vite, `npm ci`, `npm run build`, and `dist`. The helper excludes secrets and replaces the API rewrites. Do not deploy from the workspace root, which is linked to a different Vercel project. For this frontend-only source deployment, the Vercel project Root Directory must be `.`. `/api` must remain same-origin with the browser app for cookies and CSRF. The API itself should also be private behind platform network controls where available.
7. Configure `APP_URL` to the exact Vercel origin. Preview deployments require their own staging configuration; do not share production cookies, credentials, or databases.
8. After the owner signs in, run `python scripts/migrate_legacy.py --email <allowlisted-owner> --source-sqlite /secure/legacy-backup.db`. This preserves legacy records and creates review drafts for incomplete itineraries. The source backup is opened read-only. Repeated runs do not duplicate drafts or overwrite subsequently edited preferences. It never invents arrival times or missing return segments.

Backend startup refuses production with SQLite, demo access, legacy routes, automatic check-in, missing authentication, or a non-HTTPS app origin. The worker must be deployed separately; no production jobs depend on an API process staying alive.

## Release checks and cutover

The Render pre-deploy commands apply migrations, initialize the durable queue and run `scripts/release_preflight.py`. The initializer applies private table restrictions through the table-owning application role and configures private storage before preflight. Preflight checks PostgreSQL migration `0002_google_login`, private table restrictions, the worker schema, the public Google-provider setting, test-only Duffel credentials and disabled purchase/email flags. It deliberately prevents an unconfigured pilot from becoming healthy.

Keep production’s existing alias unchanged while validating the separate staging release. Verify both Google identities interactively, cookies/CSRF, isolation, search, filters saved through Preferences, comparisons, imports, trips and local-time calendar. Verify queue recovery after worker restart and restore a database backup into staging. Deploy the same reviewed release to production only after these gates pass; record deployment identifiers and database backups. For the first secure release, use a maintenance response rather than restoring an older unauthenticated booking API if rollback is necessary.

The current checkout is still gated. Resend, forwarding and reminders remain disabled because no verified email domain is available. No deployment readiness claim includes Gmail or payment-provider approval.

## Provider activation

### Duffel and traveler cards

Flight search works with the existing Duffel test token. Real provider inventory remains labeled test data when `live_mode=false`. Provider responses supply segment cabins and airport timezones. Missing timezones are rejected rather than guessed. The search reads all retrieved offers before applying requirements, groups itineraries, preserves fare alternatives, and returns provider-coverage information.

`DUFFEL_CARDS_APPROVED` is off by default. Set it only after Duffel approves the card integration and confirms eligible airline/payment coverage. `DUFFEL_CARD_AIRLINES` must list only airline codes confirmed in that approval. Duffel search responses do not expose a generic supported-card-method flag; final eligibility and charges are checked by card-specific pricing. `LIVE_CHECKOUT_ENABLED` is a separate switch, also off by default. In-app checkout additionally rejects offers requiring passport documents because the pilot does not yet collect them; airline booking remains available.

The client loads Duffel's hosted card form only on the payment step. It tokenizes the card, requests card-specific pricing, obtains acceptance of the resulting total, completes 3DS, and submits an order. API requests carry only Duffel card/session identifiers. No balance payment fallback exists in v1. Optional paid extras are deferred; the checkout explicitly states none are selected.

Quote hashes bind the accepted amount, currency, itinerary and fare rules. Each order attempt is persisted before provider submission. A network/5xx outcome stays **confirming** and is reconciled using provider order metadata; it is never resubmitted automatically. Definitive declined attempts are terminal. The worker polls unresolved orders and ticket issuance, then refreshes confirmed orders every 15 minutes until two days after travel to pick up airline schedule changes and cancellations. It must never infer “no booking” solely because an initial listing did not return an order.

Before live activation, run provider sandbox cases for card authentication, rejection, price changes, ticket documents, post-booking schedule changes and servicing. Then conduct an explicitly authorized low-value live purchase and cancellation with a named operator monitoring it. The code and local demo are not evidence that an account is approved for live sales.

Airline handoff compares every segment, dates, times and cabin against provider booking options. If that cannot be verified, the app labels an official airline link **Search on airline**, requiring reselection. Independent airline fares can differ from Duffel fares.

### Gmail and forwarding

Set a Google OAuth client, exact backend callback URI and `TOKEN_ENCRYPTION_KEY` (a Fernet key). OAuth state is account-bound, hashed, single-use and expires after ten minutes. Tokens remain encrypted server-side. The Gmail scope is `gmail.readonly`; it grants mailbox read access, while the application queries booking-related messages. Production OAuth consent/verification must be completed as required by Google; temporary test grants are not a production connection strategy.

The worker polls every two minutes, deduplicates source messages, imports complete structured flight reservations, and sends incomplete or ambiguous messages to review. Plain confirmations require confirmation of all segments. The current parser supports explicit flight/date/route fields and FlightReservation JSON-LD; unfamiliar airline formats need manual review. Email attachments are not parsed in this release.

For forwarding, configure Resend receiving, `FORWARDING_DOMAIN`, `RESEND_API_KEY`, and `RESEND_WEBHOOK_SECRET`; point `email.received` events to `/api/v1/webhooks/inbound`. Configure the exact domain's MX records. Per-account randomized inbox addresses are displayed only to their owner. Unsigned callbacks fail closed. Test signed retries and content retrieval before activation.

Set `NOTIFICATION_FROM` to a verified sender for reminders. Notifications are opt-in through the profile and contain a private itinerary link, not booking references or documents. Provider idempotency keys prevent repeat reminder sends.

### Destination information

`GOOGLE_PLACES_API_KEY` enables identity, address, website and review-score lookup. Hotel review ratings are not star classifications. A dated official-source hotel catalogue covers Madrid, London, Doha and Singapore. Five-star classification is identified as either hotel-published or a named Forbes hotel rating, separately from user reviews. Entries expire from recommendations after 30 days until rechecked. Unknown amenities cannot satisfy a requested gym/spa preference; unsupported cities show no verified hotel matches. Demo suggestions are explicitly labeled. Respect Google Places attribution and retention requirements.

## Operational checks

- CI runs backend regression tests, contract generation, frontend tests, TypeScript checking, production build and dependency audit. Regenerate types using `python backend/scripts/export_openapi.py` followed by `npm run types` in `web/`.
- Enable Sentry only after configuring its project. Backend request bodies, cookies, query strings, authentication headers and user identifiers are removed from error events. Do not enable provider debug/HTTP request logging; URLs can contain API keys and OAuth codes.
- Default per-account quotas: 100 new searches/day, 100 airline lookups/day, 30 place-discovery requests/day, 100 imports/day, 30 manual mailbox syncs/day. Search reuse within 90 seconds avoids duplicate provider calls. A dual-cabin search can issue two provider searches; account for this in Duffel usage reporting.
- Search records expire after seven days, import drafts after 30 days, expired sessions are purged. Unresolved booking attempts and webhook/notification receipts are retained for recovery and deduplication.
- Use `/health` for API availability. Monitor pending searches over three minutes, booking attempts stuck confirming, queue age, mailbox reconnect states, provider errors and quota rejections. Run `python -m procrastinate --app=app.v1.jobs.queue healthchecks --help` for worker heartbeat checks.
- Approve platform-level spending caps and alerts in each provider dashboard. Application quotas bound requests, not invoices or external retries. No automatic plan upgrades are configured.
- The pilot's service-request endpoint records a request and explicitly does not claim that a cancellation or change occurred. App operators must monitor `service_requests` and use Duffel/airline support. Automated change/refund quoting, autonomous check-in and WhatsApp are not enabled.

## Backups and rollback

Use Supabase Pro daily backups and rehearse restoration into staging before launch. Back up private document objects separately; database backups do not restore file bytes. Keep encrypted token keys in the secret manager, backed up separately from the database.

For recovery: disable live checkout, restore a backup into a separate staging project, validate row counts/ownership and object availability, reconcile all pending attempts with Duffel, then switch traffic only after validation. Do not issue new orders to replace unknown outcomes.

Roll back frontend/API/worker versions together while retaining the additive schema and provider metadata. Use the independent checkout flags as the first response to purchase incidents. No destructive schema rollback is provided.

## Verification boundary

Local tests and UI review exercise demo search, preferences, booking outcomes, trip details, calendar and imports. A Duffel sandbox round-trip search retrieved 2,063 offers and produced 821 distinct matching itineraries without the old cutoff. Account-specific card eligibility, production Gmail consent, actual email delivery, PostgreSQL worker restart recovery, hosted backups and a real purchase still require configured service accounts and staging verification. Do not advertise those external checks as completed.
