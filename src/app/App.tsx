import { CityModelProvider } from "./state/CityModelContext";
import { GrowthScenarioProvider } from "./state/GrowthScenarioContext";
import { PresentationProvider } from "./state/PresentationContext";
import { PresentationShell } from "../components/presentation/PresentationShell";

export function App() {
  return (
    <PresentationProvider>
      <GrowthScenarioProvider>
        <CityModelProvider>
          <PresentationShell />
        </CityModelProvider>
      </GrowthScenarioProvider>
    </PresentationProvider>
  );
}
