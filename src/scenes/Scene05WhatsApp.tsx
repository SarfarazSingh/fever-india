import { useState } from "react";
import { LanguageSwitch } from "../components/phones/LanguageSwitch";
import { PhoneMockup } from "../components/phones/PhoneMockup";
import { SceneContainer } from "../components/presentation/SceneContainer";
import { DisclaimerLabel } from "../components/ui/DisclaimerLabel";

const STEPS = ["Discovery", "Opt-in", "Recommendation", "Booking", "Post-event", "Next experience", "Referral"];
const PREFERENCES = ["Sufi", "Ghazal", "Bollywood instrumental", "Classical fusion"];
const METRICS = ["Opt-in rate", "Click-through rate", "Booking conversion", "Incremental CAC", "Repeat booking rate", "Opt-out rate"];

export function Scene05WhatsApp() {
  const [step, setStep] = useState(0);
  const [language, setLanguage] = useState<"en" | "hi">("en");
  const [consent, setConsent] = useState(true);
  const [preference, setPreference] = useState(PREFERENCES[0]);
  const [booked, setBooked] = useState(false);
  const hi = language === "hi";

  const visible = consent ? step : Math.min(step, 1);

  return (
    <SceneContainer>
      <div className="grid min-h-0 flex-1 items-start gap-4 lg:grid-cols-[0.9fr_0.7fr_0.7fr]">
        <div>
          <DisclaimerLabel>Consent-based lifecycle experiment</DisclaimerLabel>
          <h2 className="mt-2 font-display text-[clamp(32px,3.6vw,48px)] leading-[0.95] font-medium">From discovery to a conversation.</h2>
          <p className="mt-2 text-[16px] text-soft">A concept mock. Not a live channel. If consent is off, marketing messages do not appear.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <LanguageSwitch language={language} onChange={setLanguage} />
            <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2 text-[15px]" onClick={() => setConsent((value) => !value)} aria-pressed={consent}>
              Consent {consent ? "on" : "off"}
            </button>
            <button type="button" className="focus-ring rounded-full border border-white/15 px-4 py-2 text-[15px]" onClick={() => { setStep(0); setBooked(false); }}>
              Replay
            </button>
          </div>
          <label className="mt-4 block text-[15px]">
            Stated music preference
            <select className="focus-ring mt-1 w-full rounded-xl border border-white/15 bg-ink px-3 py-2" value={preference} onChange={(event) => setPreference(event.target.value)}>
              {PREFERENCES.map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <ol className="mt-3 space-y-1">
            {STEPS.map((label, index) => (
              <li key={label}>
                <button type="button" className={`focus-ring w-full rounded-xl px-3 py-2 text-left text-[15px] ${visible === index ? "bg-fever text-white" : "bg-white/5"}`} onClick={() => setStep(index)}>
                  0{index + 1} {label}
                </button>
              </li>
            ))}
          </ol>
        </div>
        <PhoneMockup label="Concept mock · not a live channel">
          <div className={`flex h-full flex-col bg-[#0b141a] ${hi ? "font-deva" : ""}`} lang={language}>
            <div className="bg-[#1f2c34] px-4 py-3">
              <p className="text-[16px]">Fever evenings</p>
              <p className="text-[12px] text-soft">Delhi · concept thread</p>
            </div>
            <div className="flex-1 space-y-2 overflow-hidden px-3 py-3">
              <Bubble mine={false}>
                {hi ? "आपने दिल्ली की एक शाम देखी।" : "You tapped a Fever evening in Delhi."}
              </Bubble>
              {visible >= 1 && (
                <Bubble mine>
                  {consent
                    ? hi ? "हाँ, मुझे अपडेट भेजें।" : "Yes — send me event updates."
                    : hi ? "अभी नहीं।" : "Not now."}
                </Bubble>
              )}
              {consent && visible >= 2 && (
                <Bubble mine={false}>
                  {hi ? "इस वीकेंड कुछ खास करने का मन है?" : "Looking for something special this weekend?"}
                </Bubble>
              )}
              {consent && visible >= 3 && (
                <button type="button" className="w-full rounded-xl bg-[#1f2c34] p-3 text-left" onClick={() => setBooked(true)}>
                  <p className="text-[15px]">{preference} · Delhi NCR</p>
                  <p className="mt-1 text-[13px] text-[#7ee0a8]">{booked ? (hi ? "डेमो चेकआउट खुला" : "Demo checkout opened") : hi ? "अनुभव देखें" : "View experience"}</p>
                  <p className="text-[12px] text-soft">{hi ? "काल्पनिक कार्ड" : "Fictional event card"}</p>
                </button>
              )}
              {consent && visible >= 4 && <Bubble mine={false}>{hi ? "शाम कैसी रही?" : "How was your evening?"}</Bubble>}
              {consent && visible >= 5 && (
                <Bubble mine={false}>
                  {hi ? `${preference} के पास एक और शाम।` : `A next evening, closer to ${preference}.`}
                </Bubble>
              )}
              {consent && visible >= 6 && (
                <Bubble mine>
                  {hi ? "किसी अपने के साथ साझा करें।" : "Share with a friend — optional."}
                </Bubble>
              )}
              {!consent && visible >= 1 && (
                <p className="rounded-xl border border-dashed border-white/20 p-3 text-[14px] text-soft">
                  {hi ? "सहमति नहीं है, इसलिए मार्केटिंग संदेश नहीं दिखे।" : "Consent is off, so marketing messages stay hidden."}
                </p>
              )}
            </div>
          </div>
        </PhoneMockup>
        <div>
          <h3 className="font-display text-[28px]">Proposed metrics</h3>
          <p className="mt-1 text-[15px] text-gold">Proposed metrics; results not yet observed.</p>
          <ul className="mt-4 space-y-2">
            {METRICS.map((metric) => (
              <li key={metric} className="flex items-center justify-between rounded-xl border border-white/10 px-3 py-2 text-[16px]">
                <span>{metric}</span>
                <span className="text-soft">—</span>
              </li>
            ))}
          </ul>
          <button type="button" className="focus-ring mt-4 rounded-full bg-fever px-4 py-2 text-[15px]" onClick={() => setStep((value) => Math.min(STEPS.length - 1, value + 1))}>
            Advance message
          </button>
        </div>
      </div>
    </SceneContainer>
  );
}

function Bubble({ children, mine = false }: { children: string; mine?: boolean }) {
  return (
    <p
      className={`max-w-[90%] rounded-2xl px-3 py-2 text-[15px] leading-snug ${mine ? "ml-auto bg-[#005c4b]" : "bg-[#1f2c34]"}`}
    >
      {children}
    </p>
  );
}
