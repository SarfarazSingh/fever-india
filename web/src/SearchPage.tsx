import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { addDays, format } from "date-fns";
import {
  ArrowDownUp,
  ArrowRight,
  Check,
  ChevronRight,
  Plane,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import {
  api,
  duration,
  money,
  post,
  type Checkout,
  type Offer,
  type Profile,
  type SearchRequest,
  type SearchResponse,
} from "./api";
import {
  AirportInput,
  Badge,
  Empty,
  ErrorNotice,
  FlightCard,
  Modal,
  Spinner,
} from "./components";
import { useSession } from "./session";

export default function SearchPage() {
  const session = useSession();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const searchId = params.get("search");
  const [origin, setOrigin] = useState(
    params.get("from") || session.profile.home_airport,
  );
  const [dest, setDest] = useState(params.get("to") || "LHR");
  const [date, setDate] = useState(
    params.get("date") || format(addDays(new Date(), 21), "yyyy-MM-dd"),
  );
  const [back, setBack] = useState(
    params.get("return") || format(addDays(new Date(), 28), "yyyy-MM-dd"),
  );
  const [round, setRound] = useState(
    params.has("search") ? !!params.get("return") : true,
  );
  const [prefs, setPrefs] = useState<Profile>(session.profile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [sort, setSort] = useState("best");
  const [all, setAll] = useState(false);
  const [compared, setCompared] = useState<string[]>([]);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [loaded, setLoaded] = useState<string | null>(null);
  const [extraOffers, setExtraOffers] = useState<Offer[]>([]);
  const [pageCursor, setPageCursor] = useState<number | null>();
  const [loadingMore, setLoadingMore] = useState(false);
  useEffect(() => {
    setExtraOffers([]);
    setPageCursor(undefined);
  }, [searchId, sort]);
  const query = useQuery({
    queryKey: ["search", searchId, sort],
    queryFn: () =>
      api<SearchResponse>("/searches/" + searchId + "?sort=" + sort),
    enabled: !!searchId,
    refetchInterval: (q) =>
      ["queued", "searching"].includes(q.state.data?.status || "")
        ? 1000
        : false,
  });
  useEffect(() => {
    if (query.data && loaded !== searchId) {
      const r = query.data.request;
      setOrigin(r.origin);
      setDest(r.destination);
      setDate(r.departure_date);
      setBack(r.return_date || back);
      setRound(!!r.return_date);
      setLoaded(searchId);
    }
  }, [query.data, searchId, loaded]);
  useEffect(() => {
    sessionStorage.setItem(
      "lastSearch",
      "/search" + (params.toString() ? "?" + params.toString() : ""),
    );
  }, [params]);
  const waiting =
    busy ||
    (!!searchId &&
      (query.isPending ||
        ["queued", "searching"].includes(query.data?.status || "")));
  async function search(e?: React.FormEvent, override?: Profile) {
    e?.preventDefault();
    setBusy(true);
    setError(undefined);
    setCompared([]);
    setAll(false);
    try {
      const req: SearchRequest = {
        origin,
        destination: dest,
        departure_date: date,
        return_date: round ? back : null,
        preferences: override || prefs,
      };
      const data = await post<SearchResponse>("/searches", req);
      const p = new URLSearchParams({
        search: data.id,
        from: origin,
        to: dest,
        date,
      });
      if (round) p.set("return", back);
      setParams(p);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function book(o: Offer) {
    setError(undefined);
    try {
      const c = await post<Checkout>("/checkout-sessions", {
        search_id: searchId,
        offer_id: o.id,
      });
      navigate("/checkout/" + c.id);
    } catch (e) {
      setError(e);
    }
  }
  const results = useMemo(
    () => [...(query.data?.results || []), ...extraOffers],
    [query.data, extraOffers],
  );
  const nextCursor =
    pageCursor === undefined ? query.data?.next_cursor : pageCursor;
  async function loadMore() {
    if (nextCursor == null) return;
    setLoadingMore(true);
    try {
      const data = await api<SearchResponse>(
        "/searches/" + searchId + "?sort=" + sort + "&cursor=" + nextCursor,
      );
      setExtraOffers((previous) => [...previous, ...data.results]);
      setPageCursor(data.next_cursor);
    } catch (e) {
      setError(e);
    } finally {
      setLoadingMore(false);
    }
  }

  const compare = (o: Offer) => {
    if (compared.includes(o.id))
      setCompared(compared.filter((id) => id !== o.id));
    else if (compared.length < 3) setCompared([...compared, o.id]);
    else setError(new Error("Compare up to three itineraries at a time."));
  };
  const firstName = session.profile.first_name || "Federico";
  const appliedPrefs = query.data?.request.preferences || prefs;
  return (
    <div className="page search-page">
      <header className="search-intro">
        <span className="eyebrow">YOUR PRIVATE TRAVEL DESK</span>
        <h1>
          Where to next, <span>{firstName}</span>?
        </h1>
        <p>Find your next flight. We’ll take care of the details.</p>
      </header>
      <form className="search-box" onSubmit={search}>
        <div className="search-box-top">
          <div className="trip-toggle" role="group" aria-label="Journey type">
            <button
              type="button"
              className={round ? "active" : ""}
              aria-pressed={round}
              onClick={() => setRound(true)}
            >
              Round trip
            </button>
            <button
              type="button"
              className={!round ? "active" : ""}
              aria-pressed={!round}
              onClick={() => setRound(false)}
            >
              One way
            </button>
          </div>
          <span className="search-traveler">
            <span className="green-dot" />1 adult <span>·</span>{" "}
            {prefs.cabin === "either"
              ? "Business or first"
              : prefs.cabin === "first"
                ? "First class"
                : "Business class"}
          </span>
        </div>
        <div className={`search-fields ${!round ? "oneway" : ""}`}>
          <AirportInput label="FROM" value={origin} onChange={setOrigin} />
          <button
            className="swap-button"
            type="button"
            aria-label="Swap origin and destination"
            onClick={() => {
              setOrigin(dest);
              setDest(origin);
            }}
          >
            <ArrowDownUp size={15} />
          </button>
          <AirportInput label="TO" value={dest} onChange={setDest} />
          <div className="date-field">
            <label htmlFor="depart-date">DEPARTURE</label>
            <input
              id="depart-date"
              type="date"
              required
              value={date}
              min={format(new Date(), "yyyy-MM-dd")}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          {round && (
            <div className="date-field">
              <label htmlFor="return-date">RETURN</label>
              <input
                id="return-date"
                type="date"
                required
                value={back}
                min={format(
                  addDays(new Date(date + "T12:00:00"), 1),
                  "yyyy-MM-dd",
                )}
                onChange={(e) => setBack(e.target.value)}
              />
            </div>
          )}
          <button className="button primary search-submit" disabled={waiting}>
            {waiting ? (
              <Spinner label="Searching" />
            ) : (
              <>
                <Search size={17} />
                Find my flight
              </>
            )}
          </button>
        </div>
      </form>
      <ErrorNotice error={error || query.error} />
      {(waiting || searchId) && (
        <section className="search-main" aria-label="Flight search results">
          <div className="results-heading">
            <h2>Your flight shortlist</h2>
            {searchId && !waiting && (
              <label className="sort-select">
                <span className="sr-only">Sort results</span>
                <select
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value);
                    setAll(true);
                  }}
                >
                  <option value="best">Best match</option>
                  <option value="price">Lowest fare</option>
                  <option value="fastest">Shortest journey</option>
                </select>
              </label>
            )}
          </div>
          <div className="active-preferences">
            <Badge>
              <Check size={11} />
              {appliedPrefs.cabin === "first"
                ? "First class"
                : appliedPrefs.cabin === "either"
                  ? "Business or first"
                  : "Business class"}{" "}
              · required
            </Badge>
            <Badge>
              {appliedPrefs.direct_only
                ? "Nonstop · required"
                : "Nonstop preferred"}
            </Badge>
            {appliedPrefs.airlines.length > 0 && (
              <Badge>
                {appliedPrefs.airlines.join(", ")} ·{" "}
                {appliedPrefs.airlines_required ? "required" : "preferred"}
              </Badge>
            )}
            {appliedPrefs.flexible_only && <Badge>Flexibility required</Badge>}
            <Link className="text-button" to="/preferences">
              Edit preferences
            </Link>
          </div>
          {waiting ? (
            <div className="search-loading" aria-live="polite">
              <span className="loading-orbit">
                <Plane size={26} />
              </span>
              <h3>Finding your kind of flight.</h3>
              <p>
                {query.data?.progress ||
                  "Checking routes, cabins, and the little details."}
              </p>
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          ) : searchId ? (
            <>
              <div className="result-summary">
                <span>
                  {query.data?.matching_itineraries || 0} matching itineraries
                  {query.data?.total_offers
                    ? ` from ${query.data.total_offers} airline offers`
                    : ""}
                </span>
                <span>
                  {query.data?.live_mode
                    ? "Live airline inventory"
                    : session.account.is_demo
                      ? "Demonstration fares"
                      : "Duffel test inventory"}
                </span>
              </div>
              {query.data?.status === "failed" ? (
                <Empty title="A little turbulence." icon={<Plane />}>
                  <p>{query.data.error}</p>
                  <button className="button primary" onClick={() => search()}>
                    Try again
                  </button>
                </Empty>
              ) : !results.length ? (
                <Empty
                  title="Let’s make a little room."
                  icon={<SlidersHorizontal />}
                >
                  <p>
                    No flights met every requirement. Your preferences haven’t
                    been changed.
                  </p>
                  <div className="adjustments">
                    {query.data?.adjustments.map((a) => (
                      <button
                        key={a}
                        className="button secondary"
                        onClick={() => {
                          const p = { ...appliedPrefs };
                          if (a === "Allow mixed cabins")
                            p.allow_mixed_cabin = true;
                          else if (a === "Allow a connection")
                            p.direct_only = false;
                          else if (a.includes("airline"))
                            p.airlines_required = false;
                          else if (a.includes("aircraft"))
                            p.aircraft_required = false;
                          else if (a.includes("departure"))
                            p.time_required = false;
                          else if (a.includes("flexibility"))
                            p.flexible_only = false;
                          setPrefs(p);
                          search(undefined, p);
                        }}
                      >
                        {a}
                        <ArrowRight size={13} />
                      </button>
                    ))}
                  </div>
                  {query.data && (
                    <p className="fine-print">
                      {Object.entries(query.data.exclusions)
                        .map(
                          ([k, n]) =>
                            `${n} excluded by ${k.replaceAll("_", " ")}`,
                        )
                        .join(" · ")}
                    </p>
                  )}
                </Empty>
              ) : (
                <>
                  {(all ? results : results.slice(0, 3)).map((o) => (
                    <FlightCard
                      key={o.id}
                      offer={o}
                      canBook={
                        o.card_eligible &&
                        (session.account.is_demo ||
                          (session.features.checkout &&
                            (!o.live_mode || session.features.live_checkout)))
                      }
                      selected={compared.includes(o.id)}
                      onCompare={() => compare(o)}
                      onBook={book}
                      searchId={searchId}
                    />
                  ))}
                  {(query.data?.matching_itineraries || 0) > 3 && (
                    <button
                      className="button secondary full more-results"
                      onClick={() => setAll((v) => !v)}
                    >
                      {all
                        ? "Show the shortlist"
                        : `Browse all ${query.data?.matching_itineraries} matching itineraries`}
                      <ChevronRight size={15} />
                    </button>
                  )}
                  {all && nextCursor != null && (
                    <button
                      className="button secondary full"
                      disabled={loadingMore}
                      onClick={loadMore}
                    >
                      {loadingMore ? (
                        <Spinner label="Loading more flights" />
                      ) : (
                        <>
                          Load more itineraries <Plus size={14} />
                        </>
                      )}
                    </button>
                  )}
                  <p className="coverage-note">{query.data?.coverage}</p>
                </>
              )}
            </>
          ) : null}
        </section>
      )}
      {compared.length > 0 && (
        <div className="compare-bar">
          <span>
            <b>{compared.length}</b> of 3 flights selected
          </span>
          <button className="text-button" onClick={() => setCompared([])}>
            Clear
          </button>
          <button
            className="button primary"
            onClick={() => setComparisonOpen(true)}
          >
            Compare flights <ArrowRight size={15} />
          </button>
        </div>
      )}
      <Modal
        open={comparisonOpen}
        onOpenChange={setComparisonOpen}
        title="A closer look"
        description="Compare the details that matter to you."
        wide
      >
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Itinerary</th>
                {results
                  .filter((o) => compared.includes(o.id))
                  .map((o) => (
                    <th key={o.id}>{o.slices[0].segments[0].airline_name}</th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {[
                "Total fare",
                "Journey time",
                "Stops",
                "Cabin",
                "Changes",
                "Refunds",
              ].map((label, index) => (
                <tr key={label}>
                  <th>{label}</th>
                  {results
                    .filter((o) => compared.includes(o.id))
                    .map((o) => (
                      <td key={o.id}>
                        {
                          [
                            money(o.total_amount, o.currency),
                            duration(
                              o.slices.reduce(
                                (n, s) => n + s.duration_minutes,
                                0,
                              ),
                            ),
                            o.slices
                              .map((s) =>
                                s.stops === 0 ? "Nonstop" : `${s.stops} stop`,
                              )
                              .join(" / "),
                            [
                              ...new Set(
                                o.slices.flatMap((s) =>
                                  s.segments.map(
                                    (g) =>
                                      g.cabin_name || g.cabin || "Unconfirmed",
                                  ),
                                ),
                              ),
                            ].join(", "),
                            o.change.allowed === true
                              ? "Permitted · see fare rules"
                              : o.change.allowed === false
                                ? "Not permitted"
                                : "Not provided",
                            o.refund.allowed === true
                              ? "Permitted · see fare rules"
                              : o.refund.allowed === false
                                ? "Not permitted"
                                : "Not provided",
                          ][index]
                        }
                      </td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Modal>
    </div>
  );
}
