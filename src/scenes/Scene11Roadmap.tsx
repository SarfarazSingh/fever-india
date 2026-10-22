import { useState } from "react";
import { PHASES } from "../data/roadmap";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { DetailFrame, InteractiveCard } from "../components/ui/InteractiveCard";
import diagnoseArt from "../assets/art/diagnose.jpg";
import experimentArt from "../assets/art/experiment.jpg";
import scaleArt from "../assets/art/scale.jpg";

const ART = {
  diagnose: diagnoseArt,
  experiment: experimentArt,
  decide: scaleArt,
} as const;

export function Scene11Roadmap() {
  const [phase, setPhase] = useState<(typeof PHASES)[number]["id"] | null>(null);
  const current = PHASES.find((item) => item.id === phase);

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">11 — Execution credibility</p>
      <h2 className="mt-2 font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">
        Learn fast. <span className="text-soft">Test rigorously. Scale deliberately.</span>
      </h2>
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="grid h-full min-h-0 gap-3 lg:grid-cols-3">
          {PHASES.map((item) => (
            <InteractiveCard
              key={item.id}
              eyebrow={item.days}
              title={item.name}
              line={item.intent}
              image={ART[item.id as keyof typeof ART]}
              mark={item.id}
              action="Open phase"
              onClick={() => setPhase(item.id)}
            />
          ))}
        </div>
        {current && (
          <DetailFrame eyebrow={current.days} title={current.name} image={ART[current.id as keyof typeof ART]} onClose={() => setPhase(null)}>
            <ul className="grid gap-2 text-[17px] sm:grid-cols-2">
              {current.actions.slice(0, 4).map((action) => (
                <li key={action}>· {action}</li>
              ))}
            </ul>
            <p className="mt-4 text-[16px]"><span className="text-gold">Gate. </span>{current.gate}</p>
          </DetailFrame>
        )}
      </div>
    </SceneContainer>
  );
}
