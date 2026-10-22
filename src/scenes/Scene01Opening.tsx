import { CinematicHero } from "../components/motion/CinematicHero";
import { IndiaSilhouette } from "../components/map/IndiaGrowthMap";
import { usePresentation } from "../app/state/PresentationContext";

export function Scene01Opening() {
  const { go } = usePresentation();

  return (
    <CinematicHero>
      <div className="relative flex h-full items-end px-6 pt-24 pb-28 md:px-16 lg:px-20">
        <div className="pointer-events-none absolute top-16 right-0 hidden h-[min(72vh,680px)] w-[min(42vw,520px)] lg:block" aria-hidden="true">
          <IndiaSilhouette />
        </div>
        <div className="relative z-10 w-full max-w-[920px]">
          <p className="mb-6 text-[15px] tracking-[0.18em] text-gold uppercase">
            Use arrow keys to explore
          </p>
          <h1 className="font-display text-[clamp(36px,7.2vw,108px)] leading-[0.88] font-medium">
            <span className="block">INDIA,</span>
            <span className="block">REIMAGINED.</span>
          </h1>
          <p className="mt-6 max-w-xl font-serif text-[clamp(26px,3vw,40px)] leading-tight text-glow">
            From memorable experiences
            <br />
            to measurable growth.
          </p>
          <button
            type="button"
            className="focus-ring mt-8 rounded-full bg-fever px-6 py-3 text-[16px] text-white hover:bg-fever-hover"
            onClick={() => go(1)}
          >
            Explore the Growth Engine →
          </button>
          <p className="mt-8 text-[15px] leading-relaxed text-soft">
            An independent strategy proposal for Fever India
            <br />
            Sarfaraz Singh Wahad · October 2026
          </p>
        </div>
        </div>
    </CinematicHero>
  );
}
