import type { GrowthScenario } from "../types";

export const BASE_SCENARIO: GrowthScenario = {
  paidVisitors: 50000,
  baseConversionRate: 0.028,
  localizationRelativeUplift: 0,
  marketingSpendINR: 400000,
  partnerLeads: 2000,
  partnerConversionRate: 0.04,
  partnerFeePerBookingINR: 150,
  averageOrderValueINR: 1800,
  contributionMargin: 0.3,
  repeatBookingProbability90d: 0.18,
  partnerChannel: "blended",
};

/** Opening state applies the Scene 04 demonstration lift. Reset returns to the base case. */
export const INITIAL_SCENARIO: GrowthScenario = {
  ...BASE_SCENARIO,
  localizationRelativeUplift: 0.15,
};

export type PresetId = "conservative" | "base" | "upside";

export const PRESETS: Record<
  PresetId,
  { id: PresetId; label: string; note: string; assumptions: string[]; scenario: GrowthScenario }
> = {
  conservative: {
    id: "conservative",
    label: "Conservative",
    note: "Weaker conversion, no localization lift, heavier spend, and a low repeat rate.",
    assumptions: [
      "40,000 paid visitors at a 2.0% baseline conversion",
      "0% localization lift",
      "₹5,00,000 marketing spend",
      "1,000 partner leads at 3% conversion and ₹200 fee",
      "₹1,600 average order value, 22% contribution margin",
      "8% probability of one extra booking within 90 days",
    ],
    scenario: {
      paidVisitors: 40000,
      baseConversionRate: 0.02,
      localizationRelativeUplift: 0,
      marketingSpendINR: 500000,
      partnerLeads: 1000,
      partnerConversionRate: 0.03,
      partnerFeePerBookingINR: 200,
      averageOrderValueINR: 1600,
      contributionMargin: 0.22,
      repeatBookingProbability90d: 0.08,
      partnerChannel: "blended",
    },
  },
  base: {
    id: "base",
    label: "Base case",
    note: "The documented demonstration case, with localization lift held at zero until a test earns it.",
    assumptions: [
      "50,000 paid visitors at a 2.8% baseline conversion",
      "0% localization lift",
      "₹4,00,000 marketing spend",
      "2,000 partner leads at 4% conversion and ₹150 fee",
      "₹1,800 average order value, 30% contribution margin",
      "18% probability of one extra booking within 90 days",
    ],
    scenario: { ...BASE_SCENARIO },
  },
  upside: {
    id: "upside",
    label: "Upside",
    note: "A stronger acquisition mix and the +15% localization hypothesis, still not a forecast.",
    assumptions: [
      "70,000 paid visitors at a 4.0% baseline conversion",
      "+15% relative localization lift",
      "₹4,50,000 marketing spend",
      "6,000 partner leads at 6% conversion and ₹120 fee",
      "₹2,100 average order value, 34% contribution margin",
      "28% probability of one extra booking within 90 days",
    ],
    scenario: {
      paidVisitors: 70000,
      baseConversionRate: 0.04,
      localizationRelativeUplift: 0.15,
      marketingSpendINR: 450000,
      partnerLeads: 6000,
      partnerConversionRate: 0.06,
      partnerFeePerBookingINR: 120,
      averageOrderValueINR: 2100,
      contributionMargin: 0.34,
      repeatBookingProbability90d: 0.28,
      partnerChannel: "blended",
    },
  },
};
