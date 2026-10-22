import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { PARTNERS } from "../../data/partners";
import { BASE_SCENARIO, INITIAL_SCENARIO, PRESETS, type PresetId } from "../../data/scenarios";
import { calculateGrowth } from "../../lib/financialModel";
import type { GrowthOutput, GrowthScenario, PartnerChannelId } from "../../types";

type GrowthContextValue = {
  scenario: GrowthScenario;
  output: GrowthOutput;
  update: (partial: Partial<GrowthScenario>) => void;
  reset: () => void;
  applyPreset: (id: PresetId) => void;
  applyChannel: (id: Exclude<PartnerChannelId, "blended" | "custom">) => void;
};

const GrowthContext = createContext<GrowthContextValue | null>(null);

export function GrowthScenarioProvider({ children }: { children: ReactNode }) {
  const [scenario, setScenario] = useState<GrowthScenario>(INITIAL_SCENARIO);
  const output = useMemo(() => calculateGrowth(scenario), [scenario]);

  const value = useMemo<GrowthContextValue>(
    () => ({
      scenario,
      output,
      update: (partial) => setScenario((current) => ({ ...current, ...partial })),
      reset: () => setScenario({ ...BASE_SCENARIO }),
      applyPreset: (id) => setScenario({ ...PRESETS[id].scenario }),
      applyChannel: (id) => {
        const channel = PARTNERS.find((item) => item.id === id);
        if (!channel) return;
        setScenario((current) => ({
          ...current,
          partnerChannel: id,
          partnerLeads: channel.leads,
          partnerConversionRate: channel.conversion,
          partnerFeePerBookingINR: channel.fee,
        }));
      },
    }),
    [scenario, output],
  );

  return <GrowthContext.Provider value={value}>{children}</GrowthContext.Provider>;
}

export function useGrowth() {
  const value = useContext(GrowthContext);
  if (!value) throw new Error("useGrowth must be used within GrowthScenarioProvider");
  return value;
}
