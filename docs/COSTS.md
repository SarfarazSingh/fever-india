# Service costs for approval

Reviewed 3 November 2026. No new paid resources, subscriptions or live tickets have been purchased. Prices are USD before tax unless the provider states otherwise; the provider's checkout/contract governs.

| Service | Proposed use | Published amount / approval item |
| --- | --- | --- |
| [Vercel](https://vercel.com/pricing) | Web hosting | Pro currently lists $20/month plus usage. Confirm whether the existing account/plan covers this app and set its spending limit. |
| [Render](https://render.com/pricing) | Always-on API and separate worker in Frankfurt | Two Starter instances in the blueprint. Obtain the current dashboard quote for both before provisioning; the public pricing response did not expose a reliable compute price. |
| [Supabase](https://supabase.com/pricing) | EU PostgreSQL, login and private documents | Pro starts at $25/month and includes one project and daily backups with seven-day retention. Separate staging adds project/compute costs; private-object backups need separate provision. |
| [Duffel](https://duffel.com/pricing) | Flight search and in-app orders | Public pricing lists $3/order and 1% managed-content order value; paid ancillary and FX fees may also apply. Excess search is listed at $0.005/search beyond a 1,500:1 search-to-book allowance. Confirm the account's exact contract and treatment of airline handoffs that do not generate Duffel bookings. |
| [SerpApi](https://serpapi.com/pricing) | Optional exact-itinerary airline handoff | Approve a usage plan separately. A single click can make several lookups; fallback official-airline search works without this service. |
| [Resend](https://resend.com/pricing) | Forwarded confirmations, sign-in SMTP and reminders | Free tier lists a 100/day sending limit; confirm receiving quotas, retention and domain eligibility. Do not upgrade automatically. |
| [Google Places](https://developers.google.com/maps/billing-and-pricing/pricing) | Destination discovery | Usage-based, affected by requested fields. Approve the exact SKUs and monthly cap. One guide currently makes two text searches. |
| [Sentry](https://sentry.io/pricing/) | Error monitoring | Start within an approved plan with quotas; no DSN is enabled by default. |
| Domain / OAuth verification | Receiving email and production mailbox access | Domain registration, DNS management and any Google verification/assessment costs need confirmation. |

Known published base components are **$45/month for Vercel Pro + Supabase Pro**, before Render's two instances, staging, metered services, tax and any existing-plan offsets. This is not a complete monthly quote. Final approval must cover the full provider configuration and account-specific flight/payment charges.

Example flight-service calculation using the public Duffel managed-content rates: a $5,000 order implies $3 + $50 = $53 in those fees, excluding ticket cost, payment/FX charges, extras and any negotiated terms. Airline-site booking may avoid Duffel order fees but does not automatically remove search or handoff lookup costs.

Application quotas and caching are implemented. Financial spend caps and 50/80/100% budget alerts must be configured in each connected provider account before launch. Live checkout remains disabled until approval and staging acceptance.

## Private pilot quote — 3 November 2026

The owner approved this incremental hosting quote on 3 November 2026. Live flight/payment fees and optional services still require their separate activation reviews.

The existing Vercel team is already on Pro; this release needs no additional seat or plan upgrade. Existing Vercel subscription charges and metered usage remain.

| New service | Staging and production configuration | Monthly base |
| --- | --- | --- |
| Supabase | A separate Pro organization, two EU Micro projects: $25 organization plan + $20 compute − $10 compute credit | About $35 |
| Render | Two APIs and two workers in Frankfurt, each 0.5 CPU / 512 MB, $7 per service | $28 |
| Google identity | Basic Google OAuth, no billing-enabled Google APIs or mailbox scopes | No new base charge |
| Domain / Resend | Not provisioned; Google sign-in replaces email codes | $0 |
| **Incremental hosting base** | Above the existing Vercel subscription | **About $63/month** |

This quote includes both environments and excludes tax, excess bandwidth/storage/build usage, optional monitoring and provider metering. Supabase compute is billed hourly; its spend cap does not cap compute. Render’s $7 worker price and Supabase’s $25 plan were checked in the signed-in dashboards. The second Micro project’s $10 is confirmed by the public Supabase pricing page. Existing unrelated Supabase/Render projects are not upgraded or altered. Confirm the provider’s final purchase summary before any charge. No paid resources have been created.

Use the application’s quotas, Supabase spend cap, and provider budget alerts. Do not enable autoscaling, paid extras, or automatic plan upgrades. Duffel remains in test mode with live payments off; activating live inventory requires a separate provider-cost review.
