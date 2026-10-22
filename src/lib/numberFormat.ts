const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function formatINR(value: number): string {
  return inr.format(Math.round(value));
}

export function formatNumber(value: number): string {
  return num.format(Math.round(value));
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatMultiple(value: number): string {
  const sign = value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(2)}×`;
}

export function formatOrDash(value: number | null, format: (n: number) => string): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return format(value);
}
