import { useState } from "react";
import { useCityModel } from "../app/state/CityModelContext";
import { CityScorePanel } from "../components/map/CityScorePanel";
import { IndiaGrowthMap } from "../components/map/IndiaGrowthMap";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { SourceFootnote } from "../components/ui/SourceFootnote";

export function Scene06Expansion() {
  const { cities, rankedPilots, reset } = useCityModel();
  const [selected, setSelected] = useState<string>("lucknow");
  const [recommendation, setRecommendation] = useState<string | null>(null);

  return (
    <SceneContainer width="max-w-[1600px]">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[14px] tracking-[0.16em] text-gold uppercase">06 — Expansion decision engine</p>
          <h2 className="mt-2 font-display text-[clamp(38px,4.4vw,64px)] leading-none font-medium">Where should Fever grow next?</h2>
          <p className="mt-2 text-[18px] text-soft">Expansion should be scored, not guessed.</p>
        </div>
        <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2 text-[15px]" onClick={() => { reset(); setRecommendation(null); }}>
          Reset scorecard
        </button>
      </div>
      {recommendation && <p className="mb-3 rounded-2xl border border-gold/40 bg-gold/10 px-4 py-3 text-[16px]">{recommendation}</p>}
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1.25fr_0.85fr]">
        <div className="h-[420px] min-h-0 lg:h-full">
          <IndiaGrowthMap cities={cities} selectedId={selected} onSelect={setSelected} />
        </div>
        <div className="scene-scroll min-h-0 lg:overflow-y-auto lg:pr-1">
          <CityScorePanel
            selectedId={selected}
            onSelect={setSelected}
            onRecommend={() => {
              const top = rankedPilots[0];
              if (!top) return;
              setSelected(top.id);
              const scale = top.classification === "scale-up" ? " Treat it as a scale-up assessment, not an assumed new market." : "";
              setRecommendation(`Illustrative recommendation based on editable inputs: ${top.name}.${scale}`);
            }}
          />
        </div>
      </div>
      <div className="mt-3">
        <SourceFootnote>
          Blue pins are public programming examples. Amber pins are candidates. Hyderabad is a scale-up assessment. Scores say “research required.” Outline includes the full northern boundary.
        </SourceFootnote>
      </div>
    </SceneContainer>
  );
}
