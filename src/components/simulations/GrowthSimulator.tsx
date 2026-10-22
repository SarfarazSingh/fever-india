import { useState } from "react";
import { useGrowth } from "../../app/state/GrowthScenarioContext";
import { formatINR, formatMultiple, formatNumber, formatPercent } from "../../lib/numberFormat";
import { AnimatedNumber } from "../motion/AnimatedNumber";
import { DisclaimerLabel } from "../ui/DisclaimerLabel";
import { WeightSlider } from "../ui/WeightSlider";
import type { GrowthOutput } from "../../types";

type MetricId = "customers" | "gbv" | "after" | "cac" | "proxy" | "ratio" | "roi";

const DETAILS: Record<MetricId, { says: string; doesNot: string }> = {
  customers: {
    says: "Paid visitors × conversion × (1 + localization lift), plus partner leads × partner conversion.",
    doesNot: "Not a forecast of Fever’s India customers.",
  },
  gbv: {
    says: "First-time customers, plus at most one repeat booking each, times average order value.",
    doesNot: "Not lifetime value, and not revenue after refunds.",
  },
  after: {
    says: "Gross booking value × contribution margin, minus marketing spend and partner fees.",
    doesNot: "Margin is before those costs. This is not company profit.",
  },
  cac: {
    says: "Marketing spend plus partner fees, divided by first-time customers.",
    doesNot: "Shown as — when there are no customers.",
  },
  proxy: {
    says: "Average order value × margin × (1 + repeat probability). A 90-day contribution per customer.",
    doesNot: "This is not lifetime value.",
  },
  ratio: {
    says: "90-day contribution per customer divided by blended CAC.",
    doesNot: "Below 1×, the modelled acquisition cost is not covered.",
  },
  roi: {
    says: "Contribution after acquisition divided by acquisition cost.",
    doesNot: "A contribution return, not event profit. Shown as — when cost is zero.",
  },
};

export function GrowthSimulator() {
  const { scenario, output, update, reset } = useGrowth();
  const [open, setOpen] = useState<MetricId>("after");
  const [adjust, setAdjust] = useState(false);
  const detail = DETAILS[open];
  const cards: { id: MetricId; label: string; value: number | null; format: (value: number) => string }[] = [
    { id: "after", label: "Contribution after acquisition", value: output.contributionAfterAcquisitionCost, format: formatINR },
    { id: "roi", label: "Acquisition ROI", value: output.marketingContributionROI, format: formatMultiple },
    { id: "cac", label: "Blended CAC", value: output.blendedCAC, format: formatINR },
    { id: "customers", label: "First-time customers", value: output.firstTimeCustomers, format: formatNumber },
    { id: "gbv", label: "90-day gross bookings", value: output.grossBookingValue90d, format: formatINR },
    { id: "proxy", label: "90-day contribution / customer", value: output.contributionValue90dPerCustomer, format: formatINR },
    { id: "ratio", label: "Contribution / CAC", value: output.contributionValueToCAC, format: formatMultiple },
  ];

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <DisclaimerLabel>Illustrative 90-day case — not Fever internal data</DisclaimerLabel>
        <div className="flex gap-2">
          <button type="button" className="focus-ring rounded-full border border-white/15 px-3 py-1.5 text-[14px]" onClick={() => setAdjust((value) => !value)}>
            {adjust ? "Hide assumptions" : "Adjust assumptions"}
          </button>
          <button type="button" className="focus-ring rounded-full bg-white/10 px-3 py-1.5 text-[14px]" onClick={reset}>
            Reset to base case
          </button>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <MetricCard key={card.id} {...card} active={open === card.id} onSelect={() => setOpen(card.id)} />
        ))}
      </div>
      <div className="rounded-2xl border border-gold/30 bg-white/[0.03] px-4 py-3">
        <p className="text-[14px] tracking-[0.14em] text-gold uppercase">{cards.find((card) => card.id === open)?.label}</p>
        <ul className="mt-1 grid gap-1 text-[16px] leading-snug md:grid-cols-2">
          <li>· {detail.says}</li>
          <li>· {detail.doesNot}</li>
        </ul>
      </div>
      {adjust && (
        <div className="grid gap-3 rounded-2xl border border-white/10 p-3 sm:grid-cols-2 lg:grid-cols-3">
          <WeightSlider label="Paid visitors" min={10000} max={100000} step={1000} value={scenario.paidVisitors} display={formatNumber(scenario.paidVisitors)} onChange={(value) => update({ paidVisitors: value })} />
          <WeightSlider label="Baseline conversion" min={0.01} max={0.06} step={0.001} value={scenario.baseConversionRate} display={formatPercent(scenario.baseConversionRate)} onChange={(value) => update({ baseConversionRate: value })} />
          <WeightSlider label="Localization lift" min={0} max={0.3} step={0.01} value={scenario.localizationRelativeUplift} display={formatPercent(scenario.localizationRelativeUplift, 0)} onChange={(value) => update({ localizationRelativeUplift: value })} />
          <WeightSlider label="Average order value" min={1000} max={3500} step={50} value={scenario.averageOrderValueINR} display={formatINR(scenario.averageOrderValueINR)} onChange={(value) => update({ averageOrderValueINR: value })} />
          <WeightSlider label="Contribution margin" min={0.15} max={0.45} step={0.01} value={scenario.contributionMargin} display={formatPercent(scenario.contributionMargin, 0)} onChange={(value) => update({ contributionMargin: value })} />
          <WeightSlider label="90-day repeat probability" min={0} max={0.4} step={0.01} value={scenario.repeatBookingProbability90d} display={formatPercent(scenario.repeatBookingProbability90d, 0)} onChange={(value) => update({ repeatBookingProbability90d: value })} />
        </div>
      )}
      <p className="text-[14px] text-soft">One repeat means at most one extra booking. Excludes fixed city costs, capacity, taxes, and refunds. <FlowLine output={output} /></p>
    </div>
  );
}

function MetricCard({
  label,
  value,
  format,
  active,
  onSelect,
}: {
  label: string;
  value: number | null;
  format: (value: number) => string;
  active: boolean;
  onSelect: () => void;
}) {
  const negative = typeof value === "number" && value < 0;
  return (
    <button type="button" onClick={onSelect} className={`interactive-card focus-ring min-h-[108px] rounded-2xl px-3 py-3 text-left ${active ? "border-gold" : ""} ${negative ? "text-magenta" : ""}`}>
      <p className="text-[13px] leading-tight text-soft">{label}</p>
      <p className="tabular mt-2 text-[clamp(22px,2vw,32px)] leading-none">
        {value === null ? "—" : <AnimatedNumber value={value} format={format} />}
      </p>
      <p className="card-action mt-3 inline-flex text-[13px] text-gold">{active ? "Showing detail" : "See formula →"}</p>
    </button>
  );
}

function FlowLine({ output }: { output: GrowthOutput }) {
  return (
    <span>
      {formatNumber(output.firstTimeCustomers)} first-time · {formatNumber(output.repeatBookings90d)} repeat bookings.
    </span>
  );
}
