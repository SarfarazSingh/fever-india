import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { CITIES } from "../../data/cities";
import {
  DEFAULT_WEIGHTS,
  rankCities,
  redistributeWeight,
  weightedScore,
} from "../../lib/cityScoring";
import type { City, CityFactorScore, FactorKey, FactorWeights } from "../../types";

type CityModelValue = {
  weights: FactorWeights;
  cities: City[];
  rankedPilots: City[];
  setWeight: (key: FactorKey, value: number) => void;
  setScore: (cityId: string, key: FactorKey, value: number) => void;
  reset: () => void;
  scoreOf: (city: City) => number;
};

const CityModelContext = createContext<CityModelValue | null>(null);

function initialScores(): Record<string, CityFactorScore> {
  return Object.fromEntries(CITIES.map((city) => [city.id, { ...city.scores }]));
}

export function CityModelProvider({ children }: { children: ReactNode }) {
  const [weights, setWeights] = useState<FactorWeights>(DEFAULT_WEIGHTS);
  const [scores, setScores] = useState(initialScores);

  const cities = useMemo(
    () => CITIES.map((city) => ({ ...city, scores: scores[city.id] ?? city.scores })),
    [scores],
  );
  const rankedPilots = useMemo(
    () => rankCities(cities, weights, (city) => city.classification !== "baseline"),
    [cities, weights],
  );

  const value = useMemo<CityModelValue>(
    () => ({
      weights,
      cities,
      rankedPilots,
      setWeight: (key, next) => setWeights((current) => redistributeWeight(current, key, next)),
      setScore: (cityId, key, next) =>
        setScores((current) => ({
          ...current,
          [cityId]: {
            ...current[cityId],
            [key]: Math.min(100, Math.max(0, Math.round(next))),
          },
        })),
      reset: () => {
        setWeights(DEFAULT_WEIGHTS);
        setScores(initialScores());
      },
      scoreOf: (city) => weightedScore(city.scores, weights),
    }),
    [weights, cities, rankedPilots],
  );

  return <CityModelContext.Provider value={value}>{children}</CityModelContext.Provider>;
}

export function useCityModel() {
  const value = useContext(CityModelContext);
  if (!value) throw new Error("useCityModel must be used within CityModelProvider");
  return value;
}
