import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  LoaderCircle,
  Plane,
  X,
} from "lucide-react";
import {
  api,
  clock,
  dayOffset,
  duration,
  localDate,
  money,
  post,
  type Offer,
  type Segment,
  type Slice,
} from "./api";

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className={`modal ${wide ? "wide" : ""}`}>
          <div className="modal-head">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description className={description ? "muted" : "sr-only"}>
                {description || title}
              </Dialog.Description>
            </div>
            <Dialog.Close className="icon-button" aria-label="Close dialog">
              <X size={20} />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  return error ? (
    <div className="error-notice" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="loading" role="status">
      <LoaderCircle size={18} className="spin" />
      {label}
    </span>
  );
}
export function Empty({
  title,
  children,
  icon,
}: {
  title: string;
  children: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon || <Plane size={28} />}
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Toggle({
  label,
  checked,
  onChange,
  hint,
  disabled = false,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  hint?: string;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <label className="toggle-row" htmlFor={id}>
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      <input
        id={id}
        type="checkbox"
        role="switch"
        disabled={disabled}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="switch" aria-hidden="true" />
    </label>
  );
}

type Airport = [string, string, string];
let airportCache: Airport[] | undefined;
export function AirportInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [airports, setAirports] = useState<Airport[]>(airportCache || []);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    if (!airportCache)
      fetch("/airports.json")
        .then((r) => r.json())
        .then((v: Airport[]) => {
          airportCache = v;
          setAirports(v);
        })
        .catch(() =>
          setAirports([
            ["MAD", "Madrid", "Barajas"],
            ["LHR", "London", "Heathrow"],
            ["JFK", "New York", "John F. Kennedy"],
            ["SIN", "Singapore", "Changi"],
          ]),
        );
  }, []);
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const selected = airports.find((a) => a[0] === value);
  const matches = airports
    .filter((a) => a.join(" ").toLowerCase().includes(query.toLowerCase()))
    .sort(
      (a, b) =>
        Number(b[0] === query.toUpperCase()) -
        Number(a[0] === query.toUpperCase()),
    )
    .slice(0, 7);
  const choose = (a: Airport) => {
    onChange(a[0]);
    setQuery("");
    setOpen(false);
  };
  return (
    <div className="airport-field" ref={ref}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={id + "-list"}
        aria-autocomplete="list"
        aria-activedescendant={
          open && matches[active] ? id + "-" + active : undefined
        }
        autoComplete="off"
        value={
          open ? query : selected ? `${selected[1]} (${selected[0]})` : value
        }
        placeholder="City or airport"
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((i) => Math.min(i + 1, matches.length - 1));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((i) => Math.max(0, i - 1));
          }
          if (e.key === "Enter" && open && matches[active]) {
            e.preventDefault();
            choose(matches[active]);
          }
        }}
      />
      <small>{selected?.[2] || "Select an airport"}</small>
      {open && (
        <ul id={id + "-list"} role="listbox" className="airport-options">
          {matches.map((a, i) => (
            <li
              id={id + "-" + i}
              key={a[0]}
              role="option"
              aria-selected={active === i}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(a);
              }}
              className={active === i ? "active" : ""}
            >
              <b>{a[0]}</b>
              <span>
                {a[1]}
                <small>{a[2]}</small>
              </span>
            </li>
          ))}
          {!matches.length && <li>No airports found</li>}
        </ul>
      )}
    </div>
  );
}

export function SliceSummary({
  slice,
  label,
}: {
  slice: Slice;
  label?: string;
}) {
  const first = slice.segments[0],
    last = slice.segments.at(-1)!;
  const days = dayOffset(first.departure_local, last.arrival_local);
  return (
    <div className="slice-summary">
      {label && <span className="slice-label">{label}</span>}
      <div className="flight-time">
        <strong>{clock(first.departure_local)}</strong>
        <span>{first.origin}</span>
        <small>{localDate(first.departure_local)}</small>
      </div>
      <div className="flight-line">
        <span>{duration(slice.duration_minutes)}</span>
        <div>
          <i />
          <span />
          <Plane size={15} />
          <span />
          <i />
        </div>
        <small>
          {slice.stops === 0
            ? "Nonstop"
            : `${slice.stops} stop${slice.stops > 1 ? "s" : ""} · ${slice.segments
                .slice(0, -1)
                .map((s) => s.destination)
                .join(", ")}`}
        </small>
      </div>
      <div className="flight-time end">
        <strong>
          {clock(last.arrival_local)}
          {days > 0 && <sup>+{days}</sup>}
        </strong>
        <span>{last.destination}</span>
        <small>{localDate(last.arrival_local)}</small>
      </div>
    </div>
  );
}

export function FareRules({ offer }: { offer: Offer }) {
  const rule = (c: Offer["refund"], action: string) =>
    c.allowed === null || c.allowed === undefined
      ? `${action}: not provided`
      : !c.allowed
        ? `${action}: not permitted`
        : `${action}: permitted${c.penalty_amount != null ? ` · ${money(c.penalty_amount, c.penalty_currency || offer.currency)} fee` : " · fee not provided"}`;
  return (
    <div className="fare-rules">
      <span>{rule(offer.change, "Changes")}</span>
      <span>{rule(offer.refund, "Refunds")}</span>
      <small>
        Fare differences may apply to changes. Rules shown are for the whole
        itinerary before departure.
      </small>
    </div>
  );
}

export function SegmentDetails({ segments }: { segments: Segment[] }) {
  return (
    <div className="segment-list">
      {segments.map((seg, i) => (
        <div key={seg.id + i}>
          <div className="segment">
            <span className="segment-dot" />
            <div>
              <b>
                {seg.flight_number} · {seg.airline_name}
              </b>
              {seg.operating_airline &&
                seg.operating_airline !== seg.airline && (
                  <p className="muted">
                    Operated by{" "}
                    {seg.operating_airline_name || seg.operating_airline}
                  </p>
                )}
              <div className="segment-route">
                <span>
                  {clock(seg.departure_local)} {seg.origin_city} ({seg.origin})
                  <small>
                    {localDate(seg.departure_local)} · {seg.origin_timezone}
                    {seg.origin_terminal &&
                      ` · Terminal ${seg.origin_terminal}`}
                  </small>
                </span>
                <ArrowRight size={16} />
                <span>
                  {clock(seg.arrival_local)} {seg.destination_city} (
                  {seg.destination})
                  <small>
                    {localDate(seg.arrival_local)} · {seg.destination_timezone}
                  </small>
                </span>
              </div>
              <div className="segment-meta">
                <span>
                  {seg.cabin_name || seg.cabin || "Cabin unconfirmed"}
                </span>
                <span>{seg.aircraft || "Aircraft unconfirmed"}</span>
                {seg.seat_type && (
                  <span>{seg.seat_type.replaceAll("_", " ")} seat</span>
                )}
                <span>
                  {seg.checked_bags == null
                    ? "Baggage unconfirmed"
                    : `${seg.checked_bags} checked bag${seg.checked_bags === 1 ? "" : "s"}`}
                </span>
              </div>
            </div>
          </div>
          {i < segments.length - 1 && (
            <div className="connection-note">
              Connection in {seg.destination_city} ·{" "}
              {duration(
                Math.round(
                  (Date.parse(segments[i + 1].departure_at) -
                    Date.parse(seg.arrival_at)) /
                    60000,
                ),
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const airlineColors: Record<string, string> = {
  BA: "#152b52",
  IB: "#a61929",
  QR: "#672146",
  SQ: "#1c304e",
  AF: "#1e2c50",
  LH: "#12346a",
  EK: "#bd252c",
  DL: "#a71d32",
  UA: "#1640a0",
};
export function AirlineMark({ code }: { code: string }) {
  return (
    <span
      className="airline-mark"
      style={{ background: airlineColors[code] || "#324c40" }}
    >
      <Plane size={22} />
      <small>{code}</small>
    </span>
  );
}

export function FlightCard({
  offer,
  selected,
  onCompare,
  onBook,
  searchId,
  canBook = true,
}: {
  offer: Offer;
  selected: boolean;
  onCompare: () => void;
  onBook: (offer: Offer) => void;
  searchId: string;
  canBook?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [handoff, setHandoff] = useState<{
    match: string;
    prefilled?: boolean;
    url?: string;
    message: string;
  }>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const first = offer.slices[0].segments[0];
  async function openAirline() {
    setBusy(true);
    setError(undefined);
    try {
      setHandoff(
        await post("/airline-handoffs", {
          search_id: searchId,
          offer_id: offer.id,
        }),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article
      className={`flight-card ${offer.recommendation === "Your best match" ? "best" : ""}`}
    >
      {offer.recommendation === "Your best match" && (
        <div className="recommendation-ribbon">
          <CheckCircle2 size={14} /> YOUR BEST MATCH{" "}
          <span>A little more you.</span>
        </div>
      )}
      <div className="flight-card-top">
        <div className="carrier">
          <AirlineMark code={first.airline} />
          <div>
            <h3>{first.airline_name}</h3>
            <p>
              {first.cabin_name ||
                (first.cabin === "first" ? "First class" : "Business class")}
              <span> · </span>
              {first.flight_number}
            </p>
          </div>
        </div>
        <label className="compare-check">
          <input type="checkbox" checked={selected} onChange={onCompare} />
          Compare
        </label>
      </div>
      {offer.slices.map((slice, i) => (
        <SliceSummary
          key={slice.id}
          slice={slice}
          label={
            offer.slices.length > 1
              ? i === 0
                ? "OUTBOUND"
                : "RETURN"
              : undefined
          }
        />
      ))}
      <div className="match-reasons">
        {offer.reasons.slice(0, 3).map((r) => (
          <span key={r}>
            <Check size={13} />
            {r}
          </span>
        ))}
      </div>
      {offer.tradeoffs.length > 0 && (
        <p className="tradeoffs">{offer.tradeoffs.join(" · ")}</p>
      )}
      <div className="flight-card-bottom">
        <button
          className="text-button"
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          Flight & fare details{" "}
          <ChevronDown size={15} className={expanded ? "rotated" : ""} />
        </button>
        <div className="price-block">
          <span>
            <strong>{money(offer.total_amount, offer.currency)}</strong>
            <small>
              Total · 1 adult{offer.slices.length > 1 ? " · return" : ""}
            </small>
          </span>
          <button
            className="button secondary"
            disabled={busy}
            onClick={openAirline}
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <ExternalLink size={15} />
            )}
            View airline flights
          </button>
          {canBook && offer.card_eligible && (
            <button
              className="button primary"
              disabled={Date.parse(offer.expires_at) <= Date.now()}
              onClick={() => onBook(offer)}
            >
              Book here <ArrowRight size={15} />
            </button>
          )}
        </div>
      </div>
      {Date.parse(offer.expires_at) <= Date.now() && (
        <p className="tradeoffs">
          This fare expired. Search again for current availability.
        </p>
      )}
      {expanded && (
        <div className="expanded-flight">
          {offer.slices.map((s, i) => (
            <div key={s.id}>
              <h4>{i === 0 ? "Outbound journey" : "Return journey"}</h4>
              <SegmentDetails segments={s.segments} />
            </div>
          ))}
          <FareRules offer={offer} />
          <p className="muted">
            Aisle preference is a request. Seats and aircraft can change until
            confirmed by the airline.
          </p>
          {offer.fare_options.length > 1 && (
            <div className="fare-options">
              <h4>Choose your fare</h4>
              {offer.fare_options.map((fare) => (
                <div className="fare-option" key={fare.id}>
                  <div>
                    <b>{fare.name}</b>
                    <p>
                      {fare.refund.allowed === true
                        ? "Refunds permitted"
                        : fare.refund.allowed === false
                          ? "Nonrefundable"
                          : "Refund rules unconfirmed"}{" "}
                      ·{" "}
                      {fare.change.allowed === true
                        ? "Changes permitted"
                        : fare.change.allowed === false
                          ? "Changes not permitted"
                          : "Change rules unconfirmed"}
                    </p>
                    <small>
                      Fees and fare differences may apply; review the final
                      quote.
                    </small>
                  </div>
                  <strong>{money(fare.total_amount, fare.currency)}</strong>
                  {canBook && (
                    <button
                      className="button secondary"
                      onClick={() =>
                        onBook({
                          ...offer,
                          id: fare.id,
                          total_amount: fare.total_amount,
                          currency: fare.currency,
                          fare_name: fare.name,
                          refund: fare.refund,
                          change: fare.change,
                        })
                      }
                    >
                      Choose fare
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <ErrorNotice error={error} />
      <Modal
        open={!!handoff}
        onOpenChange={(v) => !v && setHandoff(undefined)}
        title={
          handoff?.match === "exact_itinerary"
            ? "Continue with the airline"
            : handoff?.prefilled
              ? "Your airline search is ready"
              : "Search with the airline"
        }
        description={handoff?.message}
      >
        {handoff?.url && (
          <a
            className="button primary full"
            href={handoff.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setHandoff(undefined)}
          >
            {handoff.match === "exact_itinerary"
              ? "Continue at airline"
              : handoff.prefilled
                ? "Open airline flight results"
                : "Search on airline"}
            <ExternalLink size={16} />
          </a>
        )}
      </Modal>
    </article>
  );
}
