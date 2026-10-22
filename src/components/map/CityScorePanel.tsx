import { LayoutGroup, motion } from "framer-motion";
import { useCityModel } from "../../app/state/CityModelContext";
import { FACTOR_KEYS, FACTOR_LABELS } from "../../lib/cityScoring";
import { WeightSlider } from "../ui/WeightSlider";
import type { City } from "../../types";

export function CityScorePanel({
  selectedId,
  onSelect,
  onRecommend,
}: {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRecommend: () => void;
}) {
  const { weights, rankedPilots, cities, setWeight, scoreOf } = useCityModel();
  const selected = cities.find((city) => city.id === selectedId) ?? null;

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="grid gap-3">
        {FACTOR_KEYS.map((key) => (
          <WeightSlider
            key={key}
            label={FACTOR_LABELS[key]}
            min={0}
            max={100}
            step={1}
            value={weights[key]}
            display={`${weights[key]}%`}
            onChange={(value) => setWeight(key, value)}
          />
        ))}
      </div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[14px] text-soft">Weights stay at 100%. Scores are sample inputs.</p>
        <button
          type="button"
          className="focus-ring shrink-0 rounded-full bg-fever px-4 py-2 text-[15px] text-white hover:bg-fever-hover"
          onClick={onRecommend}
        >
          Recommend next pilot
        </button>
      </div>
      <LayoutGroup>
        <ol className="space-y-2">
          {rankedPilots.map((city, index) => (
            <motion.li layout key={city.id}>
              <CityRow
                city={city}
                rank={index + 1}
                score={scoreOf(city)}
                selected={city.id === selectedId}
                onSelect={onSelect}
              />
            </motion.li>
          ))}
        </ol>
      </LayoutGroup>
      {selected && <CityDetail city={selected} score={scoreOf(selected)} />}
    </div>
  );
}

function CityRow({
  city,
  rank,
  score,
  selected,
  onSelect,
}: {
  city: City;
  rank: number;
  score: number;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(city.id)}
      className={`focus-ring flex w-full items-center gap-3 rounded-2xl border px-3 py-2 text-left ${selected ? "border-gold/70 bg-white/5" : "border-white/10 hover:-translate-y-0.5"}`}
    >
      <span className="w-6 text-[14px] text-soft">{rank}</span>
      <span className="flex-1">
        <span className="block font-display text-[16px]">{city.name}</span>
        <span className="text-[13px] text-soft capitalize">{city.classification}</span>
      </span>
      <span className="tabular text-[18px] text-gold">{score.toFixed(1)}</span>
    </button>
  );
}

export function CityDetail({ city, score }: { city: City; score: number }) {
  const rows = [
    ["Why it might matter", city.why],
    ["What is missing", city.missing],
    ["Format hypothesis", city.formatHypothesis],
    ["Partner category", city.partnerCategory],
    ["Venue", city.venue],
    ["First launch KPI", city.launchKpi],
    ["Key risk", city.risk],
    ["Go / no-go", city.gate],
  ];
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-[13px] tracking-[0.14em] text-gold uppercase">{city.classification}</p>
          <h3 className="font-display text-[26px] leading-none">{city.name}</h3>
        </div>
        <p className="tabular text-[28px] text-light">{score.toFixed(1)}</p>
      </div>
      <dl className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[13px] text-gold">{label}</dt>
            <dd className="text-[15px] leading-snug text-light/90">{value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
