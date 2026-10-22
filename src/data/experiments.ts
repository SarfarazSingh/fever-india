import type { Experiment } from "../types";

export const EXPERIMENTS: Experiment[] = [
  {
    id: "hindi",
    code: "A",
    name: "Hindi-first versus English discovery",
    hypothesis:
      "In a defined Delhi NCR audience, Hindi-first creative and a Hindi landing experience will raise first-booking conversion relative to the current English journey.",
    segment: "Delhi NCR eligible traffic. Not all India traffic, and not an assumption that every visitor prefers Hindi.",
    treatment: "Hindi-first creative and landing experience.",
    control: "Current English-language acquisition journey.",
    primary: "First-booking conversion rate.",
    guardrails: ["CAC", "Refund rate", "Support contacts", "Checkout completion"],
    sampleNote:
      "Power the test from real traffic and the smallest lift worth operating. The calculator below is a worked example using fictional rates.",
    owner: "Growth, with marketing and product.",
    duration: "Long enough to cover weekday and weekend demand. Set after baseline volumes are known.",
    decision: "Scale only if the primary metric improves and guardrails hold. A flat result is a useful result.",
  },
  {
    id: "partner",
    code: "B",
    name: "Partner-driven versus paid discovery",
    hypothesis:
      "A defined partner channel can acquire first-time customers at a lower incremental CAC than paid acquisition, at a comparable contribution margin.",
    segment: "New-to-Fever customers in one city, tagged by exposure.",
    treatment: "Partner referral or co-promotion with explicit consent and attribution.",
    control: "Paid acquisition in the same city and period, held out from the partner offer.",
    primary: "Incremental first bookings and blended CAC.",
    guardrails: ["Contribution after fees", "Refund rate", "Cannibalisation of direct demand"],
    sampleNote: "Needs a holdout. A rise in bookings after a partnership announcement is not incrementality.",
    owner: "Partnerships and growth.",
    duration: "One partner, one city, one defined flight.",
    decision: "Continue only if incremental bookings remain attractive after fees and displaced demand.",
  },
  {
    id: "post-event",
    code: "C",
    name: "Personalised versus generic post-event recommendations",
    hypothesis:
      "A recommendation tied to the show someone just attended will produce more second bookings than a generic city newsletter.",
    segment: "First-time attendees in one city who can be reached under existing consent.",
    treatment: "Post-show message with a format-matched next experience.",
    control: "Generic next-event message, or no lifecycle message, assigned at random.",
    primary: "90-day second-booking rate.",
    guardrails: ["Opt-out", "Support contacts", "Discount depth"],
    sampleNote: "Randomise people, not nights, where the channel allows it. Compare cohorts, not a before-and-after.",
    owner: "CRM / lifecycle with growth.",
    duration: "Follow each cohort for 90 days.",
    decision: "Keep the journey only if the second booking rises without buying it through a standing discount.",
  },
  {
    id: "format",
    code: "D",
    name: "Localised format programming",
    hypothesis:
      "A locally familiar format will deliver better yield or repeat than an unfamiliar title in the same city and room type.",
    segment: "One candidate city, new session dates, comparable capacity.",
    treatment: "Local-format pilot.",
    control: "A proven format in the same city, priced and staffed on the same rules.",
    primary: "Ticket yield and event contribution.",
    guardrails: ["Refund / cancellation", "Satisfaction", "Operating incidents"],
    sampleNote: "Dates and seasons confound format tests. Pre-commit the comparison before tickets go on sale.",
    owner: "Programming, city operations, and growth.",
    duration: "A pre-agreed pair of dates, then a read of repeat after 90 days.",
    decision: "A second run requires contribution, not only a full opening night.",
  },
  {
    id: "referral",
    code: "E",
    name: "Referral incentive versus no incentive",
    hypothesis:
      "A modest, capped referral incentive will create incremental new customers beyond organic sharing.",
    segment: "Recent attendees with permission to be contacted.",
    treatment: "A single, capped referral reward.",
    control: "A share action with no reward.",
    primary: "Incremental new customers who book.",
    guardrails: ["Reward cost", "Fraud / self-referral", "Discount dependence"],
    sampleNote: "Count booked new customers, not shares. Shares are a vanity step.",
    owner: "Growth.",
    duration: "One campaign cycle plus a booking window.",
    decision: "Keep the incentive only if new-customer contribution exceeds the reward and the operational cost.",
  },
];

export const MOCK_SCHEMA = `events (
  event_id, city, format, session_date, capacity
)
bookings (
  booking_id, user_id, event_id, booked_at,
  channel, partner_id, order_value, status
)
experiment_assignments (
  user_id, experiment_id, arm, assigned_at
)`;

export const MOCK_SQL = `-- Illustrative query. This is not a Fever table.
select
  a.arm,
  count(distinct a.user_id) as assigned,
  count(distinct case when b.status = 'booked' then b.user_id end) as booked
from experiment_assignments a
left join bookings b
  on b.user_id = a.user_id
 and b.booked_at >= a.assigned_at
where a.experiment_id = 'hindi_first_delhi'
group by a.arm;`;
