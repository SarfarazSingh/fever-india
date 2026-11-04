# Live flight search and airline handoff — 4 November 2026

Production search now uses the live Duffel credential configured in the shared Render environment group. In-app purchases remain disabled. Production API and worker enforce 600 upstream Duffel cabin searches per UTC month across users. Staging retains test inventory.

A production JFK–LHR search for 25 November 2026 returned 157 live offers. The result persisted `live_mode=true`; the shared monthly counter increased to one. Earlier searches during rollout were test snapshots. New code excludes test offers from live searches, separates live/test cache keys, and asks users to refresh saved test searches instead of rendering their synthetic schedules.

Handoff verification found and fixed two issues:
- Duffel zero-pads flight numbers (BA0114, AA0100); Google Flights may return BA114, AA100. Comparison normalizes padding while retaining carrier, suffix, route, dates, times, and cabin checks.
- Google booking options can include cheaper cabins even for a Business itinerary. Selection now rejects known cabin mismatches and requires positive cabin evidence in the booking option or airline URL.

Using current production inventory and SerpApi with the corrected resolver, browser checks reached:
- British Airways BA114, JFK–LHR, 25 November 2026, 21:50–09:45 next day, Business: flight already selected on Flight summary, with Continue to passenger details next.
- American Airlines AA100, same route/date, 18:25–06:20 next day, Flagship Business: passenger-information page with flight selected.

Both airline pages displayed USD 4,248.50 during verification. Airline prices/currencies and fare conditions can differ from Duffel. No passenger data was entered and no ticket was purchased. These checks establish these two itineraries, not universal airline coverage. Unmatched or unverifiable handoffs remain labeled airline searches requiring flight selection.

Validation: 91 backend tests passed, including padded flight identities, cabin downgrade rejection, rejection of sandbox results in live search, and saved test-search refresh behavior.
