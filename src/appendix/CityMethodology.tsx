import { useCityModel } from "../app/state/CityModelContext";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { WeightSlider } from "../components/ui/WeightSlider";
import { FACTOR_KEYS, FACTOR_LABELS, riskAdjustedScore, unverifiedDiscount } from "../lib/cityScoring";

export function CityMethodology() {
  const { weights, cities, setWeight, setScore, scoreOf, reset } = useCityModel();
  return (
    <SceneContainer scroll>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">13 — Appendix</p>
      <h2 className="mt-2 font-display text-[clamp(36px,4vw,60px)] leading-none font-medium">City scoring methodology</h2>
      <p className="mt-3 max-w-3xl text-[18px] leading-snug">
        weighted score = 0.25 demand + 0.20 venue + 0.20 audience + 0.20 fit + 0.15 partners, until you edit the weights. All factors are 0–100 sample inputs. Weights are renormalised to 100%.
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-5">
        {FACTOR_KEYS.map((key) => (
          <WeightSlider key={key} label={FACTOR_LABELS[key]} min={0} max={100} step={1} value={weights[key]} display={`${weights[key]}%`} onChange={(value) => setWeight(key, value)} />
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2 text-[15px]" onClick={reset}>Reset factors</button>
      </div>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[880px] text-left text-[15px]">
          <thead className="text-soft">
            <tr>
              <th className="py-2">City</th>
              {FACTOR_KEYS.map((key) => <th key={key}>{FACTOR_LABELS[key].split(" ")[0]}</th>)}
              <th>Weighted</th>
              <th>Discount</th>
              <th>Risk-adjusted</th>
            </tr>
          </thead>
          <tbody>
            {cities.map((city) => (
              <tr key={city.id} className="border-t border-white/10">
                <td className="py-2">
                  {city.name}
                  <span className="ml-2 text-[12px] text-soft capitalize">{city.classification}</span>
                </td>
                {FACTOR_KEYS.map((key) => (
                  <td key={key}>
                    <input
                      className="focus-ring w-16 rounded-md border border-white/15 bg-transparent px-2 py-1"
                      type="number"
                      min={0}
                      max={100}
                      aria-label={`${city.name} ${key}`}
                      value={city.scores[key]}
                      onChange={(event) => setScore(city.id, key, Number(event.target.value))}
                    />
                  </td>
                ))}
                <td className="tabular">{scoreOf(city).toFixed(1)}</td>
                <td className="tabular">−{unverifiedDiscount(city.classification)}</td>
                <td className="tabular">{riskAdjustedScore(city, weights).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Note title="Research gaps" body="Search demand, venue cost, achievable price, operating feasibility, and verified current presence. None of the factor cells above is a measured market statistic." />
        <Note title="Potential data sources" body="Fever’s own search and booking cohorts, venue pipeline from operations, partner CRM, and publicly announced programming used only as context." />
        <Note title="Risk-adjusted score" body="A fixed unverified-input discount: 6 points for documented examples, 10 for a scale-up assessment, 12 for candidates. It is a presentation device, not a statistical interval." />
      </div>
    </SceneContainer>
  );
}

function Note({ title, body }: { title: string; body: string }) {
  return (
    <article className="rounded-2xl border border-white/10 p-4">
      <h3 className="font-display text-[20px]">{title}</h3>
      <p className="mt-2 text-[15px] leading-snug text-soft">{body}</p>
    </article>
  );
}
