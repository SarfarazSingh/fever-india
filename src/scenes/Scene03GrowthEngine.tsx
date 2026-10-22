import { useState } from "react";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { DetailFrame, InteractiveCard } from "../components/ui/InteractiveCard";
import discoverArt from "../assets/art/discover.jpg";
import convertArt from "../assets/art/convert.jpg";
import returnArt from "../assets/art/return.jpg";
import expandArt from "../assets/art/expand.jpg";

const NODES = [
  {
    id: "discover",
    title: "Discover",
    line: "Reach the right audience",
    points: ["Language and creative localization", "Creator-led acquisition", "City-specific discovery"],
    metric: "Qualified traffic and cost of a first session",
    experiment: "Hindi-first versus current English discovery in Delhi NCR",
    image: discoverArt,
    mark: "discover",
  },
  {
    id: "convert",
    title: "Convert",
    line: "Turn interest into bookings",
    points: ["Relevant landing pages", "Lower funnel friction", "Partner-assisted distribution"],
    metric: "First-booking conversion and checkout completion",
    experiment: "Landing relevance, then one partner distribution test",
    image: convertArt,
    mark: "convert",
  },
  {
    id: "return",
    title: "Return",
    line: "Turn one night into another",
    points: ["Post-show recommendations", "CRM and lifecycle journeys", "Referrals and relevant bundles"],
    metric: "90-day second booking, not survey intent",
    experiment: "Personalised versus generic post-event recommendation",
    image: returnArt,
    mark: "return",
  },
  {
    id: "expand",
    title: "Expand",
    line: "Replicate what works",
    points: ["City prioritisation", "Format validation", "Local partner ecosystems"],
    metric: "Contribution after a controlled pilot, not a launch press release",
    experiment: "Score the next city, then validate the top factors",
    image: expandArt,
    mark: "expand",
  },
] as const;

export function Scene03GrowthEngine() {
  const [active, setActive] = useState<(typeof NODES)[number]["id"] | "measure" | null>(null);
  const node = NODES.find((item) => item.id === active);

  return (
    <SceneContainer>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">03 — The operating model</p>
      <h2 className="mt-2 font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">
        Four connected levers.
        <span className="text-soft"> One repeatable growth system.</span>
      </h2>
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="grid h-full min-h-0 gap-3 md:grid-cols-4">
          {NODES.map((item, index) => (
            <InteractiveCard
              key={item.id}
              eyebrow={`0${index + 1}`}
              title={item.title}
              line={item.line}
              image={item.image}
              mark={item.mark}
              onClick={() => setActive(item.id)}
            />
          ))}
        </div>
        {active && (
          <DetailFrame
            title={node ? node.title : "Measure"}
            eyebrow={node ? node.line : "City × format × cohort × channel"}
            image={node?.image}
            onClose={() => setActive(null)}
          >
            <ul className="space-y-2 text-[18px] leading-snug">
              {node ? (
                <>
                  {node.points.map((point) => <li key={point}>· {point}</li>)}
                  <li>· Metric: {node.metric}</li>
                  <li>· Experiment: {node.experiment}</li>
                </>
              ) : (
                <>
                  <li>· City, format, cohort, and channel — the same cut every time</li>
                  <li>· A national average hides the decision</li>
                  <li>· The economics of those cuts sit on the metrics slide</li>
                </>
              )}
            </ul>
          </DetailFrame>
        )}
      </div>
    </SceneContainer>
  );
}
