# Integration activation quote — 3 November 2026

Decision recorded 4 November 2026: the owner requested **Keep new paid integrations off**. Google Places, Duffel live search and in-app purchases remain disabled. Completing Duffel billing does not authorize activation. Only the existing free SerpApi allowance and separately consented Gmail imports/reminders are configured; no provider upgrade is authorized.

Existing hosting remains approximately $53/month before tax and usage, above the existing Vercel subscription.

| Integration | Proposed activation boundary | Incremental charge |
| --- | --- | --- |
| Airline handoffs | Existing SerpApi Free account; 250 searches/month, no upgrade | $0; verified 232 searches remained before this review’s test lookups |
| Gmail import and trip emails | Separate read-only mailbox and send-email consent for the two private accounts | No new base service fee; Google quotas apply |
| Google Places | Text Search Pro fields only; 450 API requests/month in production and 50 in staging; no photos, reviews or Enterprise fields | Expected $0 within the shared 5,000-request free allowance; worst case $16/month before tax if that allowance is used elsewhere. Request approval ceiling: $20/month, no upgrades |
| Duffel live searches | Reserve at most 600 upstream cabin searches/month in production; existing staging stays test | At the published excess-search price of $0.005, worst case $3/month before tax. Request approval ceiling: $5/month |
| Duffel purchases | Only purchases the traveler explicitly reviews and submits; no automatic purchases | Published $3/order + 1% managed-content order value; paid ancillaries $2 each, 2% FX when currency conversion is required. Ticket price and airline/card charges are additional; show current pricing before acceptance |
| Automated check-in | No production provider account is configured; legacy browser bots are not validated | No service purchase proposed; airline/provider support must be established before activation |

Sources checked: https://duffel.com/pricing and https://developers.google.com/maps/billing-and-pricing/pricing . The current provider checkout and contract govern. Application quotas bound this app’s requests; Google’s free allowance is shared with other projects on the billing account. No live ticket or paid add-on is purchased by approving setup.

On 4 November 2026 the owner approved live Duffel search up to $5/month. Production reserves at most 600 upstream Duffel cabin searches per UTC month across accounts; staging remains on test inventory. This bounds application requests, not other usage on the Duffel account or changes to provider pricing. In-app purchases remain disabled.
