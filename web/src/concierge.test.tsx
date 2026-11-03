import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AirportInput, FlightCard } from "./components";
import {
  dayOffset,
  defaultProfile,
  money,
  type Offer,
  type Session,
} from "./api";
import App from "./App";
import { useState } from "react";
import { SearchFilters } from "./SearchFilters";

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const offer: Offer = {
  id: "demo",
  provider: "demo",
  live_mode: false,
  total_amount: "1234.56",
  currency: "EUR",
  expires_at: "2030-01-01T00:00:00Z",
  refund: { allowed: null },
  change: { allowed: false },
  fare_name: null,
  passenger_id: null,
  card_eligible: true,
  identity_documents_required: false,
  reasons: ["Premium cabin on every flight"],
  tradeoffs: ["Refund rules not provided"],
  recommendation: "Your best match",
  fare_options: [],
  slices: [
    {
      id: "out",
      duration_minutes: 420,
      stops: 0,
      segments: [
        {
          id: "1",
          origin: "JFK",
          destination: "LHR",
          origin_city: "New York",
          destination_city: "London",
          origin_timezone: "America/New_York",
          destination_timezone: "Europe/London",
          departure_at: "2026-12-10T23:00:00Z",
          arrival_at: "2026-12-11T06:00:00Z",
          departure_local: "2026-12-10T18:00:00-05:00",
          arrival_local: "2026-12-11T06:00:00+00:00",
          airline: "BA",
          airline_name: "British Airways",
          flight_number: "BA178",
          cabin: "business",
        },
      ],
    },
  ],
};

describe("flight presentation", () => {
  it("lets a traveler type several preferred airlines without losing commas", () => {
    function Form() {
      const [prefs, setPrefs] = useState(defaultProfile);
      return (
        <>
          <SearchFilters prefs={prefs} setPrefs={setPrefs} />
          <output data-testid="codes">{prefs.airlines.join("|")}</output>
        </>
      );
    }
    render(<Form />);
    const input = screen.getByLabelText("PREFERRED AIRLINES");
    fireEvent.change(input, { target: { value: "BA" } });
    fireEvent.change(input, { target: { value: "BA," } });
    expect(input).toHaveValue("BA,");
    fireEvent.change(input, { target: { value: "BA, QR" } });
    expect(screen.getByTestId("codes")).toHaveTextContent("BA|QR");
  });
  it("preserves cents and calendar-day offsets across DST", () => {
    expect(money("1234.56", "EUR")).toContain("1,234.56");
    expect(
      dayOffset("2026-10-24T23:30:00+02:00", "2026-10-25T01:30:00+01:00"),
    ).toBe(1);
  });
  it("shows actual arrival time, overnight marker, fare uncertainty, and keyboard-expandable details", () => {
    render(
      <FlightCard
        offer={offer}
        selected={false}
        onCompare={() => {}}
        onBook={() => {}}
        searchId="search"
      />,
    );
    expect(screen.getByText("18:00")).toBeInTheDocument();
    expect(screen.getByText("06:00")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Flight & fare details" }),
    );
    expect(screen.getByText("Refunds: not provided")).toBeInTheDocument();
    expect(screen.getByText("Changes: not permitted")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Flight & fare details" }),
    ).toHaveAttribute("aria-expanded", "true");
  });
  it("supports keyboard selection of an airport", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json([
        ["MAD", "Madrid", "Barajas"],
        ["LHR", "London", "Heathrow"],
      ]),
    );
    const change = vi.fn();
    render(<AirportInput label="Origin" value="MAD" onChange={change} />);
    const field = screen.getByRole("combobox", { name: "Origin" });
    fireEvent.focus(field);
    fireEvent.change(field, { target: { value: "London" } });
    await screen.findByText("Heathrow");
    fireEvent.keyDown(field, { key: "Enter" });
    expect(change).toHaveBeenCalledWith("LHR");
    expect(field).toHaveAttribute("aria-expanded", "false");
  });
});

it("enters the demo immediately after sign-in without requiring a reload", async () => {
  const session: Session = {
    csrf_token: "csrf",
    account: { id: "demo", email: "demo@example.invalid", is_demo: true },
    profile: { ...defaultProfile, first_name: "Federico" },
    features: {
      demo: true,
      checkout: true,
      live_checkout: false,
      gmail: false,
      places: false,
      forwarding: false,
    },
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    const url = String(path);
    if (url.endsWith("/auth/session")) return json({ detail: "Sign in" }, 401);
    if (url.endsWith("/config"))
      return json({
        demo_available: true,
        login_available: false,
        login_methods: [],
        environment: "development",
      });
    if (url.endsWith("/auth/demo")) return json(session);
    return json([]);
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Explore the private preview/ }),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: /Find your next flight, Federico/ }),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText(/fictional trips and fares/)).toBeInTheDocument();
  client.clear();
});

it("offers Google sign-in without a mailbox connection or email-code form", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).endsWith("/auth/session"))
      return json({ detail: "Sign in" }, 401);
    return json({
      demo_available: false,
      login_available: true,
      login_methods: ["google"],
      environment: "production",
    });
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByRole("button", { name: /Continue with Google/ }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Sign-in doesn’t connect your mailbox/),
  ).toBeInTheDocument();
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Explore the private preview/ }),
  ).not.toBeInTheDocument();
  client.clear();
});

it("shows a recoverable Google sign-in failure without exposing provider details", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    const url = String(path);
    if (url.endsWith("/auth/session")) return json({ detail: "Sign in" }, 401);
    if (url.endsWith("/auth/google/start"))
      return json({ detail: "Sign-in is temporarily unavailable" }, 503);
    return json({
      demo_available: false,
      login_available: true,
      login_methods: ["google"],
      environment: "production",
    });
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Continue with Google/ }),
  );
  expect(
    await screen.findByText("Sign-in is temporarily unavailable"),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Continue with Google/ }),
  ).toBeEnabled();
  client.clear();
});
