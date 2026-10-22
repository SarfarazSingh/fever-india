import { useState } from "react";
import { useGrowth } from "../app/state/GrowthScenarioContext";
import { LanguageSwitch } from "../components/phones/LanguageSwitch";
import { PhoneMockup } from "../components/phones/PhoneMockup";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { formatPercent } from "../lib/numberFormat";

const LIFTS = [0, 0.1, 0.15, 0.25];

const COPY = {
  en: {
    hero: "Discover an unforgettable evening in Delhi.",
    support: "A concept for testing relevance, not a live Fever page.",
    card: "Candlelight: An Evening of Sufi Music",
    meta: "Delhi NCR · Example evening",
    cta: "Explore Experiences",
    filters: ["Candlelight", "Sufi Nights", "Live Music", "Experiences for Two"],
  },
  hi: {
    hero: "दिल्ली की शाम, सुरों के नाम",
    support: "अपनों के साथ संगीत से सजी एक यादगार शाम।",
    card: "कैंडललाइट: सूफ़ी संगीत की एक शाम",
    meta: "दिल्ली एनसीआर · उदाहरण",
    cta: "शो देखें",
    filters: ["कैंडललाइट", "सूफ़ी नाइट्स", "लाइव संगीत", "दो के लिए"],
  },
};

export function Scene04Localization() {
  const { scenario, update } = useGrowth();
  const [language, setLanguage] = useState<"en" | "hi">("en");
  const [filter, setFilter] = useState(0);
  const [tab, setTab] = useState<"discover" | "saved" | "bookings">("discover");
  const copy = COPY[language];

  return (
    <SceneContainer>
      <div className="grid items-start gap-8 lg:grid-cols-[0.95fr_0.8fr]">
        <div>
          <p className="text-[14px] tracking-[0.16em] text-gold uppercase">04 — Live product prototype</p>
          <h2 className="mt-3 font-display text-[clamp(40px,4.6vw,68px)] leading-[0.95] font-medium">
            Localization is more than translation.
          </h2>
          <p className="mt-3 max-w-xl text-[20px] text-soft">Test relevance, cultural familiarity, and booking conversion.</p>
          <p className="mt-5 max-w-xl text-[17px] leading-relaxed">
            The proposal is not “make India Hindi.” It is a Delhi NCR test of whether Hindi-first creative helps a specific audience book the first time. Other cities, and other languages, would be separate questions.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <LanguageSwitch language={language} onChange={setLanguage} />
            <span className="text-[14px] text-soft">Hindi is left to right. The interface does not flip.</span>
          </div>
          <p className="mt-6 text-[14px] tracking-[0.14em] text-soft uppercase">Localization hypothesis</p>
          <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Illustrative conversion lift">
            {LIFTS.map((lift) => (
              <button
                key={lift}
                type="button"
                aria-pressed={Math.abs(scenario.localizationRelativeUplift - lift) < 0.001}
                className={`focus-ring rounded-full px-3 py-2 text-[15px] ${Math.abs(scenario.localizationRelativeUplift - lift) < 0.001 ? "bg-fever text-white" : "border border-white/15"}`}
                onClick={() => update({ localizationRelativeUplift: lift })}
              >
                {lift === 0 ? "0%" : `+${Math.round(lift * 100)}%`} relative lift
              </button>
            ))}
          </div>
          <p className="mt-2 text-[15px] text-gold">
            Illustrative assumption — test with a randomised experiment. Currently {formatPercent(scenario.localizationRelativeUplift, 0)} on the metrics slide.
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Fact title="Audience" body="Delhi NCR eligible traffic" />
            <Fact title="Variant A" body="Current English-language acquisition journey" />
            <Fact title="Variant B" body="Hindi-first creative and landing experience" />
            <Fact title="Primary metric" body="First-booking conversion rate" />
          </div>
          <p className="mt-3 text-[15px] text-soft">Guardrails: CAC, refund rate, support contacts, checkout completion. Read results by device, campaign, and audience.</p>
        </div>
        <PhoneMockup label="Product concept · Delhi NCR · not a live listing">
          <div className={`flex h-full flex-col ${language === "hi" ? "font-deva" : ""}`} lang={language}>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="font-display text-[18px]">Fever</span>
              <span className="text-[13px] text-soft">Delhi NCR</span>
            </div>
            <div className="flex-1 overflow-hidden px-4">
              {tab === "discover" && (
                <>
                  <div className="relative h-40 overflow-hidden rounded-2xl bg-[radial-gradient(circle_at_50%_80%,rgba(233,188,112,0.85),rgba(111,65,215,0.25)_45%,#071018_72%)]">
                    <p className="absolute right-3 bottom-3 left-3 text-[13px] text-glow">Abstract candlelight · concept art</p>
                  </div>
                  <div key={`${language}-${filter}`}>
                      <h3 className="mt-4 text-[22px] leading-tight">{copy.hero}</h3>
                      <p className="mt-2 text-[15px] text-soft">{copy.support}</p>
                      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
                        {copy.filters.map((item, index) => (
                          <button key={item} type="button" aria-pressed={filter === index} className={`shrink-0 rounded-full px-3 py-1 text-[13px] ${filter === index ? "bg-fever text-white" : "bg-white/10"}`} onClick={() => setFilter(index)}>
                            {item}
                          </button>
                        ))}
                      </div>
                      <article className="mt-3 rounded-2xl border border-white/10 p-3">
                        <p className="text-[16px] leading-snug">{copy.card}</p>
                        <p className="mt-1 text-[13px] text-soft">{copy.meta}</p>
                        <p className="mt-2 text-[13px] text-gold">Example only · no live price</p>
                      </article>
                      <button type="button" className="mt-3 w-full rounded-full bg-fever py-3 text-[15px]">{copy.cta}</button>
                    </div>
                </>
              )}
              {tab === "saved" && <Empty title={language === "hi" ? "अभी कुछ सेव नहीं है" : "Nothing saved in this concept"} />}
              {tab === "bookings" && <Empty title={language === "hi" ? "बुकिंग एक असली चेकआउट के बाद दिखेगी" : "Bookings would appear after a real checkout"} />}
            </div>
            <div className="grid grid-cols-3 border-t border-white/10 text-[13px]">
              {(
                [
                  ["discover", language === "hi" ? "खोजें" : "Discover"],
                  ["saved", language === "hi" ? "सेव्ड" : "Saved"],
                  ["bookings", language === "hi" ? "बुकिंग" : "Bookings"],
                ] as const
              ).map(([id, label]) => (
                <button key={id} type="button" className={`py-3 ${tab === id ? "text-fever" : "text-soft"}`} onClick={() => setTab(id)}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </PhoneMockup>
      </div>
    </SceneContainer>
  );
}

function Fact({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-white/10 p-3">
      <p className="text-[13px] text-gold">{title}</p>
      <p className="text-[15px] leading-snug">{body}</p>
    </div>
  );
}

function Empty({ title }: { title: string }) {
  return <p className="grid h-64 place-items-center px-4 text-center text-[16px] text-soft">{title}</p>;
}
