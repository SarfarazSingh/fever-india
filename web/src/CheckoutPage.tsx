import { lazy, Suspense, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  CreditCard,
  FileCheck2,
  LockKeyhole,
  Plane,
  ShieldCheck,
} from "lucide-react";
import { api, money, post, type Checkout, type Passenger } from "./api";
import {
  Badge,
  ErrorNotice,
  FareRules,
  SegmentDetails,
  SliceSummary,
  Spinner,
} from "./components";
import { useSession } from "./session";

const CardPayment = lazy(() => import("./CardPayment"));
export default function CheckoutPage() {
  const { checkoutId } = useParams();
  const client = useQueryClient();
  const session = useSession();
  const [step, setStep] = useState(0);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [outcome, setOutcome] = useState("success");
  const [passenger, setPassenger] = useState<Passenger>({
    given_name: session.profile.first_name,
    family_name: session.profile.last_name,
    email: session.account.is_demo
      ? "traveler@example.com"
      : session.account.email,
    born_on: "",
    phone_number: "",
    gender: "m",
    title: "mr",
  });
  const checkout = useQuery({
    queryKey: ["checkout", checkoutId],
    queryFn: () => api<Checkout>("/checkout-sessions/" + checkoutId),
    refetchInterval: (q) =>
      ["submitting", "confirming"].includes(q.state.data?.state || "")
        ? 4000
        : false,
  });
  const data = checkout.data;
  async function submit(cardId = "", threeDS = "") {
    if (!data) return;
    setBusy(true);
    setError(undefined);
    let attempt = sessionStorage.getItem("checkout-attempt-" + data.id);
    if (!attempt) {
      attempt = crypto.randomUUID();
      sessionStorage.setItem("checkout-attempt-" + data.id, attempt);
    }
    try {
      const result = await post<Checkout>("/orders", {
        checkout_id: data.id,
        attempt_key: attempt,
        accepted_quote_hash: data.quote_hash,
        passenger,
        card_id: cardId,
        three_d_secure_session_id: threeDS,
        demo_outcome: outcome,
      });
      client.setQueryData(["checkout", checkoutId], result);
      client.invalidateQueries({ queryKey: ["trips"] });
    } catch (e) {
      setError(e);
      await client.invalidateQueries({ queryKey: ["checkout", checkoutId] });
      setAccepted(false);
    } finally {
      setBusy(false);
    }
  }
  if (checkout.isPending)
    return (
      <div className="page standard-page">
        <Spinner label="Refreshing your flight" />
      </div>
    );
  if (!data)
    return (
      <div className="page standard-page">
        <ErrorNotice error={checkout.error} />
        <Link to="/search">Back to search</Link>
      </div>
    );
  if (["declined", "cancelled"].includes(data.state))
    return (
      <div className="page booking-result">
        <span className="booking-result-icon">
          <CreditCard size={35} />
        </span>
        <h1>
          {data.state === "cancelled"
            ? "The booking was cancelled."
            : "The booking wasn’t completed."}
        </h1>
        <p>{data.message}</p>
        <p className="muted">This attempt will not be submitted again.</p>
        <Link
          className="button primary"
          to={
            data.trip_id
              ? "/trips/" + data.trip_id
              : sessionStorage.getItem("lastSearch") || "/search"
          }
        >
          {data.trip_id ? "View itinerary" : "Return to your flights"}
          <ArrowRight size={15} />
        </Link>
      </div>
    );
  if (["confirmed", "confirming", "submitting"].includes(data.state))
    return (
      <div className="page booking-result">
        <span className="booking-result-icon">
          {data.state === "confirmed" ? (
            <CheckCircle2 size={38} />
          ) : (
            <Plane size={38} />
          )}
        </span>
        <span className="eyebrow">
          {data.is_demo ? "DEMONSTRATION BOOKING" : "YOUR JOURNEY"}
        </span>
        <h1>
          {data.state === "confirmed"
            ? "Your next chapter is ready."
            : "We’re confirming the details."}
        </h1>
        <p>{data.message}</p>
        {data.state !== "confirmed" && (
          <div className="review-note">
            Do not submit another booking. We’ll keep checking the airline
            outcome and update this screen.
          </div>
        )}
        {data.is_demo && (
          <p className="muted">
            No card was charged and no real ticket was issued.
          </p>
        )}
        {data.trip_id ? (
          <Link className="button primary" to={"/trips/" + data.trip_id}>
            View my itinerary
            <ArrowRight size={16} />
          </Link>
        ) : (
          <Link className="button secondary" to="/trips">
            Go to My Trips
          </Link>
        )}
      </div>
    );
  const set = <K extends keyof Passenger>(key: K, value: Passenger[K]) =>
    setPassenger({ ...passenger, [key]: value });
  return (
    <div className="page standard-page checkout-page">
      <Link
        className="back-link"
        to={sessionStorage.getItem("lastSearch") || "/search"}
      >
        <ArrowLeft size={15} />
        Back to your flights
      </Link>
      <div className="page-title-row">
        <div>
          <span className="eyebrow">LET’S MAKE IT A JOURNEY</span>
          <h1>A few details. Then you’re away.</h1>
        </div>
        <span className="private-label">
          <LockKeyhole size={15} />
          Secure checkout
        </span>
      </div>
      <div className="checkout-steps">
        {["Your journey", "Traveler details", "Review & payment"].map(
          (s, i) => (
            <span
              className={step === i ? "active" : step > i ? "done" : ""}
              key={s}
            >
              <b>{step > i ? <Check size={13} /> : i + 1}</b>
              {s}
            </span>
          ),
        )}
      </div>
      <div className="checkout-layout">
        <section className="settings-card checkout-main">
          {data.price_changed && (
            <div className="review-note">
              The airline updated this quote. Please review the current total
              and fare conditions before accepting again.
            </div>
          )}
          {step === 0 && (
            <>
              <h2>Your journey, considered.</h2>
              {data.offer.slices.map((s, i) => (
                <div key={s.id}>
                  <h4>{i === 0 ? "Outbound" : "Return"}</h4>
                  <SliceSummary slice={s} />
                  <SegmentDetails segments={s.segments} />
                </div>
              ))}
              <button
                className="button primary full"
                onClick={() => setStep(1)}
              >
                Traveler details
                <ArrowRight size={15} />
              </button>
            </>
          )}
          {step === 1 && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setStep(2);
              }}
            >
              <h2>Who’s traveling?</h2>
              <p className="muted">
                Use your name exactly as it appears on your travel document.
              </p>
              <div className="form-grid">
                <label>
                  First name
                  <input
                    required
                    maxLength={100}
                    autoComplete="given-name"
                    value={passenger.given_name}
                    onChange={(e) => set("given_name", e.target.value)}
                  />
                </label>
                <label>
                  Last name
                  <input
                    required
                    maxLength={100}
                    autoComplete="family-name"
                    value={passenger.family_name}
                    onChange={(e) => set("family_name", e.target.value)}
                  />
                </label>
                <label>
                  Date of birth
                  <input
                    type="date"
                    required
                    autoComplete="bday"
                    value={passenger.born_on}
                    onChange={(e) => set("born_on", e.target.value)}
                  />
                </label>
                <label>
                  Phone number
                  <input
                    type="tel"
                    required
                    pattern="\+[1-9][0-9]{6,14}"
                    autoComplete="tel"
                    placeholder="+34600123456"
                    value={passenger.phone_number}
                    onChange={(e) => set("phone_number", e.target.value)}
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={passenger.email}
                    onChange={(e) => set("email", e.target.value)}
                  />
                </label>
                <label>
                  Title
                  <select
                    value={passenger.title}
                    onChange={(e) =>
                      set("title", e.target.value as Passenger["title"])
                    }
                  >
                    {["mr", "ms", "mrs", "miss", "dr"].map((t) => (
                      <option key={t} value={t}>
                        {t.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Gender marker required by airline
                  <select
                    value={passenger.gender}
                    onChange={(e) =>
                      set("gender", e.target.value as Passenger["gender"])
                    }
                  >
                    <option value="m">Male</option>
                    <option value="f">Female</option>
                  </select>
                </label>
              </div>
              <p className="fine-print">
                The initial release supports one adult traveler. These details
                are sent to the airline only when you confirm booking.
              </p>
              <button className="button primary full">
                Review & payment
                <ArrowRight size={15} />
              </button>
              <button
                type="button"
                className="text-button"
                onClick={() => setStep(0)}
              >
                Back to journey
              </button>
            </form>
          )}
          {step === 2 && (
            <>
              <h2>The final details.</h2>
              <div className="passenger-review">
                <FileCheck2 size={20} />
                <div>
                  <b>
                    {passenger.given_name} {passenger.family_name}
                  </b>
                  <p>
                    {passenger.email} · {passenger.phone_number}
                  </p>
                </div>
                <button className="text-button" onClick={() => setStep(1)}>
                  Edit
                </button>
              </div>
              <FareRules offer={data.offer} />
              {data.state === "declined" && (
                <ErrorNotice error={data.message} />
              )}
              {data.is_demo ? (
                <>
                  <div className="demo-payment">
                    <CreditCard size={25} />
                    <div>
                      <b>Preview a booking outcome</b>
                      <p>No card information or real purchase is involved.</p>
                    </div>
                  </div>
                  <label>
                    Demo scenario
                    <select
                      value={outcome}
                      onChange={(e) => setOutcome(e.target.value)}
                    >
                      <option value="success">Successful confirmation</option>
                      <option value="declined">Payment declined</option>
                      <option value="uncertain">
                        Uncertain airline response
                      </option>
                    </select>
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={accepted}
                      onChange={(e) => setAccepted(e.target.checked)}
                    />
                    I’ve reviewed the itinerary and fare rules.
                  </label>
                  <button
                    className="button primary full"
                    disabled={!accepted || busy}
                    onClick={() => submit()}
                  >
                    {busy ? (
                      <Spinner label="Confirming" />
                    ) : (
                      <>
                        Simulate booking ·{" "}
                        {money(data.offer.total_amount, data.offer.currency)}
                        <ArrowRight size={15} />
                      </>
                    )}
                  </button>
                </>
              ) : (
                <Suspense fallback={<Spinner label="Loading secure payment" />}>
                  <CardPayment
                    checkout={data}
                    accepted={accepted}
                    setAccepted={setAccepted}
                    onPay={submit}
                    onPrice={(r) => {
                      client.setQueryData(["checkout", checkoutId], r);
                      setAccepted(false);
                    }}
                    onError={setError}
                    busy={busy}
                  />
                </Suspense>
              )}
              <button className="text-button" onClick={() => setStep(1)}>
                Back to traveler details
              </button>
            </>
          )}
          <ErrorNotice error={error} />
        </section>
        <aside className="checkout-summary info-card">
          <span className="eyebrow">YOUR ITINERARY</span>
          <h3>
            {data.offer.slices[0].segments[0].origin} <ArrowRight size={17} />
            {data.offer.slices[0].segments.at(-1)!.destination}
          </h3>
          <p>
            {data.offer.slices.length > 1
              ? "Return journey"
              : "One-way journey"}{" "}
            · 1 adult
          </p>
          <dl>
            <div>
              <dt>Flights, taxes & fees</dt>
              <dd>{money(data.offer.total_amount, data.offer.currency)}</dd>
            </div>
            <div className="total-row">
              <dt>Total</dt>
              <dd>{money(data.offer.total_amount, data.offer.currency)}</dd>
            </div>
          </dl>
          <p className="fine-print">
            No extras have been selected. Seats and additional baggage can be
            arranged with the airline where supported.
          </p>
          <span className="secure-note">
            <ShieldCheck size={16} />
            {data.is_demo
              ? "Preview · no payment collected"
              : "Card details stay with Duffel"}
          </span>
        </aside>
      </div>
    </div>
  );
}
