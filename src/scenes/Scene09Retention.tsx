import { useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useGrowth } from "../app/state/GrowthScenarioContext";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { WeightSlider } from "../components/ui/WeightSlider";
import { formatNumber, formatPercent } from "../lib/numberFormat";

const STAGES = [
  ["Discovery", "The first time Fever becomes relevant."],
  ["First booking", "Acquisition has a customer. Retention does not, yet."],
  ["Experience", "The night has to earn the second invitation."],
  ["Post-show engagement", "A consented, specific follow-up. Not a generic blast."],
  ["Personalised recommendation", "The next format should feel like a continuation."],
  ["Second booking", "This is the metric. Intent is only a clue."],
  ["Referral", "A friend is a hypothesis, counted only when they book."],
];

const LEVERS = [
  ["Post-event recommendations", "Suggest another experience aligned to the show they just attended."],
  ["Bundles / membership concepts", "Test whether a relevant bundle improves frequency or contribution. This is not a claim that an Indian membership exists."],
  ["Social referrals", "Encourage sharing with friends and family, then measure booked customers rather than shares."],
];

export function Scene09Retention() {
  const { scenario, output, update } = useGrowth();
  const [stage, setStage] = useState(0);
  const [intervention, setIntervention] = useState(true);
  const repeat = scenario.repeatBookingProbability90d;
  const referrals = output.firstTimeCustomers * repeat * 0.2;
  const data = [0, 30, 60, 90].map((day, index) => {
    const shape = [0, 0.45, 0.75, 1][index];
    return {
      day: `Day ${day}`,
      intervention: repeat * 100 * shape,
      baseline: 0.08 * 100 * shape,
    };
  });

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">09 — Customer lifecycle</p>
      <h2 className="mt-2 font-display text-[clamp(38px,4.6vw,68px)] leading-[0.95] font-medium">The first booking is the beginning.</h2>
      <p className="mt-2 text-[20px] text-soft">Intent is encouraging. Actual repeat behaviour is the metric.</p>
      <div className="mt-3 grid min-h-0 flex-1 gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <ol className="space-y-2">
            {STAGES.map(([title, body], index) => (
              <li key={title}>
                <button type="button" onClick={() => setStage(index)} className={`focus-ring w-full rounded-2xl border px-3 py-2 text-left ${stage === index ? "border-gold bg-white/5" : "border-white/10"}`}>
                  <span className="text-[13px] text-soft">0{index + 1}</span>
                  <span className="ml-2 font-display text-[18px]">{title}</span>
                  {stage === index && <span className="mt-1 block text-[15px] text-soft">{body}</span>}
                </button>
              </li>
            ))}
          </ol>
        </div>
        <div className="space-y-3">
          <div className="grid gap-2 md:grid-cols-3">
            {LEVERS.map(([title, body]) => (
              <article key={title} className="rounded-2xl border border-white/10 p-3">
                <h3 className="font-display text-[18px] leading-tight">{title}</h3>
                <p className="mt-2 text-[14px] leading-snug text-soft">{body}</p>
              </article>
            ))}
          </div>
          <div className="rounded-3xl border border-white/10 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-display text-[24px]">90-day repeat booking assumption</h3>
              <div className="flex rounded-full border border-white/15 p-1 text-[14px]">
                <button type="button" className={`rounded-full px-3 py-1 ${intervention ? "" : "bg-white/10"}`} onClick={() => setIntervention(false)}>No lifecycle intervention</button>
                <button type="button" className={`rounded-full px-3 py-1 ${intervention ? "bg-fever" : ""}`} onClick={() => setIntervention(true)}>Proposed lifecycle intervention</button>
              </div>
            </div>
            <WeightSlider label="Illustrative 90-day repeat probability" min={0} max={0.4} step={0.01} value={repeat} display={formatPercent(repeat, 0)} onChange={(value) => update({ repeatBookingProbability90d: value })} />
            <div className="mt-2 h-24">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                  <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: "#A7B2BA", fontSize: 14 }} />
                  <YAxis tick={{ fill: "#A7B2BA", fontSize: 14 }} unit="%" width={48} />
                  <Tooltip contentStyle={{ background: "#031419", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 12 }} />
                  <Area type="monotone" dataKey="baseline" name="No intervention (hypothetical 8%)" stroke="#A7B2BA" fill="#A7B2BA" fillOpacity={0.15} />
                  {intervention && <Area type="monotone" dataKey="intervention" name="Proposed intervention (slider)" stroke="#0079CA" fill="#0079CA" fillOpacity={0.25} />}
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-[15px] md:grid-cols-5">
              <Mini label="30-day shape" value={formatPercent(repeat * 0.45, 0)} />
              <Mini label="60-day shape" value={formatPercent(repeat * 0.75, 0)} />
              <Mini label="90-day" value={formatPercent(repeat, 0)} />
              <Mini label="Time to second booking" value="Illustrative curve" />
              <Mini label="Referral customers" value={formatNumber(referrals)} />
            </div>
            <p className="mt-2 text-[13px] text-soft">Both lines are hypothetical. The grey line is a fixed 8% illustration. Referrals are outside the contribution formula.</p>
          </div>
        </div>
      </div>
    </SceneContainer>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/5 p-2">
      <p className="text-[12px] text-soft">{label}</p>
      <p className="tabular">{value}</p>
    </div>
  );
}
