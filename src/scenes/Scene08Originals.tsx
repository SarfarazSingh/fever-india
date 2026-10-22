import { useState } from "react";
import { EXPERIENCES } from "../data/experienceConcepts";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { DetailFrame, InteractiveCard } from "../components/ui/InteractiveCard";
import bollywoodArt from "../assets/art/bollywood.jpg";
import sufiArt from "../assets/art/sufi.jpg";
import ghazalArt from "../assets/art/ghazal.jpg";
import fusionArt from "../assets/art/fusion.jpg";
import regionalArt from "../assets/art/regional.jpg";

const ART: Record<string, string> = {
  bollywood: bollywoodArt,
  sufi: sufiArt,
  ghazal: ghazalArt,
  fusion: fusionArt,
  regional: regionalArt,
};

export function Scene08Originals() {
  const [selected, setSelected] = useState<string | null>(null);
  const concept = EXPERIENCES.find((item) => item.id === selected);

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">08 — Localised product strategy</p>
      <h2 className="mt-2 font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">Global production quality. Local cultural relevance.</h2>
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="grid h-full min-h-0 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {EXPERIENCES.map((item) => (
            <InteractiveCard
              key={item.id}
              eyebrow={item.eyebrow}
              title={item.title}
              line={item.relation}
              image={ART[item.id]}
              mark={item.id === "fusion" ? "convert" : item.id === "regional" ? "expand" : item.id === "ghazal" ? "return" : item.id === "sufi" ? "occasions" : "discover"}
              action="Open concept"
              onClick={() => setSelected(item.id)}
            />
          ))}
        </div>
        {concept && (
          <DetailFrame eyebrow={concept.relation} title={concept.title} image={ART[concept.id]} onClose={() => setSelected(null)}>
            <ul className="space-y-2 text-[18px] leading-snug">
              <li>· {concept.summary}</li>
              <li>· Audience: {concept.audience}</li>
              <li>· City: {concept.city}</li>
              <li>· Pilot: {concept.scale}</li>
              <li>· Gate: {concept.gate}</li>
            </ul>
          </DetailFrame>
        )}
      </div>
    </SceneContainer>
  );
}
