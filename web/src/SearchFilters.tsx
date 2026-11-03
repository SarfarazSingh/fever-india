import { useEffect, useId, useState } from "react";
import type { Profile } from "./api";
import { Toggle } from "./components";

export function SearchFilters({
  prefs,
  setPrefs,
}: {
  prefs: Profile;
  setPrefs: (p: Profile) => void;
}) {
  const filterId = useId();
  const airlineCodes = prefs.airlines.join(", ");
  const [airlineText, setAirlineText] = useState(airlineCodes);
  useEffect(() => setAirlineText(airlineCodes), [airlineCodes]);
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) =>
    setPrefs({ ...prefs, [key]: value });
  return (
    <div className="filter-content">
      <div className="filter-section">
        <label htmlFor={filterId + "-cabin"}>CABIN</label>
        <select
          id={filterId + "-cabin"}
          value={prefs.cabin}
          onChange={(e) => set("cabin", e.target.value as Profile["cabin"])}
        >
          <option value="business">Business class</option>
          <option value="first">First class</option>
          <option value="either">Business or first</option>
        </select>
        <Toggle
          label="Premium throughout"
          hint="Every flight, every direction"
          checked={!prefs.allow_mixed_cabin}
          onChange={(v) => set("allow_mixed_cabin", !v)}
        />
      </div>
      <div className="filter-section">
        <label>THE JOURNEY</label>
        <Toggle
          label="Nonstop only"
          hint="Make this a requirement"
          checked={prefs.direct_only}
          onChange={(v) => set("direct_only", v)}
        />
        <Toggle
          label="Flexible fares only"
          hint="Verified changes or refunds"
          checked={prefs.flexible_only}
          onChange={(v) => set("flexible_only", v)}
        />
      </div>
      <div className="filter-section">
        <label htmlFor={filterId + "-airlines"}>PREFERRED AIRLINES</label>
        <input
          id={filterId + "-airlines"}
          placeholder="IB, BA, QR"
          value={airlineText}
          onChange={(e) => {
            setAirlineText(e.target.value.toUpperCase());
            set(
              "airlines",
              e.target.value
                .toUpperCase()
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean),
            );
          }}
        />
        <Toggle
          label="Only these airlines"
          checked={prefs.airlines_required}
          onChange={(v) => set("airlines_required", v)}
        />
      </div>
      <div className="filter-section">
        <label htmlFor={filterId + "-after"}>DEPARTURE WINDOW</label>
        <div className="time-window">
          <select
            aria-label="Depart after"
            id={filterId + "-after"}
            value={prefs.depart_after}
            onChange={(e) => set("depart_after", Number(e.target.value))}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {String(i).padStart(2, "0")}:00
              </option>
            ))}
          </select>
          <span>—</span>
          <select
            aria-label="Depart before"
            value={prefs.depart_before}
            onChange={(e) => set("depart_before", Number(e.target.value))}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i + 1}>
                {String(i + 1).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </div>
        <Toggle
          label="Only within this window"
          checked={prefs.time_required}
          onChange={(v) => set("time_required", v)}
        />
      </div>
      <div className="filter-section">
        <label htmlFor={filterId + "-aircraft"}>PREFERRED AIRCRAFT</label>
        <input
          id={filterId + "-aircraft"}
          value={prefs.aircraft}
          placeholder="A350, 787"
          onChange={(e) => set("aircraft", e.target.value)}
        />
        <Toggle
          label="Require aircraft match"
          checked={prefs.aircraft_required}
          onChange={(v) => set("aircraft_required", v)}
        />
      </div>
      <p className="filter-footnote">
        Non-required preferences help us rank your options. We’ll always explain
        the tradeoffs.
      </p>
    </div>
  );
}
