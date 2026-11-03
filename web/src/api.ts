import type { components } from "./generated/api";

export type Profile = Required<components["schemas"]["Profile"]>;
export type PublicConfig = components["schemas"]["PublicConfig"];
export type GoogleStart = components["schemas"]["GoogleStart"];
export type Offer = Required<components["schemas"]["Offer"]>;
export type Segment = components["schemas"]["Segment"];
export type Slice = components["schemas"]["Slice"];
export type SearchRequest = Omit<
  components["schemas"]["SearchRequest"],
  "preferences"
> & { preferences: Profile };
export type SearchResponse = Omit<
  Required<components["schemas"]["SearchResponse"]>,
  "results" | "request"
> & { results: Offer[]; request: SearchRequest };
export type TripData = components["schemas"]["TripData"];
export type Passenger = components["schemas"]["Passenger"];
export type Trip = TripData & {
  id: string;
  title: string;
  status: string;
  source: string;
  is_demo: boolean;
  departure_at: string;
  created_at: string;
  origin: string;
  destination: string;
  destination_city: string;
  manage_url?: string;
};
export type Session = {
  csrf_token: string;
  account: { id: string; email: string; is_demo: boolean };
  profile: Profile;
  features: {
    demo: boolean;
    checkout: boolean;
    live_checkout: boolean;
    gmail: boolean;
    forwarding: boolean;
    places: boolean;
    notifications?: boolean;
  };
};
export type Checkout = {
  id: string;
  offer: Offer;
  quote_hash: string;
  expires_at: string;
  state: string;
  trip_id?: string;
  provider_order_id?: string;
  is_demo: boolean;
  message?: string;
  price_changed: boolean;
};
export type CalendarEvent = {
  id: string;
  trip_id: string;
  title: string;
  date: string;
  departure_at: string;
  arrival_at: string;
  departure_local: string;
  arrival_local: string;
  timezone: string;
  destination_timezone: string;
  references: string[];
};
export type Draft = {
  id: string;
  data: TripData;
  issues: string[];
  source?: string;
};
export type Connection = {
  gmail: { status: string; last_synced_at?: string; configured: boolean };
  forwarding_address?: string;
};
export type Place = {
  name: string;
  area: string;
  reason: string;
  url: string;
  verification: string;
  rating?: number;
  hotel_stars?: number;
  classification?: string;
  sources?: string[];
  attributions?: { displayName?: string; uri?: string }[];
};
export type Guide = {
  city: string;
  note: string;
  hotels: Place[];
  restaurants: Place[];
  activities: Place[];
  is_demo: boolean;
};

let csrfToken = "";
export function setCsrf(value: string) {
  csrfToken = value;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
      ...options.headers,
    },
  });
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(
      response.status,
      "The service is temporarily unavailable. Please try again.",
    );
  }
  if (!response.ok) {
    const message =
      typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? body.detail
              .map((x: { msg: string }) => x.msg.replace("Value error, ", ""))
              .join(". ")
          : "This request could not be completed";
    throw new ApiError(response.status, message);
  }
  return body as T;
}
export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
export const money = (amount: string | number, currency = "USD") =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
    minimumFractionDigits: Number(amount) % 1 ? 2 : 0,
  }).format(Number(amount));
export const clock = (local: string) => local.slice(11, 16);
export const duration = (minutes: number) =>
  `${Math.floor(minutes / 60)}h${minutes % 60 ? ` ${minutes % 60}m` : ""}`;
export const localDate = (
  local: string,
  options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" },
) =>
  new Intl.DateTimeFormat("en-GB", options).format(
    new Date(local.slice(0, 10) + "T12:00:00"),
  );
export const dayOffset = (departure: string, arrival: string) =>
  Math.round(
    (Date.parse(arrival.slice(0, 10)) - Date.parse(departure.slice(0, 10))) /
      86400000,
  );
export const defaultProfile: Profile = {
  first_name: "",
  last_name: "",
  home_airport: "MAD",
  cabin: "business",
  direct_only: false,
  airlines: [],
  airlines_required: false,
  aircraft: "",
  aircraft_required: false,
  depart_after: 0,
  depart_before: 24,
  time_required: false,
  flexible_only: false,
  allow_mixed_cabin: false,
  seat: "aisle",
  wants_gym: true,
  wants_spa: true,
  hotel_stars: 5,
  destination_notes: "",
  reminders: true,
};
