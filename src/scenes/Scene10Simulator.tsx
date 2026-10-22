import { SceneContainer } from "../components/presentation/SceneContainer";
import { GrowthSimulator } from "../components/simulations/GrowthSimulator";

export function Scene10Simulator() {
  return (
    <SceneContainer width="max-w-[1600px]">
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">10 — The decision metrics</p>
      <h2 className="mt-1 font-display text-[clamp(32px,3.6vw,48px)] leading-none font-medium">These are the numbers the case has to survive.</h2>
      <div className="mt-3 min-h-0 flex-1">
        <GrowthSimulator />
      </div>
    </SceneContainer>
  );
}
