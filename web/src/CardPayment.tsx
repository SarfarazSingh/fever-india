import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DuffelCardForm,
  createThreeDSecureSession,
  useDuffelCardFormActions,
} from "@duffel/components";
import { api, money, post, type Checkout } from "./api";
import { ErrorNotice, Spinner } from "./components";

export default function CardPayment({
  checkout,
  accepted,
  setAccepted,
  onPay,
  onPrice,
  onError,
  busy,
}: {
  checkout: Checkout;
  accepted: boolean;
  setAccepted: (v: boolean) => void;
  onPay: (card: string, session: string) => Promise<void>;
  onPrice: (v: Checkout) => void;
  onError: (e: unknown) => void;
  busy: boolean;
}) {
  const key = useQuery({
    queryKey: ["card-key", checkout.id],
    queryFn: () =>
      post<{ component_client_key: string }>(
        "/checkout-sessions/" + checkout.id + "/component-key",
      ),
  });
  const { ref, createCardForTemporaryUse } = useDuffelCardFormActions();
  const [cardId, setCardId] = useState("");
  const [valid, setValid] = useState(false);
  const [working, setWorking] = useState(false);
  async function cardCreated(card: { id: string }) {
    setWorking(true);
    try {
      const priced = await post<Checkout>(
        "/checkout-sessions/" + checkout.id + "/price",
        { card_id: card.id },
      );
      setCardId(card.id);
      onPrice(priced);
    } catch (e) {
      onError(e);
    } finally {
      setWorking(false);
    }
  }
  async function pay() {
    if (!key.data || !cardId || !accepted) return;
    setWorking(true);
    try {
      const auth = await createThreeDSecureSession(
        key.data.component_client_key,
        cardId,
        checkout.offer.id,
        [],
        true,
      );
      if (auth.status !== "ready_for_payment")
        throw new Error(
          "Card authentication did not complete. Please try again.",
        );
      await onPay(cardId, auth.id);
    } catch (e) {
      onError(e);
    } finally {
      setWorking(false);
    }
  }
  if (key.isPending) return <Spinner label="Opening secure card form" />;
  if (!key.data) return <ErrorNotice error={key.error} />;
  return (
    <div className="card-payment">
      <p className="muted">
        Card details are collected securely by Duffel. We don’t receive or store
        your card number.
      </p>
      {!cardId ? (
        <>
          <DuffelCardForm
            clientKey={key.data.component_client_key}
            ref={ref}
            intent="to-create-card-for-temporary-use"
            onValidateSuccess={() => setValid(true)}
            onValidateFailure={() => setValid(false)}
            onCreateCardForTemporaryUseSuccess={cardCreated}
            onCreateCardForTemporaryUseFailure={() =>
              onError(
                new Error(
                  "Could not validate the card. Please check its details.",
                ),
              )
            }
          />
          <button
            className="button primary full"
            disabled={!valid || working}
            onClick={() => createCardForTemporaryUse()}
          >
            Review final card price
          </button>
        </>
      ) : (
        <>
          <div className="review-note">
            Your final total, including applicable card fees, is{" "}
            {money(checkout.offer.total_amount, checkout.offer.currency)}.
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
            />
            I accept this total, itinerary, and fare conditions and authorize
            the purchase.
          </label>
          <button
            className="button primary full"
            disabled={!accepted || busy || working}
            onClick={pay}
          >
            {working || busy ? (
              <Spinner label="Authenticating & confirming" />
            ) : (
              "Pay & book · " +
              money(checkout.offer.total_amount, checkout.offer.currency)
            )}
          </button>
        </>
      )}
    </div>
  );
}
