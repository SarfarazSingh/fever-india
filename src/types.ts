export type FactorKey = "demand" | "venue" | "audience" | "fit" | "partners";

export type FactorWeights = Record<FactorKey, number>;

export type CityFactorScore = Record<FactorKey, number>;

export type CityClassification = "baseline" | "candidate" | "scale-up";

export type City = {
  id: string;
  name: string;
  lon: number;
  lat: number;
  classification: CityClassification;
  scores: CityFactorScore;
  why: string;
  missing: string;
  formatHypothesis: string;
  partnerCategory: string;
  venue: string;
  launchKpi: string;
  risk: string;
  gate: string;
};

export type PartnerChannelId =
  | "blended"
  | "hotels"
  | "banks"
  | "corporates"
  | "occasions"
  | "custom";

export type PartnerChannel = {
  id: Exclude<PartnerChannelId, "blended" | "custom">;
  number: string;
  title: string;
  summary: string;
  points: string[];
  target: string;
  valueForPartner: string;
  valueForFever: string;
  structure: string;
  dependencies: string;
  metrics: string[];
  risk: string;
  pilot: string;
  leads: number;
  conversion: number;
  fee: number;
};

export type ExperienceConcept = {
  id: string;
  title: string;
  eyebrow: string;
  relation: "Existing Candlelight territory" | "Format extension to test";
  summary: string;
  audience: string;
  positioning: string;
  city: string;
  venue: string;
  scale: string;
  measure: string[];
  gate: string;
  familiarity: "Higher" | "Medium" | "Lower";
  productionFit: "Higher" | "Medium" | "Lower";
  localizationEffort: "Higher" | "Medium" | "Lower";
  complexity: "Higher" | "Medium" | "Lower";
  tone: "gold" | "violet" | "blue" | "magenta" | "ink";
};

export type GrowthScenario = {
  paidVisitors: number;
  baseConversionRate: number;
  localizationRelativeUplift: number;
  marketingSpendINR: number;
  partnerLeads: number;
  partnerConversionRate: number;
  partnerFeePerBookingINR: number;
  averageOrderValueINR: number;
  contributionMargin: number;
  repeatBookingProbability90d: number;
  partnerChannel: PartnerChannelId;
};

export type GrowthOutput = {
  effectivePaidConversionRate: number;
  paidCustomers: number;
  partnerCustomers: number;
  firstTimeCustomers: number;
  repeatBookings90d: number;
  totalBookings90d: number;
  grossBookingValue90d: number;
  partnerAcquisitionFees: number;
  totalAcquisitionCost: number;
  contributionBeforeAcquisitionCost: number;
  contributionAfterAcquisitionCost: number;
  blendedCAC: number | null;
  marketingContributionROI: number | null;
  contributionValue90dPerCustomer: number;
  contributionValueToCAC: number | null;
};

export type Experiment = {
  id: string;
  code: string;
  name: string;
  hypothesis: string;
  segment: string;
  treatment: string;
  control: string;
  primary: string;
  guardrails: string[];
  sampleNote: string;
  owner: string;
  duration: string;
  decision: string;
};

export type EvidenceSource = {
  id: string;
  group: "evidence" | "hypothesis";
  title: string;
  detail: string;
  date: string;
  href?: string;
};

export type SlideMetadata = {
  id: string;
  number: string;
  nav: string;
  title: string;
  kicker: string;
  notes: string;
  appendix?: boolean;
};

export type RoadmapMilestone = {
  id: string;
  phase: "diagnose" | "experiment" | "decide";
  lane: "Growth" | "Marketing" | "Partnerships" | "Operations" | "Data / Product";
  title: string;
  owner: string;
  dependency: string;
  input: string;
  deliverable: string;
  criterion: string;
};
