import { describe, expect, it } from "vitest";
import { CITIES } from "../data/cities";
import {
  DEFAULT_WEIGHTS,
  rankCities,
  redistributeWeight,
  weightTotal,
  weightedScore,
} from "./cityScoring";

describe("city scoring", () => {
  it("uses the stated default weights", () => {
    expect(weightTotal(DEFAULT_WEIGHTS)).toBe(100);
    const lucknow = CITIES.find((city) => city.id === "lucknow");
    expect(lucknow).toBeTruthy();
    expect(weightedScore(lucknow!.scores, DEFAULT_WEIGHTS)).toBeCloseTo(71.5);
  });

  it("renormalises weights to 100", () => {
    const next = redistributeWeight(DEFAULT_WEIGHTS, "fit", 50);
    expect(weightTotal(next)).toBe(100);
    expect(next.fit).toBe(50);
    expect(next.demand).toBeGreaterThan(0);
  });

  it("ranks Hyderabad first on the default illustrative inputs", () => {
    const ranked = rankCities(CITIES, DEFAULT_WEIGHTS, (city) => city.classification !== "baseline");
    expect(ranked[0]?.id).toBe("hyderabad");
    expect(ranked[0]?.classification).toBe("scale-up");
  });

  it("lets a programming-fit weight lift Lucknow", () => {
    const fitHeavy = redistributeWeight(DEFAULT_WEIGHTS, "fit", 70);
    const ranked = rankCities(CITIES, fitHeavy, (city) => city.classification === "candidate");
    expect(ranked[0]?.id).toBe("lucknow");
  });
});
