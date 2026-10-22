import { describe, expect, it } from "vitest";
import { BASE_SCENARIO } from "../data/scenarios";
import { calculateGrowth } from "./financialModel";

describe("calculateGrowth", () => {
  it("matches the documented base case", () => {
    const result = calculateGrowth(BASE_SCENARIO);
    expect(result.paidCustomers).toBeCloseTo(1400);
    expect(result.partnerCustomers).toBeCloseTo(80);
    expect(result.firstTimeCustomers).toBeCloseTo(1480);
    expect(result.repeatBookings90d).toBeCloseTo(266.4);
    expect(result.totalBookings90d).toBeCloseTo(1746.4);
    expect(result.grossBookingValue90d).toBeCloseTo(3143520);
    expect(result.partnerAcquisitionFees).toBeCloseTo(12000);
    expect(result.totalAcquisitionCost).toBeCloseTo(412000);
    expect(result.contributionBeforeAcquisitionCost).toBeCloseTo(943056);
    expect(result.contributionAfterAcquisitionCost).toBeCloseTo(531056);
    expect(result.blendedCAC).toBeCloseTo(412000 / 1480);
    expect(result.marketingContributionROI).toBeCloseTo(531056 / 412000);
    expect(result.contributionValue90dPerCustomer).toBeCloseTo(637.2);
    expect(result.contributionValueToCAC).toBeCloseTo(637.2 / (412000 / 1480));
  });

  it("applies localization as a relative lift on paid conversion only", () => {
    const result = calculateGrowth({ ...BASE_SCENARIO, localizationRelativeUplift: 0.15 });
    expect(result.effectivePaidConversionRate).toBeCloseTo(0.028 * 1.15);
    expect(result.paidCustomers).toBeCloseTo(50000 * 0.028 * 1.15);
    expect(result.partnerCustomers).toBeCloseTo(80);
  });

  it("returns null ratios when there is nothing to divide", () => {
    const empty = calculateGrowth({
      ...BASE_SCENARIO,
      paidVisitors: 0,
      partnerLeads: 0,
      marketingSpendINR: 0,
    });
    expect(empty.firstTimeCustomers).toBe(0);
    expect(empty.blendedCAC).toBeNull();
    expect(empty.marketingContributionROI).toBeNull();
    expect(empty.contributionValueToCAC).toBeNull();
  });

  it("keeps one repeat booking as the ceiling of the 90-day probability", () => {
    const result = calculateGrowth({ ...BASE_SCENARIO, repeatBookingProbability90d: 0.4 });
    expect(result.repeatBookings90d).toBeCloseTo(result.firstTimeCustomers * 0.4);
    expect(result.repeatBookings90d).toBeLessThanOrEqual(result.firstTimeCustomers);
  });
});
