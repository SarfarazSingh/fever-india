import { useState } from "react";
import { PARTNERS } from "../data/partners";
import { useGrowth } from "../app/state/GrowthScenarioContext";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { DetailFrame, InteractiveCard } from "../components/ui/InteractiveCard";
import type { PartnerChannel } from "../types";
import hotelsArt from "../assets/art/hotels.jpg";
import banksArt from "../assets/art/banks.jpg";
import corporatesArt from "../assets/art/corporates.jpg";
import occasionsArt from "../assets/art/occasions.jpg";

const ART: Record<PartnerChannel["id"], string> = {
  hotels: hotelsArt,
  banks: banksArt,
  corporates: corporatesArt,
  occasions: occasionsArt,
};

export function Scene07Partnerships() {
  const { applyChannel } = useGrowth();
  const [open, setOpen] = useState<PartnerChannel["id"] | null>(null);
  const channel = PARTNERS.find((item) => item.id === open);

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">07 — Business development</p>
      <h2 className="mt-2 max-w-4xl font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">
        Partners should create distribution, not just provide venues.
      </h2>
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="grid h-full min-h-0 gap-3 md:grid-cols-4" role="tablist" aria-label="Partner types">
          {PARTNERS.map((item) => (
            <InteractiveCard
              key={item.id}
              eyebrow={item.number}
              title={item.title}
              line={item.summary}
              image={ART[item.id]}
              mark={item.id}
              action="Open channel"
              onClick={() => {
                setOpen(item.id);
                applyChannel(item.id);
              }}
            />
          ))}
        </div>
        {channel && (
          <DetailFrame eyebrow={channel.number} title={channel.title} image={ART[channel.id]} onClose={() => setOpen(null)}>
            <ul className="grid gap-2 text-[18px] sm:grid-cols-2">
              {channel.points.map((point) => (
                <li key={point}>· {point}</li>
              ))}
            </ul>
            <ul className="mt-5 space-y-2 text-[17px] leading-snug">
              <li>· Fever: {channel.valueForFever}</li>
              <li>· Partner: {channel.valueForPartner}</li>
              <li>· Pilot: {channel.pilot}</li>
            </ul>
            <p className="mt-4 text-[14px] text-soft">Illustrative. No agreement is claimed.</p>
          </DetailFrame>
        )}
      </div>
    </SceneContainer>
  );
}
