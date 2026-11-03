import { useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarDays,
  ChevronDown,
  Compass,
  LogOut,
  Luggage,
  Plane,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import {
  api,
  post,
  setCsrf,
  type Session,
  type PublicConfig,
  type GoogleStart,
} from "./api";
import { ErrorNotice, Spinner } from "./components";
import SearchPage from "./SearchPage";
import { CalendarPage, TripDetail, TripsPage } from "./TripsPage";
import PreferencesPage from "./PreferencesPage";
import CheckoutPage from "./CheckoutPage";
import { SessionContext, useSession } from "./session";

export default function App() {
  const client = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        const data = await api<Session>("/auth/session");
        setCsrf(data.csrf_token);
        return data;
      } catch (e) {
        if (e && typeof e === "object" && "status" in e && e.status === 401)
          return null;
        throw e;
      }
    },
    staleTime: 5 * 60_000,
  });
  if (session.isPending)
    return (
      <div className="boot">
        <Brand />
        <Spinner label="Making room for your next journey" />
      </div>
    );
  if (!session.data)
    return (
      <Login
        onLogin={(data) => {
          setCsrf(data.csrf_token);
          client.removeQueries({
            predicate: (q) => q.queryKey[0] !== "session",
          });
          client.setQueryData(["session"], data);
        }}
        error={session.error}
      />
    );
  return (
    <SessionContext.Provider value={session.data}>
      <Shell />
    </SessionContext.Provider>
  );
}

function Brand() {
  return (
    <span className="brand">
      <span className="brand-icon">
        <Plane size={20} strokeWidth={1.5} />
      </span>
      elsewhere<span className="brand-period">.</span>
    </span>
  );
}

function Shell() {
  const routeLocation = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [routeLocation.pathname]);
  const session = useSession();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [menu, setMenu] = useState(false);
  const [error, setError] = useState<unknown>();
  async function logout() {
    try {
      await post("/auth/logout");
      setCsrf("");
      sessionStorage.clear();
      client.clear();
      navigate("/");
      location.reload();
    } catch (e) {
      setError(e);
    }
  }
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <NavLink
          to="/search"
          className="personal-brand"
          aria-label="Federico’s travel desk home"
        >
          <Brand />
          <span>{session.profile.first_name || "Federico"}’s travel desk</span>
        </NavLink>
        <nav className="primary-nav" aria-label="Main navigation">
          <NavLink
            to={sessionStorage.getItem("lastSearch") || "/search"}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <Compass size={16} />
            Search flights
          </NavLink>
          <NavLink to="/trips">
            <Luggage size={16} />
            My trips
          </NavLink>
          <NavLink to="/calendar">
            <CalendarDays size={16} />
            Calendar
          </NavLink>
          <NavLink to="/preferences">
            <Settings2 size={16} />
            Preferences
          </NavLink>
        </nav>
        <div className="profile-menu">
          <button
            className="profile-button"
            aria-expanded={menu}
            aria-controls="profile-options"
            onClick={() => setMenu((v) => !v)}
          >
            <span className="avatar">
              {(session.profile.first_name || "F").slice(0, 1)}
            </span>
            <span>{session.profile.first_name || "Your account"}</span>
            <ChevronDown size={13} />
          </button>
          {menu && (
            <>
              <button
                aria-label="Close profile menu"
                className="menu-scrim"
                onClick={() => setMenu(false)}
              />
              <div id="profile-options" className="profile-options">
                <NavLink to="/preferences" onClick={() => setMenu(false)}>
                  <Settings2 size={16} />
                  Preferences & connections
                </NavLink>
                <button onClick={logout}>
                  <LogOut size={16} />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </header>
      {session.account.is_demo && (
        <div className="demo-banner">
          <span>
            <ShieldCheck size={13} /> PRIVATE PREVIEW
          </span>{" "}
          You’re exploring fictional trips and fares. No purchase will be made.
        </div>
      )}
      <main id="main">
        <ErrorNotice error={error} />
        <Routes>
          <Route path="/search" element={<SearchPage />} />
          <Route path="/trips" element={<TripsPage />} />
          <Route path="/trips/:tripId" element={<TripDetail />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/preferences" element={<PreferencesPage />} />
          <Route path="/checkout/:checkoutId" element={<CheckoutPage />} />
          <Route path="*" element={<Navigate to="/search" replace />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <span>
          <ShieldCheck size={13} /> {session.profile.first_name || "Federico"}’s
          private travel concierge
        </span>
        <p>elsewhere.</p>
      </footer>
    </>
  );
}

function Login({
  onLogin,
  error: initialError,
}: {
  onLogin: (s: Session) => void;
  error?: unknown;
}) {
  const config = useQuery({
    queryKey: ["config"],
    queryFn: () => api<PublicConfig>("/config"),
  });
  const [busy, setBusy] = useState(false);
  const authMessages: Record<string, string> = {
    cancelled:
      "Google sign-in was cancelled. You can try again when you’re ready.",
    expired: "Your sign-in attempt expired. Please start again.",
    not_invited:
      "This Google account isn’t invited. Choose your invited account.",
    failed: "We couldn’t complete Google sign-in. Please try again.",
  };
  const callbackError = new URLSearchParams(window.location.search).get(
    "auth_error",
  );
  const [error, setError] = useState<unknown>(
    initialError ||
      (callbackError
        ? new Error(authMessages[callbackError] || authMessages.failed)
        : undefined),
  );
  async function demo() {
    setBusy(true);
    setError(undefined);
    try {
      onLogin(await post<Session>("/auth/demo"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function googleSignIn() {
    setBusy(true);
    setError(undefined);
    try {
      const data = await post<GoogleStart>("/auth/google/start");
      location.assign(data.url);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <div className="login-content">
        <Brand />
        <div className="login-copy">
          <span className="eyebrow">
            <span className="little-line" /> FEDERICO’S PRIVATE TRAVEL DESK
          </span>
          <h1>
            Welcome back,
            <br />
            <span>Federico.</span>
          </h1>
          <p>Your next journey starts with the right flight.</p>
          <div className="login-form">
            <div className="login-form-title">
              <ShieldCheck size={17} />A private space, just for you.
            </div>
            {config.data?.login_methods.includes("google") && (
              <>
                <button
                  className="button secondary full google-sign-in"
                  disabled={busy}
                  onClick={googleSignIn}
                >
                  {busy ? (
                    <Spinner label="Opening Google" />
                  ) : (
                    <>
                      <span className="google-letter" aria-hidden="true">
                        G
                      </span>
                      Continue with Google
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
                <p className="fine-print">
                  Use your invited Google account. Sign-in doesn’t connect your
                  mailbox.
                </p>
              </>
            )}
            {config.data?.demo_available && (
              <>
                <button
                  className="button primary full"
                  disabled={busy}
                  onClick={demo}
                >
                  {busy ? (
                    <Spinner label="Preparing your concierge" />
                  ) : (
                    <>
                      Explore the private preview <ArrowRight size={17} />
                    </>
                  )}
                </button>
                <p className="fine-print">
                  Explore sample flights and trips. No email or payment needed.
                </p>
              </>
            )}
            {!config.data?.demo_available &&
              !config.data?.login_available &&
              !config.isPending &&
              !config.isError && (
                <p>
                  Private sign-in is being configured. Please contact your
                  concierge for access.
                </p>
              )}
            <ErrorNotice error={error || config.error} />
            {!!(error || config.error) && (
              <button
                className="button secondary full"
                onClick={() => location.reload()}
              >
                Reconnect
              </button>
            )}
          </div>
        </div>
        <p className="login-footer">PRIVATE. PERSONAL. READY WHEN YOU ARE.</p>
      </div>
    </div>
  );
}
