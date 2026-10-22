import { useState } from "react";
import { CinematicHero } from "../components/motion/CinematicHero";
import { DetailFrame, InteractiveCard } from "../components/ui/InteractiveCard";
import builderArt from "../assets/art/builder.jpg";
import dataArt from "../assets/art/data.jpg";
import navyArt from "../assets/art/navy.jpg";

const CREDENTIALS = [
  {
    id: "builder",
    title: "Builder",
    line: "Weave and AnterVid. Consumer and technology ventures.",
    detail:
      "Weave: a Madrid community-experiences venture. Candidate-reported outcomes: 500+ users and approximately €7,000 revenue. AnterVid: a co-founded infrastructure technology venture that won a first Indian Railways contract.",
    image: builderArt,
    mark: "builder",
  },
  {
    id: "data",
    title: "Data & delivery",
    line: "PwC consulting, with practical SQL and Python.",
    detail: "PwC: enterprise technology and data/AI consulting.",
    image: dataArt,
    mark: "data",
  },
  {
    id: "leadership",
    title: "Leadership",
    line: "11 years of operational leadership in the Indian Navy.",
    detail: "Technical leadership, complex operations, and multidisciplinary stakeholder management.",
    image: navyArt,
    mark: "navy",
  },
];

export function Scene12Closing() {
  const [open, setOpen] = useState<string | null>(null);
  const selected = CREDENTIALS.find((item) => item.id === open);

  return (
    <CinematicHero>
      <div className="relative mx-auto flex h-full max-w-6xl flex-col px-6 pt-14 pb-16 md:px-10">
        <p className="text-[14px] tracking-[0.18em] text-gold uppercase">12 — Close</p>
        <h2 className="mt-1 font-display text-[clamp(30px,3.8vw,54px)] leading-[0.92] font-medium">
          Extraordinary experiences.
          <span className="block">Repeatable growth.</span>
        </h2>
        <p className="mt-2 max-w-2xl font-serif text-[clamp(17px,1.8vw,24px)] leading-snug text-glow">
          Help Fever turn local insight, trusted partners, and data-driven decisions into scalable growth across India.
        </p>
        <div className="relative mt-5 min-h-0 flex-1">
          <div className="grid h-full min-h-0 gap-3 md:grid-cols-3">
            {CREDENTIALS.map((item) => (
              <InteractiveCard
                key={item.id}
                eyebrow={item.title}
                title={item.title}
                line={item.line}
                image={item.image}
                mark={item.mark}
                action="Open note"
                onClick={() => setOpen(item.id)}
              />
            ))}
          </div>
          {selected && (
            <DetailFrame eyebrow={selected.title} title={selected.title} image={selected.image} onClose={() => setOpen(null)}>
              <p className="text-[18px] leading-snug">{selected.detail}</p>
              <p className="mt-4 text-[14px] text-soft">Candidate-reported. Verify titles, dates, and metrics before final use.</p>
            </DetailFrame>
          )}
        </div>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <p className="max-w-xl font-serif text-[clamp(22px,2.4vw,34px)] leading-tight">Where do you see the largest untapped growth opportunity in India today?</p>
          <div>
            <p className="font-display text-[20px]">Thank you.</p>
            <p className="text-[15px]">Sarfaraz Singh Wahad</p>
            <a className="text-link underline" href="https://sarfarazsingh.dev" target="_blank" rel="noreferrer">sarfarazsingh.dev</a>
          </div>
        </div>
      </div>
    </CinematicHero>
  );
}
