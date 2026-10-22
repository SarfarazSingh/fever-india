import { useState } from "react";
import { AUDIENCE_SOURCE, DOCUMENTED_CITIES, METRICS } from "../data/evidence";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { AnimatedNumber } from "../components/motion/AnimatedNumber";
import { SourceFootnote } from "../components/ui/SourceFootnote";
import { InteractiveCard } from "../components/ui/InteractiveCard";
import firstArt from "../assets/art/discover.jpg";
import intentArt from "../assets/art/return.jpg";
import programmeArt from "../assets/art/bollywood.jpg";

const ART = {
  "first-time": firstArt,
  intent: intentArt,
  programme: programmeArt,
} as const;

const MARK = {
  "first-time": "first",
  intent: "intent",
  programme: "programme",
} as const;

export function Scene02Opportunity() {
  const [open, setOpen] = useState<string | null>(null);
  const active = METRICS.find((metric) => metric.id === open);

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">02 — Evidence, not assumptions</p>
      <h2 className="mt-2 max-w-4xl font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">
        The experience resonates.
        <span className="block text-soft">The next question is what happens after.</span>
      </h2>
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="grid h-full min-h-0 gap-3 lg:grid-cols-3">
          {METRICS.map((metric) => (
            <InteractiveCard
              key={metric.id}
              eyebrow={metric.id === "intent" ? "Intent, not repeat" : "Published figure"}
              title={`${metric.prefix}${metric.value}${metric.suffix}`}
              line={metric.label}
              image={ART[metric.id]}
              mark={MARK[metric.id]}
              action="Read the figure"
              onClick={() => setOpen((current) => (current === metric.id ? null : metric.id))}
            >
              <span className="sr-only">
                {metric.prefix}
                <AnimatedNumber value={metric.value} format={(value) => Math.round(value).toString()} />
                {metric.suffix}
              </span>
            </InteractiveCard>
          ))}
        </div>
        {active && (
          <div className="detail-frame absolute inset-x-0 bottom-0 z-20 rounded-[28px] border border-gold/40 bg-deep/95 p-5 backdrop-blur-md">
            <div className="flex items-start justify-between gap-4">
              <p className="font-display text-[28px] leading-none">{active.prefix}{active.value}{active.suffix}</p>
              <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2 text-[15px]" onClick={() => setOpen(null)}>
                Back
              </button>
            </div>
            <ul className="mt-3 grid gap-2 text-[16px] leading-snug md:grid-cols-3">
              <li><span className="text-gold">Says. </span>{active.says}</li>
              <li><span className="text-gold">Does not say. </span>{active.doesNot}</li>
              <li><span className="text-gold">Measure next. </span>{active.next}</li>
            </ul>
          </div>
        )}
      </div>
      <p className="mt-3 text-[14px] text-soft">{DOCUMENTED_CITIES.join(" · ")}</p>
      <SourceFootnote>
        {AUDIENCE_SOURCE.publisher}, {AUDIENCE_SOURCE.date}. Public programming examples, not a full footprint.
      </SourceFootnote>
    </SceneContainer>
  );
}
