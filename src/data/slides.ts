import type { SlideMetadata } from "../types";

export const SLIDES: SlideMetadata[] = [
  {
    id: "opening",
    number: "01",
    nav: "Opening",
    title: "India, Reimagined",
    kicker: "Opening",
    notes:
      "My hypothesis is straightforward. Fever has already introduced extraordinary experiences to Indian audiences. I want to show how I would turn those initial encounters into a repeatable, measurable growth system.",
  },
  {
    id: "opportunity",
    number: "02",
    nav: "Evidence",
    title: "The opportunity is already here",
    kicker: "Evidence",
    notes:
      "I would avoid treating survey intent as retention. My first step would be to inspect actual booking cohorts and understand the gap between the first experience and the second.",
  },
  {
    id: "engine",
    number: "03",
    nav: "Engine",
    title: "The India growth engine",
    kicker: "Operating model",
    notes:
      "I see the opportunity as a system rather than a series of disconnected campaigns. Localization, partnerships, retention, and expansion all need to connect to commercial outcomes.",
  },
  {
    id: "hindi",
    number: "04",
    nav: "Discovery",
    title: "Hindi-first discovery",
    kicker: "Live prototype",
    notes:
      "My proposal is not to translate Fever’s entire India experience into Hindi. It is to test culturally relevant discovery for audiences where Hindi-first creative may improve resonance, beginning in Delhi NCR.",
  },
  {
    id: "whatsapp",
    number: "05",
    nav: "WhatsApp",
    title: "The WhatsApp conversion loop",
    kicker: "Channel test",
    notes:
      "WhatsApp would be one channel hypothesis, not a default solution. I would first validate consent, integration feasibility, user preference, and incremental economics versus Fever’s existing channels.",
  },
  {
    id: "cities",
    number: "06",
    nav: "Cities",
    title: "Where should Fever go next?",
    kicker: "Expansion",
    notes:
      "I would not choose the next city from intuition or from a ranking made without internal data. I would build a repeatable scorecard and then investigate the leading opportunities with operations, marketing, and venue teams.",
  },
  {
    id: "partners",
    number: "07",
    nav: "Partners",
    title: "Partners as distribution",
    kicker: "Business development",
    notes:
      "My priority would be partners with distribution, not just logo value. Every deal should have a clear revenue or customer-acquisition hypothesis and an operating model that can scale.",
  },
  {
    id: "originals",
    number: "08",
    nav: "Programming",
    title: "India’s own Fever Originals",
    kicker: "Product",
    notes:
      "I would not assume that any one musical genre will work everywhere in India. Fever’s existing local repertoire is a starting point. The next step is disciplined format-by-city testing.",
  },
  {
    id: "retention",
    number: "09",
    nav: "Retention",
    title: "From first-time to every-time",
    kicker: "Lifecycle",
    notes:
      "The June audience survey is an interesting starting point. I would want actual customer-level retention, segmented by city, show type, and acquisition channel, before designing the retention programme.",
  },
  {
    id: "simulator",
    number: "10",
    nav: "Metrics",
    title: "The metrics that decide the case",
    kicker: "Economics",
    notes:
      "This is not a forecast. It is a framework for making growth decisions. The purpose is to make assumptions explicit, see which variables matter, and identify the data we would need from Fever before an investment decision.",
  },
  {
    id: "roadmap",
    number: "11",
    nav: "90 days",
    title: "The first 90 days",
    kicker: "Execution",
    notes:
      "The first month should be about listening, learning the numbers, and understanding the operating realities. I would test a few focused hypotheses rather than arrive with a fully predetermined answer.",
  },
  {
    id: "closing",
    number: "12",
    nav: "Close",
    title: "The next chapter",
    kicker: "Close",
    notes:
      "What excites me about this role is the combination of market building, analytical decision-making, and real execution. I would want to understand how the team currently thinks about the greatest growth opportunities in India.",
  },
  {
    id: "method",
    number: "13",
    nav: "Scoring",
    title: "City scoring methodology",
    kicker: "Appendix",
    notes:
      "Walk through the formula, then change a weight or a factor. The point is the discipline of the scorecard, not the sample numbers on the screen.",
    appendix: true,
  },
  {
    id: "experiments",
    number: "14",
    nav: "Experiments",
    title: "Experimentation framework",
    kicker: "Appendix",
    notes:
      "Emphasise randomisation, guardrails, and decision rules. Do not let a pre/post chart stand in for incrementality.",
    appendix: true,
  },
  {
    id: "sources",
    number: "15",
    nav: "Sources",
    title: "Sources and assumptions",
    kicker: "Appendix",
    notes:
      "Separate what was published from what I am proposing to test. If a number is not in the evidence column, it is an assumption.",
    appendix: true,
  },
];

export const SIMULATOR_INDEX = SLIDES.findIndex((slide) => slide.id === "simulator");
