import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addDays,
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { fromZonedTime } from "date-fns-tz";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Luggage,
  Mail,
  MapPin,
  Plane,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import {
  api,
  clock,
  localDate,
  money,
  post,
  type CalendarEvent,
  type Draft,
  type Guide,
  type Segment,
  type Slice,
  type Trip,
  type TripData,
} from "./api";
import {
  Badge,
  Empty,
  ErrorNotice,
  Modal,
  SegmentDetails,
  SliceSummary,
  Spinner,
} from "./components";
import { useSession } from "./session";

export function TripsPage() {
  const query = useQuery({
    queryKey: ["trips"],
    queryFn: () => api<Trip[]>("/trips"),
  });
  const drafts = useQuery({
    queryKey: ["imports"],
    queryFn: () => api<Draft[]>("/imports"),
  });
  const [tab, setTab] = useState("upcoming");
  const [importOpen, setImportOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>();
  const [manualOpen, setManualOpen] = useState(false);
  const end = (t: Trip) =>
    Math.max(
      ...t.slices.flatMap((s) =>
        s.segments.map((g) => Date.parse(g.arrival_at)),
      ),
    );
  const filtered = (query.data || []).filter((t) =>
    tab === "attention"
      ? t.status === "needs_attention" || t.ticketing_status === "pending"
      : tab === "past"
        ? end(t) < Date.now() || t.status === "cancelled"
        : end(t) >= Date.now() && t.status !== "cancelled",
  );
  return (
    <div className="page standard-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">EVERY JOURNEY, TOGETHER</span>
          <h1>Your next chapters.</h1>
          <p>All the details. A little less to think about.</p>
        </div>
        <button className="button primary" onClick={() => setImportOpen(true)}>
          <Plus size={17} />
          Add a trip
        </button>
      </div>
      {!!drafts.data?.length && (
        <div className="attention-banner">
          <Mail size={20} />
          <span>
            <b>
              {drafts.data.length} booking import
              {drafts.data.length === 1 ? "" : "s"} ready for review
            </b>
            <small>
              Check the details before adding them to your itinerary.
            </small>
          </span>
          <button
            className="text-button"
            onClick={() => setDraft(drafts.data![0])}
          >
            Review <ArrowRight size={15} />
          </button>
        </div>
      )}
      <div className="tabs" role="group" aria-label="Trip view">
        {[
          ["upcoming", "Upcoming"],
          ["past", "Past journeys"],
          ["attention", "Needs attention"],
        ].map(([value, label]) => (
          <button
            key={value}
            className={tab === value ? "active" : ""}
            onClick={() => setTab(value)}
          >
            {label}
            {value === "upcoming" && (
              <span>
                {
                  (query.data || []).filter(
                    (t) => end(t) >= Date.now() && t.status !== "cancelled",
                  ).length
                }
              </span>
            )}
          </button>
        ))}
      </div>
      <ErrorNotice error={query.error || drafts.error} />
      {query.isPending ? (
        <Spinner label="Gathering your journeys" />
      ) : !filtered.length ? (
        <Empty
          title={
            tab === "upcoming"
              ? "Your next chapter is unwritten."
              : "Nothing here just yet."
          }
          icon={<Luggage />}
        >
          <p>
            {tab === "upcoming"
              ? "Find your next flight or add an existing booking."
              : "Your journeys will appear here when the time comes."}
          </p>
          <Link className="button primary" to="/search">
            Find a flight <ArrowRight size={15} />
          </Link>
        </Empty>
      ) : (
        <div className="trip-grid">
          {filtered.map((t) => (
            <Link className="trip-card" key={t.id} to={"/trips/" + t.id}>
              <div className="trip-photo">
                <img
                  src={
                    t.destination === "LHR" || t.destination === "LGW"
                      ? "/images/london.jpg"
                      : "/images/lake.jpg"
                  }
                  alt="Travel inspiration"
                />
                <Badge>
                  {t.is_demo ? "Demo itinerary" : t.status.replaceAll("_", " ")}
                </Badge>
                <span className="trip-photo-code">{t.destination}</span>
              </div>
              <div className="trip-card-body">
                <span className="eyebrow">
                  {localDate(t.slices[0].segments[0].departure_local, {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </span>
                <h2>{t.destination_city}</h2>
                <div className="trip-card-route">
                  <Plane size={15} />
                  {t.origin}
                  <ArrowRight size={13} />
                  {t.destination}
                  <span>
                    {t.slices.length > 1 ? "Return journey" : "One way"}
                  </span>
                </div>
                <div className="trip-card-footer">
                  <span>{t.references.join(" · ")}</span>
                  <span>
                    View itinerary <ArrowRight size={14} />
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      <Modal
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bring your trip along"
        description="Paste your airline confirmation or add the itinerary yourself."
      >
        <ImportPaste
          onDraft={(d) => {
            setDraft(d);
            setImportOpen(false);
          }}
        />
        <div className="divider-label">or</div>
        <button
          className="button secondary full"
          onClick={() => {
            setImportOpen(false);
            setManualOpen(true);
          }}
        >
          Enter flight details manually <Plus size={16} />
        </button>
        <p className="fine-print">
          You can also connect Gmail or set up forwarding in{" "}
          <Link to="/preferences">preferences</Link>.
        </p>
      </Modal>
      <TripEditor
        open={manualOpen || !!draft}
        onClose={() => {
          setDraft(undefined);
          setManualOpen(false);
        }}
        draft={draft}
      />
    </div>
  );
}

function ImportPaste({ onDraft }: { onDraft: (d: Draft) => void }) {
  const [raw, setRaw] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      onDraft(await post<Draft>("/imports/preview", { raw_text: raw }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <label htmlFor="confirmation-text">Booking confirmation</label>
      <textarea
        id="confirmation-text"
        rows={8}
        minLength={20}
        maxLength={100000}
        required
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        placeholder={
          "Paste the airline email here.\n\nWe’ll extract what we can and ask you to check the details."
        }
      />
      <ErrorNotice error={error} />
      <button className="button primary full" disabled={busy}>
        {busy ? (
          <Spinner label="Reading your confirmation" />
        ) : (
          <>
            Review flight details
            <ArrowRight size={16} />
          </>
        )}
      </button>
    </form>
  );
}

const timezoneMap: Record<string, string> = {
  MAD: "Europe/Madrid",
  BCN: "Europe/Madrid",
  LHR: "Europe/London",
  LGW: "Europe/London",
  LCY: "Europe/London",
  JFK: "America/New_York",
  EWR: "America/New_York",
  SIN: "Asia/Singapore",
  DOH: "Asia/Qatar",
  DXB: "Asia/Dubai",
  SYD: "Australia/Sydney",
  CDG: "Europe/Paris",
  FRA: "Europe/Berlin",
  HKG: "Asia/Hong_Kong",
  ATH: "Europe/Athens",
};
type Leg = {
  flight: string;
  origin: string;
  destination: string;
  departure: string;
  arrival: string;
  origin_timezone: string;
  destination_timezone: string;
  direction: number;
};
const blankLeg = (): Leg => ({
  flight: "",
  origin: "",
  destination: "",
  departure: "",
  arrival: "",
  origin_timezone: "",
  destination_timezone: "",
  direction: 0,
});
export function TripEditor({
  open,
  onClose,
  draft,
}: {
  open: boolean;
  onClose: () => void;
  draft?: Draft;
}) {
  return (
    <Modal
      open={open}
      onOpenChange={(v) => !v && onClose()}
      title="Check your itinerary"
      description="Keep every segment and both directions together. Dates and times use the airport’s local timezone."
      wide
    >
      {open && (
        <TripEditorForm
          key={draft?.id || "manual"}
          onClose={onClose}
          draft={draft}
        />
      )}
    </Modal>
  );
}
function TripEditorForm({
  onClose,
  draft,
}: {
  onClose: () => void;
  draft?: Draft;
}) {
  const session = useSession();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState(
    draft?.data.passenger_name ||
      [session.profile.first_name, session.profile.last_name]
        .filter(Boolean)
        .join(" "),
  );
  const [ref, setRef] = useState(draft?.data.references.join(", ") || "");
  const [legs, setLegs] = useState<Leg[]>(
    draft?.data.slices?.length
      ? draft.data.slices.flatMap((s, i) =>
          s.segments.map((g) => ({
            flight: g.flight_number,
            origin: g.origin,
            destination: g.destination,
            departure: g.departure_local.slice(0, 16),
            arrival: g.arrival_local.slice(0, 16),
            origin_timezone: g.origin_timezone,
            destination_timezone: g.destination_timezone,
            direction: i,
          })),
        )
      : [blankLeg()],
  );
  const [cancelled, setCancelled] = useState(!!draft?.data.cancelled);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const update = (i: number, key: keyof Leg, v: string | number) =>
    setLegs((prev) =>
      prev.map((l, j) =>
        j === i
          ? {
              ...l,
              [key]: v,
              ...(key === "origin" && timezoneMap[String(v)]
                ? { origin_timezone: timezoneMap[String(v)] }
                : {}),
              ...(key === "destination" && timezoneMap[String(v)]
                ? { destination_timezone: timezoneMap[String(v)] }
                : {}),
            }
          : l,
      ),
    );
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const slices: Slice[] = [];
      for (const [i, l] of legs.entries()) {
        const departure = fromZonedTime(l.departure, l.origin_timezone);
        const arrival = fromZonedTime(l.arrival, l.destination_timezone);
        if (!Number.isFinite(+departure) || !Number.isFinite(+arrival))
          throw new Error(
            "Check the airport timezone and local time for every flight.",
          );
        const seg: Segment = {
          id: "manual-" + i,
          origin: l.origin,
          destination: l.destination,
          origin_city: l.origin,
          destination_city: l.destination,
          origin_timezone: l.origin_timezone,
          destination_timezone: l.destination_timezone,
          departure_at: departure.toISOString(),
          arrival_at: arrival.toISOString(),
          departure_local: l.departure,
          arrival_local: l.arrival,
          airline: l.flight.slice(0, 2),
          airline_name: l.flight.slice(0, 2),
          flight_number: l.flight,
        };
        if (!slices[l.direction])
          slices[l.direction] = {
            id: "manual-slice-" + l.direction,
            segments: [],
            duration_minutes: 0,
            stops: 0,
          };
        slices[l.direction].segments.push(seg);
      }
      const data: TripData = {
        passenger_name: name,
        references: ref
          .split(",")
          .map((r) => r.trim().toUpperCase())
          .filter(Boolean),
        slices: slices.filter(Boolean),
        payment_status: "external",
        ticketing_status: "imported",
        checkin_status: "not_open",
        documents: [],
        cancelled,
        notes: "",
        needs_review: false,
      };
      const result = await post<Trip>(
        draft ? "/imports/" + draft.id + "/confirm" : "/trips",
        data,
      );
      client.invalidateQueries({ queryKey: ["trips"] });
      client.invalidateQueries({ queryKey: ["imports"] });
      client.invalidateQueries({ queryKey: ["calendar"] });
      onClose();
      navigate("/trips/" + result.id);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="trip-editor">
      {draft?.issues && draft.issues.length > 0 && (
        <div className="review-note">
          <b>A few details need your attention</b>
          <ul>
            {draft.issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="form-grid">
        <label>
          Passenger name
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
          />
        </label>
        <label>
          Airline reference(s)
          <input
            required
            minLength={5}
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder="ABC123"
          />
        </label>
      </div>
      {legs.map((l, i) => (
        <div className="leg-editor" key={i}>
          <div className="leg-editor-head">
            <b>Flight {i + 1}</b>
            {legs.length > 1 && (
              <button
                type="button"
                className="icon-button"
                aria-label={`Remove flight ${i + 1}`}
                onClick={() => setLegs(legs.filter((_, j) => i !== j))}
              >
                <X size={16} />
              </button>
            )}
          </div>
          <div className="form-grid three">
            <label>
              Flight number
              <input
                required
                pattern="[A-Z0-9]{2}[0-9]{1,4}"
                placeholder="BA178"
                value={l.flight}
                onChange={(e) =>
                  update(
                    i,
                    "flight",
                    e.target.value.toUpperCase().replaceAll(" ", ""),
                  )
                }
              />
            </label>
            <label>
              From airport
              <input
                required
                pattern="[A-Z]{3}"
                placeholder="JFK"
                maxLength={3}
                value={l.origin}
                onChange={(e) =>
                  update(i, "origin", e.target.value.toUpperCase())
                }
              />
            </label>
            <label>
              To airport
              <input
                required
                pattern="[A-Z]{3}"
                placeholder="LHR"
                maxLength={3}
                value={l.destination}
                onChange={(e) =>
                  update(i, "destination", e.target.value.toUpperCase())
                }
              />
            </label>
          </div>
          <div className="form-grid">
            <label>
              Departure (local)
              <input
                type="datetime-local"
                required
                value={l.departure}
                onChange={(e) => update(i, "departure", e.target.value)}
              />
            </label>
            <label>
              Arrival (local)
              <input
                type="datetime-local"
                required
                value={l.arrival}
                onChange={(e) => update(i, "arrival", e.target.value)}
              />
            </label>
            <label>
              Origin timezone
              <input
                required
                placeholder="America/New_York"
                value={l.origin_timezone}
                onChange={(e) => update(i, "origin_timezone", e.target.value)}
              />
            </label>
            <label>
              Destination timezone
              <input
                required
                placeholder="Europe/London"
                value={l.destination_timezone}
                onChange={(e) =>
                  update(i, "destination_timezone", e.target.value)
                }
              />
            </label>
            <label>
              Journey
              <select
                value={l.direction}
                onChange={(e) => update(i, "direction", Number(e.target.value))}
              >
                <option value={0}>Outbound</option>
                <option value={1}>Return</option>
              </select>
            </label>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="button secondary"
        onClick={() => setLegs([...legs, blankLeg()])}
      >
        <Plus size={15} />
        Add connection or return flight
      </button>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={cancelled}
          onChange={(e) => setCancelled(e.target.checked)}
        />
        This reservation was cancelled
      </label>
      <ErrorNotice error={error} />
      <button className="button primary full" disabled={busy}>
        {busy ? (
          <Spinner label="Saving your itinerary" />
        ) : (
          <>
            Save to My Trips <Check size={16} />
          </>
        )}
      </button>
    </form>
  );
}

export function TripDetail() {
  const { tripId } = useParams();
  const [showGuide, setShowGuide] = useState(false);
  const [serviceOpen, setServiceOpen] = useState(false);
  const [kind, setKind] = useState("support");
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState<unknown>();
  const trip = useQuery({
    queryKey: ["trip", tripId],
    queryFn: () => api<Trip>("/trips/" + tripId),
  });
  const guide = useQuery({
    queryKey: ["guide", tripId],
    queryFn: () => api<Guide>("/trips/" + tripId + "/guide"),
    enabled: showGuide,
    staleTime: 10 * 60_000,
  });
  const data = trip.data;
  async function service(e: React.FormEvent) {
    e.preventDefault();
    setError(undefined);
    try {
      const r = await post<{ message: string }>(
        "/trips/" + tripId + "/service-requests",
        { kind, message },
      );
      setNotice(r.message);
      setServiceOpen(false);
    } catch (e) {
      setError(e);
    }
  }
  async function document(index: number) {
    try {
      const r = await api<{ url: string }>(
        "/trips/" + tripId + "/documents/" + index,
      );
      location.assign(r.url);
    } catch (e) {
      setError(e);
    }
  }
  if (trip.isPending)
    return (
      <div className="page standard-page">
        <Spinner label="Opening your itinerary" />
      </div>
    );
  if (!data)
    return (
      <div className="page standard-page">
        <ErrorNotice error={trip.error} />
        <Link to="/trips">Back to My Trips</Link>
      </div>
    );
  return (
    <div className="page standard-page">
      <Link className="back-link" to="/trips">
        <ArrowLeft size={15} />
        All journeys
      </Link>
      <div className="trip-detail-hero">
        <div>
          <span className="eyebrow">YOUR JOURNEY TO</span>
          <h1>{data.destination_city}</h1>
          <p>
            {localDate(data.slices[0].segments[0].departure_local, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}{" "}
            · {data.passenger_name}
          </p>
          <Badge tone="green">
            {data.is_demo
              ? "Fictional demo itinerary"
              : data.status.replaceAll("_", " ")}
          </Badge>
        </div>
        <span className="detail-airport-code">{data.destination}</span>
      </div>
      <div className="trip-detail-layout">
        <div>
          <div className="section-heading">
            <h2>The journey</h2>
            <a href="/api/v1/calendar.ics" className="text-button">
              <Download size={15} />
              Add to calendar
            </a>
          </div>
          {data.slices.map((s, i) => (
            <article className="itinerary-card" key={s.id}>
              <span className="eyebrow">
                {i === 0 ? "OUTBOUND JOURNEY" : "RETURN JOURNEY"}
              </span>
              <SliceSummary slice={s} />
              <SegmentDetails segments={s.segments} />
            </article>
          ))}
          <div className="section-heading">
            <h2>A little local knowledge</h2>
            {!showGuide && (
              <button
                className="text-button"
                onClick={() => setShowGuide(true)}
              >
                Discover {data.destination_city}
                <ArrowRight size={15} />
              </button>
            )}
          </div>
          {showGuide ? (
            guide.isPending ? (
              <Spinner label="Gathering places to consider" />
            ) : guide.error ? (
              <ErrorNotice error={guide.error} />
            ) : (
              <>
                <p className="muted">{guide.data?.note}</p>
                {(["hotels", "restaurants", "activities"] as const).map(
                  (kind) => (
                    <div className="guide-group" key={kind}>
                      <h3>
                        {kind === "hotels"
                          ? "Somewhere to stay"
                          : kind === "restaurants"
                            ? "A table worth finding"
                            : "Time well spent"}
                      </h3>
                      {!guide.data?.[kind].length && (
                        <p className="muted">
                          No verified suggestions available yet.
                        </p>
                      )}
                      {guide.data?.[kind].map((p) => (
                        <div key={p.name}>
                          <a
                            className="place-card"
                            key={p.name}
                            href={p.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <span className="place-icon">
                              <MapPin size={18} />
                            </span>
                            <div>
                              <h4>{p.name}</h4>
                              <p>{p.area}</p>
                              <p>{p.reason}</p>
                              {p.classification && (
                                <small>{p.classification}</small>
                              )}
                              <small>
                                {p.verification}
                                {p.rating ? ` · User rating ${p.rating}/5` : ""}
                              </small>
                              {p.attributions?.map((a, i) => (
                                <small key={i}>{a.displayName}</small>
                              ))}
                            </div>
                            <ExternalLink size={15} />
                          </a>
                          {p.sources && (
                            <div className="source-links">
                              {p.sources.map((url, i) => (
                                <a
                                  key={url}
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Official source {i + 1}{" "}
                                  <ExternalLink size={10} />
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ),
                )}
              </>
            )
          ) : (
            <div className="discovery-placeholder">
              <Sparkles size={22} />
              <p>
                Thoughtful stays, good tables, and things worth making time for.
              </p>
              <button
                className="button secondary"
                onClick={() => setShowGuide(true)}
              >
                Discover your destination
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
        <aside className="trip-detail-sidebar">
          <div className="info-card">
            <span className="eyebrow">THE IMPORTANT DETAILS</span>
            <h3>Your reservation</h3>
            <label>Booking reference</label>
            {data.references.map((ref) => (
              <button
                className="reference-copy"
                key={ref}
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(ref);
                    setNotice("Booking reference copied.");
                  } catch {
                    setNotice("Booking reference: " + ref);
                  }
                }}
              >
                {ref}
                <Copy size={14} />
              </button>
            ))}
            <dl>
              <div>
                <dt>Payment</dt>
                <dd>
                  {data.payment_status === "external"
                    ? "Booked elsewhere"
                    : data.is_demo
                      ? "Demo · no charge"
                      : data.payment_status}
                </dd>
              </div>
              <div>
                <dt>Ticketing</dt>
                <dd>
                  {data.is_demo ? "Demo · no ticket" : data.ticketing_status}
                </dd>
              </div>
              <div>
                <dt>Check-in</dt>
                <dd>
                  {data.checkin_status?.replaceAll("_", " ") || "See airline"}
                </dd>
              </div>
              {data.total_amount && (
                <div>
                  <dt>Journey total</dt>
                  <dd>{money(data.total_amount, data.currency || "USD")}</dd>
                </div>
              )}
            </dl>
            {data.checkin_url && !data.is_demo && (
              <a className="button primary full" href={data.checkin_url} target="_blank" rel="noopener noreferrer">
                Check in with airline <ExternalLink size={16} />
              </a>
            )}
            {data.manage_url && !data.is_demo && (
              <a
                className="button primary full"
                href={data.manage_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Manage with airline <ExternalLink size={14} />
              </a>
            )}
            <p className="fine-print">
              Check-in windows vary by airline. Use your airline reference to
              check in or manage your reservation.
            </p>
          </div>
          <div className="info-card">
            <FileText size={21} />
            <h3>Travel documents</h3>
            {!data.documents?.length ? (
              <p className="muted">
                Issued documents will appear here when securely available.
              </p>
            ) : (
              data.documents.map((d, i) => (
                <button
                  className="document-button"
                  key={i}
                  disabled={data.is_demo || !d.available}
                  onClick={() => document(i)}
                >
                  <FileText size={16} />
                  {String(d.name || d.type || "Travel document").replaceAll(
                    "_",
                    " ",
                  )}
                  {d.unique_identifier
                    ? ` · ${String(d.unique_identifier)}`
                    : ""}
                  {!data.is_demo && !!d.available && <Download size={15} />}
                </button>
              ))
            )}
          </div>
          <div className="concierge-note">
            <LeafIcon />
            <h3>A hand when you need one.</h3>
            <p>
              Keep a change, cancellation, or support request with your trip.
            </p>
            <button
              className="text-button"
              onClick={() => setServiceOpen(true)}
            >
              Request assistance <ArrowRight size={15} />
            </button>
          </div>
        </aside>
      </div>
      {notice && (
        <div className="success-notice" role="status">
          {notice}
          <button
            className="icon-button"
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}
      <ErrorNotice error={error} />
      <Modal
        open={serviceOpen}
        onOpenChange={setServiceOpen}
        title="How can we help?"
        description="This saves a request. It does not change or cancel your booking."
      >
        <form onSubmit={service}>
          <label>
            Request type
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="support">General assistance</option>
              <option value="change">Change a flight</option>
              <option value="cancel">Cancellation request</option>
            </select>
          </label>
          <label>
            Tell us what you need
            <textarea
              required
              minLength={10}
              maxLength={3000}
              rows={5}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </label>
          <button className="button primary full">
            Save request <ArrowRight size={15} />
          </button>
        </form>
      </Modal>
    </div>
  );
}
function LeafIcon() {
  return <Sparkles size={20} />;
}

export function CalendarPage() {
  const query = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api<CalendarEvent[]>("/calendar"),
  });
  const [month, setMonth] = useState(new Date());
  const [view, setView] = useState(() =>
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width:760px)").matches
      ? "agenda"
      : "month",
  );
  const days = eachDayOfInterval({
    start: startOfWeek(startOfMonth(month), { weekStartsOn: 1 }),
    end: endOfWeek(endOfMonth(month), { weekStartsOn: 1 }),
  });
  return (
    <div className="page standard-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">ROOM FOR WHAT’S NEXT</span>
          <h1>A world on your calendar.</h1>
          <p>Every flight, in the time zone where it happens.</p>
        </div>
        <a className="button secondary" href="/api/v1/calendar.ics">
          <Download size={16} />
          Export calendar
        </a>
      </div>
      <div className="calendar-toolbar">
        <div className="month-selector">
          {view === "month" ? (
            <>
              <button
                className="icon-button"
                aria-label="Previous month"
                onClick={() => setMonth(addMonths(month, -1))}
              >
                <ChevronLeft size={19} />
              </button>
              <h2>{format(month, "MMMM yyyy")}</h2>
              <button
                className="icon-button"
                aria-label="Next month"
                onClick={() => setMonth(addMonths(month, 1))}
              >
                <ChevronRight size={19} />
              </button>
              <button
                className="text-button"
                onClick={() => setMonth(new Date())}
              >
                Today
              </button>
            </>
          ) : (
            <h2>Your travel agenda</h2>
          )}
        </div>
        <div className="trip-toggle">
          <button
            className={view === "month" ? "active" : ""}
            onClick={() => setView("month")}
          >
            Month
          </button>
          <button
            className={view === "agenda" ? "active" : ""}
            onClick={() => setView("agenda")}
          >
            Agenda
          </button>
        </div>
      </div>
      <ErrorNotice error={query.error} />
      {query.isPending ? (
        <Spinner label="Loading your travel calendar" />
      ) : view === "month" ? (
        <div className="calendar-wrap">
          <div className="calendar-grid calendar-day-names">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="calendar-grid">
            {days.map((day) => (
              <div
                className={`calendar-day ${!isSameMonth(day, month) ? "other-month" : ""} ${isToday(day) ? "today" : ""}`}
                key={String(day)}
              >
                <span className="day-number">{format(day, "d")}</span>
                {query.data
                  ?.filter((e) => e.date === format(day, "yyyy-MM-dd"))
                  .map((event) => (
                    <Link
                      className="calendar-flight"
                      aria-label={`${event.title}, ${clock(event.departure_local)}, ${event.timezone}`}
                      key={event.id}
                      to={"/trips/" + event.trip_id}
                    >
                      <Plane size={11} />
                      <b>{clock(event.departure_local)}</b>
                      <span>{event.title}</span>
                    </Link>
                  ))}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="agenda">
          {!query.data?.length && (
            <Empty title="Your calendar is open.">
              <p>Flights appear here as soon as you add a trip.</p>
              <Link to="/trips" className="button primary">
                Add a trip
              </Link>
            </Empty>
          )}
          {query.data?.map((e) => (
            <Link
              className="agenda-event"
              key={e.id}
              to={"/trips/" + e.trip_id}
            >
              <div className="agenda-date">
                <strong>
                  {localDate(e.departure_local, { day: "numeric" })}
                </strong>
                <span>{localDate(e.departure_local, { month: "short" })}</span>
              </div>
              <Plane size={20} />
              <div>
                <h3>{e.title}</h3>
                <p>
                  {clock(e.departure_local)} · {e.timezone}
                  <span> → </span>
                  {clock(e.arrival_local)} · {e.destination_timezone}
                </p>
                <small>{e.references.join(" · ")}</small>
              </div>
              <ChevronRight size={18} />
            </Link>
          ))}
        </div>
      )}
      <p className="calendar-note">
        <CalendarDays size={14} />
        Flight dates follow each departure airport’s local time. Calendar
        exports adjust to your calendar’s timezone.
      </p>
    </div>
  );
}
