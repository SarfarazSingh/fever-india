import type { EvidenceSource } from "../types";

export const AUDIENCE_SOURCE = {
  publisher: "Fever / Live Your City newsroom",
  date: "24 June 2026",
  href: "https://newsroom.feverup.com/en-IN/267465-candlelight-is-changing-how-india-experiences-classical-music-concerts/",
};

export const METRICS = [
  {
    id: "first-time",
    value: 83,
    prefix: "",
    suffix: "%",
    label: "First-time Candlelight attendees",
    says: "Most people in the reported audience were experiencing Candlelight for the first time. That is an acquisition signal.",
    doesNot: "It does not say those attendees will book again, or what it cost to bring them in.",
    next: "Booking-cohort repeat rate by city, format, and acquisition channel.",
  },
  {
    id: "intent",
    value: 84,
    prefix: "",
    suffix: "%",
    label: "Expressed intent to attend future Candlelight or other classical concerts",
    says: "A large share of respondents said they intend to attend another concert. Interest is real enough to test.",
    doesNot: "This is not a measured repeat-booking rate. Intent is not a second ticket.",
    next: "The gap between stated intent and a completed second booking within 90 days.",
  },
  {
    id: "programme",
    value: 80,
    prefix: "~",
    suffix: "%",
    label: "Attendees citing the musical programme as their primary motivation",
    says: "The music itself, not only the setting, appears central to why people come.",
    doesNot: "It does not prove that any one genre will travel to every Indian city.",
    next: "Fill rate, ticket yield, and repeat behaviour by format and city.",
  },
] as const;

export const DOCUMENTED_CITIES = [
  "Delhi NCR",
  "Mumbai",
  "Bengaluru",
  "Chennai",
  "Pune",
  "Jaipur",
  "Ahmedabad",
];

export const SOURCES: EvidenceSource[] = [
  {
    id: "role",
    group: "evidence",
    title: "Fever official job posting",
    detail:
      "Growth Manager — Hindi Speaker. The posting describes ownership of the India growth roadmap, partner advice, CAC / LTV / ROI, and coordination with regional teams.",
    date: "Accessed 22 October 2026",
    href: "https://careers.feverup.com/jobs/4964149101/growth-manager-hindi-speaker/",
  },
  {
    id: "home",
    group: "evidence",
    title: "Fever",
    detail: "Consumer marketplace for live entertainment and cultural experiences.",
    date: "Accessed 22 October 2026",
    href: "https://feverup.com/",
  },
  {
    id: "newsroom",
    group: "evidence",
    title: "Fever India newsroom",
    detail: "Public newsroom used as the source of India programming announcements. Historic releases are not treated as a live inventory or a sales report.",
    date: "Accessed 22 October 2026",
    href: "https://newsroom.feverup.com/en-IN/",
  },
  {
    id: "insights",
    group: "evidence",
    title: "Candlelight audience insights",
    detail:
      "83% first-time attendees. 84% expressed intent to attend future Candlelight or other classical concerts. Nearly 80% cited the musical programme as their primary motivation. The 84% figure is intent, not a repeat-booking rate.",
    date: "24 June 2026",
    href: "https://newsroom.feverup.com/en-IN/267465-candlelight-is-changing-how-india-experiences-classical-music-concerts/",
  },
  {
    id: "gurugram",
    group: "evidence",
    title: "Candlelight Signature in Gurugram",
    detail:
      "Public announcement of Bollywood and Sufi Candlelight Signature programming in Gurugram. Used only as evidence that locally familiar repertoire is already part of the public story.",
    date: "Newsroom release",
    href: "https://newsroom.feverup.com/en-IN/269427-the-familiar-heard-differently-candlelight-signature-in-gurugram/",
  },
  {
    id: "releases",
    group: "evidence",
    title: "Fever India news release archive",
    detail: "Archive of public India announcements, including ghazal programming referenced as public evidence rather than as a new approved product.",
    date: "Accessed 22 October 2026",
    href: "https://newsroom.feverup.com/en-IN/releases/",
  },
  {
    id: "delhi",
    group: "evidence",
    title: "New Delhi Candlelight listing",
    detail: "Public Live Your City listing used as evidence of Delhi programming. Availability and sales are not inferred from the listing.",
    date: "Accessed 22 October 2026",
    href: "https://liveyourcity.com/en/new-delhi/candlelight",
  },
  {
    id: "hindi",
    group: "hypothesis",
    title: "Hindi-first creative test",
    detail:
      "A relative conversion lift from Hindi-first creative in Delhi NCR. The opening demonstration uses +15%. It is an assumption to test, not a claim that Hindi outperforms English.",
    date: "Illustrative",
  },
  {
    id: "whatsapp",
    group: "hypothesis",
    title: "WhatsApp consent experiment",
    detail:
      "A permission-based messaging journey. No opt-in, click, booking, or incremental CAC result is shown because none has been observed.",
    date: "Illustrative",
  },
  {
    id: "partners",
    group: "hypothesis",
    title: "Partner economics",
    detail:
      "Lead volumes, conversion, and referral fees by channel are synthetic inputs for the simulator.",
    date: "Illustrative",
  },
  {
    id: "cities",
    group: "hypothesis",
    title: "City scoring",
    detail:
      "Demand, venue, audience, fit, and partner scores are editable sample inputs. They are not research-backed market statistics.",
    date: "Illustrative",
  },
  {
    id: "roi",
    group: "hypothesis",
    title: "90-day contribution scenarios",
    detail:
      "Visitors, conversion, spend, margin, and repeat probability are fictional. The output is a decision framework, not a forecast or Fever internal result.",
    date: "Illustrative",
  },
  {
    id: "retention",
    group: "hypothesis",
    title: "Retention intervention",
    detail:
      "Both cohort curves are hypothetical. Neither line is Fever’s current retention.",
    date: "Illustrative",
  },
];
