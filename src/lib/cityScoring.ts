import type { City, CityFactorScore, FactorKey, FactorWeights } from "../types";

export const FACTOR_KEYS: FactorKey[] = ["demand", "venue", "audience", "fit", "partners"];

export const FACTOR_LABELS: Record<FactorKey, string> = {
  demand: "Demand / search interest",
  venue: "Venue availability",
  audience: "Addressable audience",
  fit: "Programming fit",
  partners: "Partner distribution",
};

export const DEFAULT_WEIGHTS: FactorWeights = {
  demand: 25,
  venue: 20,
  audience: 20,
  fit: 20,
  partners: 15,
};

export function weightTotal(weights: FactorWeights): number {
  return FACTOR_KEYS.reduce((sum, key) => sum + weights[key], 0);
}

export function weightedScore(scores: CityFactorScore, weights: FactorWeights): number {
  const total = weightTotal(weights);
  if (total === 0) return 0;
  return FACTOR_KEYS.reduce((sum, key) => sum + (weights[key] / total) * scores[key], 0);
}

/** Points removed because every factor input is unverified. This is not a confidence interval. */
export function unverifiedDiscount(classification: City["classification"]): number {
  if (classification === "baseline") return 6;
  if (classification === "scale-up") return 10;
  return 12;
}

export function riskAdjustedScore(city: City, weights: FactorWeights): number {
  return Math.max(0, weightedScore(city.scores, weights) - unverifiedDiscount(city.classification));
}

export function redistributeWeight(
  weights: FactorWeights,
  key: FactorKey,
  nextValue: number,
): FactorWeights {
  const value = clamp(Math.round(nextValue), 0, 100);
  const others = FACTOR_KEYS.filter((item) => item !== key);
  const remain = 100 - value;
  const sumOthers = others.reduce((sum, item) => sum + weights[item], 0);
  const next: FactorWeights = { ...weights, [key]: value };

  if (sumOthers <= 0) {
    const base = Math.floor(remain / others.length);
    let leftover = remain - base * others.length;
    others.forEach((item) => {
      next[item] = base + (leftover > 0 ? 1 : 0);
      leftover -= leftover > 0 ? 1 : 0;
    });
    return next;
  }

  const raw = others.map((item) => (weights[item] / sumOthers) * remain);
  const floors = raw.map((item) => Math.floor(item));
  let leftover = remain - floors.reduce((sum, item) => sum + item, 0);
  const order = raw
    .map((item, index) => ({ index, frac: item - floors[index] }))
    .sort((a, b) => b.frac - a.frac);
  order.forEach((item) => {
    if (leftover > 0) {
      floors[item.index] += 1;
      leftover -= 1;
    }
  });
  others.forEach((item, index) => {
    next[item] = floors[index];
  });
  return next;
}

export function rankCities<T extends City>(
  cities: T[],
  weights: FactorWeights,
  eligible?: (city: T) => boolean,
): T[] {
  return cities
    .filter((city) => (eligible ? eligible(city) : true))
    .slice()
    .sort((a, b) => weightedScore(b.scores, weights) - weightedScore(a.scores, weights));
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
