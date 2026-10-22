import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PRESETS, type PresetId } from "../../data/scenarios";
import { calculateGrowth } from "../../lib/financialModel";
import { formatINR, formatNumber } from "../../lib/numberFormat";
import type { GrowthOutput, GrowthScenario } from "../../types";

const axis = { fill: "#A7B2BA", fontSize: 14 };
const grid = "rgba(255,255,255,0.08)";

export type ChartId = "waterfall" | "channel" | "sensitivity" | "scenarios" | "bridge";

export const CHARTS: { id: ChartId; label: string }[] = [
  { id: "waterfall", label: "Booking waterfall" },
  { id: "channel", label: "Channel mix" },
  { id: "sensitivity", label: "CAC sensitivity" },
  { id: "scenarios", label: "Scenarios" },
  { id: "bridge", label: "Contribution bridge" },
];

export function SimulatorCharts({
  id,
  scenario,
  output,
}: {
  id: ChartId;
  scenario: GrowthScenario;
  output: GrowthOutput;
}) {
  return (
    <div className="h-[250px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        {id === "waterfall" ? (
          <Waterfall output={output} />
        ) : id === "channel" ? (
          <Channel output={output} />
        ) : id === "sensitivity" ? (
          <Sensitivity scenario={scenario} />
        ) : id === "scenarios" ? (
          <Scenarios scenario={scenario} />
        ) : (
          <Bridge scenario={scenario} output={output} />
        )}
      </ResponsiveContainer>
    </div>
  );
}

function tipStyle() {
  return {
    background: "#031419",
    border: "1px solid rgba(255,255,255,0.15)",
    borderRadius: 12,
    color: "#F8FAFC",
    fontSize: 14,
  };
}

function Waterfall({ output }: { output: GrowthOutput }) {
  const rows = [
    row("Paid", 0, output.paidCustomers, "#0079CA"),
    row("Partner", output.paidCustomers, output.partnerCustomers, "#6F41D7"),
    row("Repeat", output.paidCustomers + output.partnerCustomers, output.repeatBookings90d, "#E9BC70"),
    row("Total", 0, output.totalBookings90d, "#F8FAFC"),
  ];
  return (
    <BarChart data={rows}>
      <CartesianGrid stroke={grid} vertical={false} />
      <XAxis dataKey="name" tick={axis} />
      <YAxis tick={axis} tickFormatter={(value) => formatNumber(Number(value))} width={64} />
      <Tooltip contentStyle={tipStyle()} formatter={(value) => formatNumber(Number(value))} />
      <Bar dataKey="offset" stackId="a" fill="transparent" />
      <Bar dataKey="amount" stackId="a" radius={[6, 6, 0, 0]}>
        {rows.map((item) => (
          <Cell key={item.name} fill={item.fill} />
        ))}
      </Bar>
    </BarChart>
  );
}

function Channel({ output }: { output: GrowthOutput }) {
  const data = [
    { name: "Paid customers", value: output.paidCustomers, fill: "#0079CA" },
    { name: "Partner customers", value: output.partnerCustomers, fill: "#6F41D7" },
  ];
  return (
    <BarChart data={data}>
      <CartesianGrid stroke={grid} vertical={false} />
      <XAxis dataKey="name" tick={axis} />
      <YAxis tick={axis} tickFormatter={(value) => formatNumber(Number(value))} width={64} />
      <Tooltip contentStyle={tipStyle()} formatter={(value) => formatNumber(Number(value))} />
      <Bar dataKey="value" radius={[6, 6, 0, 0]}>
        {data.map((item) => (
          <Cell key={item.name} fill={item.fill} />
        ))}
      </Bar>
    </BarChart>
  );
}

function Sensitivity({ scenario }: { scenario: GrowthScenario }) {
  const data = [];
  for (let spend = 200000; spend <= 2000000; spend += 200000) {
    const result = calculateGrowth({ ...scenario, marketingSpendINR: spend });
    data.push({ spend: `₹${Math.round(spend / 100000)}L`, cac: result.blendedCAC ?? 0 });
  }
  return (
    <LineChart data={data}>
      <CartesianGrid stroke={grid} vertical={false} />
      <XAxis dataKey="spend" tick={axis} />
      <YAxis tick={axis} tickFormatter={(value) => formatNumber(Number(value))} width={64} />
      <Tooltip contentStyle={tipStyle()} formatter={(value) => formatINR(Number(value))} />
      <Line type="monotone" dataKey="cac" name="Blended CAC" stroke="#0079CA" strokeWidth={2.5} dot={false} />
    </LineChart>
  );
}

function Scenarios({ scenario }: { scenario: GrowthScenario }) {
  const cases: { name: string; value: number }[] = (Object.keys(PRESETS) as PresetId[]).map((id) => ({
    name: PRESETS[id].label,
    value: calculateGrowth(PRESETS[id].scenario).contributionAfterAcquisitionCost,
  }));
  cases.push({
    name: "Current",
    value: calculateGrowth(scenario).contributionAfterAcquisitionCost,
  });
  return (
    <BarChart data={cases}>
      <CartesianGrid stroke={grid} vertical={false} />
      <XAxis dataKey="name" tick={axis} />
      <YAxis tick={axis} tickFormatter={(value) => `${Math.round(Number(value) / 100000)}L`} width={48} />
      <Tooltip contentStyle={tipStyle()} formatter={(value) => formatINR(Number(value))} />
      <Bar dataKey="value" name="Contribution after acquisition" radius={[6, 6, 0, 0]}>
        {cases.map((item) => (
          <Cell key={item.name} fill={item.value < 0 ? "#EB0052" : item.name === "Current" ? "#E9BC70" : "#6F41D7"} />
        ))}
      </Bar>
    </BarChart>
  );
}

function Bridge({ scenario, output }: { scenario: GrowthScenario; output: GrowthOutput }) {
  const outside = output.grossBookingValue90d - output.contributionBeforeAcquisitionCost;
  const afterSpend = output.contributionBeforeAcquisitionCost - scenario.marketingSpendINR;
  const rows = [
    row("Gross bookings", 0, output.grossBookingValue90d, "#F8FAFC"),
    row("Outside contribution", output.contributionBeforeAcquisitionCost, outside, "#415863"),
    row("Contribution before", 0, output.contributionBeforeAcquisitionCost, "#0079CA"),
    row("Marketing spend", Math.min(afterSpend, output.contributionBeforeAcquisitionCost), scenario.marketingSpendINR, "#EB0052"),
    row("Partner fees", output.contributionAfterAcquisitionCost, output.partnerAcquisitionFees, "#6F41D7"),
    row("Contribution after", 0, output.contributionAfterAcquisitionCost, output.contributionAfterAcquisitionCost < 0 ? "#EB0052" : "#E9BC70"),
  ];
  return (
    <BarChart data={rows}>
      <CartesianGrid stroke={grid} vertical={false} />
      <XAxis dataKey="name" tick={{ ...axis, fontSize: 12 }} interval={0} />
      <YAxis tick={axis} tickFormatter={(value) => `${Math.round(Number(value) / 100000)}L`} width={48} />
      <Tooltip contentStyle={tipStyle()} formatter={(value, name) => (name === "offset" ? [null, null] : formatINR(Number(value)))} />
      <Bar dataKey="offset" stackId="a" fill="transparent" />
      <Bar dataKey="amount" stackId="a" radius={[4, 4, 0, 0]}>
        {rows.map((item) => (
          <Cell key={item.name} fill={item.fill} />
        ))}
      </Bar>
    </BarChart>
  );
}

function row(name: string, offset: number, amount: number, fill: string) {
  return { name, offset: Math.max(0, offset), amount: Math.max(0, amount), fill };
}
