/** Two-sided two-proportion sample size per arm. A planning formula, not a study result. */
export function sampleSizePerArm(
  baseline: number,
  variant: number,
  alpha = 0.05,
  power = 0.8,
): number | null {
  if (
    baseline <= 0 ||
    baseline >= 1 ||
    variant <= 0 ||
    variant >= 1 ||
    baseline === variant ||
    alpha <= 0 ||
    alpha >= 1 ||
    power <= 0 ||
    power >= 1
  ) {
    return null;
  }
  const zAlpha = inverseNormal(1 - alpha / 2);
  const zBeta = inverseNormal(power);
  const numerator =
    (zAlpha + zBeta) ** 2 * (baseline * (1 - baseline) + variant * (1 - variant));
  const denominator = (variant - baseline) ** 2;
  if (denominator === 0) return null;
  return Math.ceil(numerator / denominator);
}

function inverseNormal(probability: number): number {
  const a = [
    -3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2,
    -3.066479806614716e1, 2.506628277459239,
  ];
  const b = [
    -5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1,
    -1.328068155288572e1,
  ];
  const c = [
    -7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734,
    4.374664141464968, 2.938163982698783,
  ];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
  const plow = 0.02425;
  const phigh = 1 - plow;
  let q: number;
  if (probability < plow) {
    q = Math.sqrt(-2 * Math.log(probability));
    return (
      (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  }
  if (probability > phigh) {
    q = Math.sqrt(-2 * Math.log(1 - probability));
    return -(
      (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  }
  q = probability - 0.5;
  const r = q * q;
  return (
    ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
  );
}
