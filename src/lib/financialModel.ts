import type { GrowthOutput, GrowthScenario } from "../types";

function safeDivide(numerator: number, denominator: number): number | null {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) {
    return null;
  }
  return numerator / denominator;
}

/**
 * Illustrative 90-day acquisition model.
 * One repeat probability adds at most one extra booking per first-time customer.
 * Contribution margin is before marketing spend and partner referral fees.
 */
export function calculateGrowth(scenario: GrowthScenario): GrowthOutput {
  const effectivePaidConversionRate =
    scenario.baseConversionRate * (1 + scenario.localizationRelativeUplift);
  const paidCustomers = scenario.paidVisitors * effectivePaidConversionRate;
  const partnerCustomers = scenario.partnerLeads * scenario.partnerConversionRate;
  const firstTimeCustomers = paidCustomers + partnerCustomers;
  const repeatBookings90d = firstTimeCustomers * scenario.repeatBookingProbability90d;
  const totalBookings90d = firstTimeCustomers + repeatBookings90d;
  const grossBookingValue90d = totalBookings90d * scenario.averageOrderValueINR;
  const partnerAcquisitionFees = partnerCustomers * scenario.partnerFeePerBookingINR;
  const totalAcquisitionCost = scenario.marketingSpendINR + partnerAcquisitionFees;
  const contributionBeforeAcquisitionCost = grossBookingValue90d * scenario.contributionMargin;
  const contributionAfterAcquisitionCost =
    contributionBeforeAcquisitionCost - totalAcquisitionCost;
  const blendedCAC = safeDivide(totalAcquisitionCost, firstTimeCustomers);
  const marketingContributionROI = safeDivide(
    contributionAfterAcquisitionCost,
    totalAcquisitionCost,
  );
  const contributionValue90dPerCustomer =
    scenario.averageOrderValueINR *
    scenario.contributionMargin *
    (1 + scenario.repeatBookingProbability90d);
  const contributionValueToCAC =
    blendedCAC === null ? null : safeDivide(contributionValue90dPerCustomer, blendedCAC);

  return {
    effectivePaidConversionRate,
    paidCustomers,
    partnerCustomers,
    firstTimeCustomers,
    repeatBookings90d,
    totalBookings90d,
    grossBookingValue90d,
    partnerAcquisitionFees,
    totalAcquisitionCost,
    contributionBeforeAcquisitionCost,
    contributionAfterAcquisitionCost,
    blendedCAC,
    marketingContributionROI,
    contributionValue90dPerCustomer,
    contributionValueToCAC,
  };
}

export function partnerEconomics(scenario: GrowthScenario) {
  const bookings = scenario.partnerLeads * scenario.partnerConversionRate;
  const grossBookingValue = bookings * scenario.averageOrderValueINR;
  const fees = bookings * scenario.partnerFeePerBookingINR;
  const contributionAfterFees = grossBookingValue * scenario.contributionMargin - fees;
  return {
    bookings,
    grossBookingValue,
    fees,
    contributionAfterFees,
    acquisitionCost: safeDivide(fees, bookings),
  };
}
