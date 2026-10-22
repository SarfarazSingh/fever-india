import { useMemo, useState } from "react";
import { EXPERIMENTS, MOCK_SCHEMA, MOCK_SQL } from "../data/experiments";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { sampleSizePerArm } from "../lib/sampleSize";
import { formatNumber, formatPercent } from "../lib/numberFormat";

export function ExperimentFramework() {
  const [selected, setSelected] = useState(EXPERIMENTS[0].id);
  const [baseline, setBaseline] = useState(0.028);
  const [lift, setLift] = useState(0.15);
  const experiment = EXPERIMENTS.find((item) => item.id === selected) ?? EXPERIMENTS[0];
  const variant = baseline * (1 + lift);
  const sample = useMemo(() => sampleSizePerArm(baseline, variant), [baseline, variant]);

  return (
    <SceneContainer scroll>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">14 — Appendix</p>
      <h2 className="mt-2 font-display text-[clamp(36px,4vw,60px)] leading-none font-medium">Experimentation framework</h2>
      <p className="mt-3 max-w-3xl text-[18px]">Randomise, keep cohorts comparable, and decide on incrementality. A pre/post difference is not proof.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXPERIMENTS.map((item) => (
          <button key={item.id} type="button" className={`focus-ring rounded-full px-3 py-2 text-[15px] ${item.id === selected ? "bg-fever" : "border border-white/15"}`} onClick={() => setSelected(item.id)}>
            {item.code}. {item.name}
          </button>
        ))}
      </div>
      <article className="mt-4 grid gap-3 rounded-3xl border border-white/10 p-5 md:grid-cols-2">
        <Field label="Hypothesis" value={experiment.hypothesis} />
        <Field label="Target segment" value={experiment.segment} />
        <Field label="Treatment" value={experiment.treatment} />
        <Field label="Control" value={experiment.control} />
        <Field label="Primary metric" value={experiment.primary} />
        <Field label="Guardrails" value={experiment.guardrails.join(" · ")} />
        <Field label="Sample size" value={experiment.sampleNote} />
        <Field label="Owner" value={experiment.owner} />
        <Field label="Duration" value={experiment.duration} />
        <Field label="Decision rule" value={experiment.decision} />
      </article>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-3xl border border-white/10 p-4">
          <h3 className="font-display text-[24px]">Planning calculator</h3>
          <p className="mt-1 text-[14px] text-soft">Worked example only. The 2.8% starting point is the fictional simulator baseline, not Fever’s conversion.</p>
          <label className="mt-3 block text-[15px]">Baseline conversion
            <input className="mt-1 w-full" type="range" min={0.01} max={0.08} step={0.001} value={baseline} onChange={(event) => setBaseline(Number(event.target.value))} />
          </label>
          <label className="mt-2 block text-[15px]">Relative lift to detect
            <input className="mt-1 w-full" type="range" min={0.05} max={0.3} step={0.01} value={lift} onChange={(event) => setLift(Number(event.target.value))} />
          </label>
          <p className="mt-3 text-[16px]">
            {formatPercent(baseline)} → {formatPercent(variant)}. About {sample ? formatNumber(sample) : "—"} people per arm at 80% power and 5% significance, two-sided.
          </p>
        </div>
        <div className="rounded-3xl border border-white/10 p-4">
          <h3 className="font-display text-[24px]">Mock events schema</h3>
          <pre className="mt-3 overflow-x-auto text-[14px] leading-relaxed text-soft">{MOCK_SCHEMA}</pre>
          <pre className="mt-3 overflow-x-auto text-[14px] leading-relaxed text-link">{MOCK_SQL}</pre>
        </div>
      </div>
    </SceneContainer>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[13px] text-gold">{label}</p>
      <p className="text-[16px] leading-snug">{value}</p>
    </div>
  );
}
