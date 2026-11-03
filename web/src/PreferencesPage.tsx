import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  Copy,
  ExternalLink,
  Leaf,
  Link2,
  Mail,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Unplug,
} from "lucide-react";
import { api, post, type Connection, type Profile, type Session } from "./api";
import {
  AirportInput,
  Badge,
  ErrorNotice,
  Modal,
  Spinner,
  Toggle,
} from "./components";
import { SearchFilters } from "./SearchFilters";
import { useSession } from "./session";

export default function PreferencesPage() {
  const session = useSession();
  const client = useQueryClient();
  const [profile, setProfile] = useState<Profile>(session.profile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [gmailReminders, setGmailReminders] = useState(
    !!session.features.gmail_send,
  );
  const [testEmailId, setTestEmailId] = useState<string>();
  const testEmail = useQuery({
    queryKey: ["testEmail", testEmailId],
    queryFn: () =>
      api<{ id: string; state: string; message?: string }>(
        "/notifications/" + testEmailId,
      ),
    enabled: !!testEmailId,
    refetchInterval: (q) =>
      ["queued", "sending"].includes(q.state.data?.state || "")
        ? 2000
        : q.state.data?.state === "confirming"
          ? 10000
          : false,
  });
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: () => api<Connection>("/connections"),
  });
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const p = await api<Profile>("/profile", {
        method: "PUT",
        body: JSON.stringify(profile),
      });
      client.setQueryData<Session>(["session"], (old) =>
        old ? { ...old, profile: p } : old,
      );
      setNotice("Your preferences are saved. Future searches will use them.");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function connect(sendReminders = gmailReminders) {
    setError(undefined);
    try {
      const r = await post<{ url: string }>("/connections/gmail/connect", {
        send_reminders: !!session.features.gmail_send && sendReminders,
      });
      location.assign(r.url);
    } catch (e) {
      setError(e);
    }
  }
  async function disconnect() {
    try {
      await api("/connections/gmail", { method: "DELETE" });
      client.invalidateQueries({ queryKey: ["connections"] });
      setNotice("Gmail disconnected. Imported trips remain in your account.");
    } catch (e) {
      setError(e);
    }
  }
  async function sync() {
    setBusy(true);
    try {
      const result = await post<{ more_pending?: boolean }>(
        "/connections/gmail/sync",
      );
      await client.invalidateQueries({ queryKey: ["connections"] });
      client.invalidateQueries({ queryKey: ["imports"] });
      client.invalidateQueries({ queryKey: ["trips"] });
      setNotice(
        result.more_pending
          ? "Bookings are being imported. More messages will be checked automatically; review any incomplete bookings in My Trips."
          : "Mailbox checked. Any uncertain bookings are waiting for review in My Trips.",
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function sendTestEmail() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await post<{ id: string }>("/notifications/test");
      setTestEmailId(result.id);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function deleteData() {
    try {
      await api("/account/data", { method: "DELETE" });
      client.clear();
      location.assign("/preferences");
    } catch (e) {
      setError(e);
      setDeleteOpen(false);
    }
  }
  return (
    <div className="page standard-page preferences-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">
            {session.profile.first_name || "Federico"}’S TRAVEL PROFILE
          </span>
          <h1>The way you like to travel.</h1>
          <p>Saved here. Considered in every flight search.</p>
        </div>
        <span className="private-label">
          <ShieldCheck size={15} />
          Private to your account
        </span>
      </div>
      <div className="preferences-layout">
        <form onSubmit={save}>
          <section className="settings-card">
            <div className="settings-heading">
              <span className="settings-icon">
                <Settings2 size={19} />
              </span>
              <div>
                <h2>Your traveler profile</h2>
                <p>The essentials for a more personal journey.</p>
              </div>
            </div>
            <div className="form-grid">
              <label>
                First name
                <input
                  value={profile.first_name}
                  maxLength={100}
                  autoComplete="given-name"
                  onChange={(e) =>
                    setProfile({ ...profile, first_name: e.target.value })
                  }
                />
              </label>
              <label>
                Last name
                <input
                  value={profile.last_name}
                  maxLength={100}
                  autoComplete="family-name"
                  onChange={(e) =>
                    setProfile({ ...profile, last_name: e.target.value })
                  }
                />
              </label>
            </div>
            <AirportInput
              label="HOME AIRPORT"
              value={profile.home_airport}
              onChange={(v) => setProfile({ ...profile, home_airport: v })}
            />
            <label>
              Seat preference
              <select
                value={profile.seat}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    seat: e.target.value as Profile["seat"],
                  })
                }
              >
                <option value="aisle">Aisle</option>
                <option value="window">Window</option>
                <option value="none">No preference</option>
              </select>
            </label>
            <p className="fine-print">
              A seat preference is a request. Your seat is confirmed only when
              assigned by the airline.
            </p>
          </section>
          <section className="settings-card">
            <h2>The way you like to fly</h2>
            <p className="muted">
              Requirements are enforced. Preferences help us choose the best
              fit.
            </p>
            <SearchFilters prefs={profile} setPrefs={setProfile} />
          </section>
          <section className="settings-card">
            <h2>When you get there</h2>
            <div className="form-grid">
              <label>
                Preferred hotel classification
                <select
                  value={profile.hotel_stars}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      hotel_stars: Number(e.target.value),
                    })
                  }
                >
                  {[5, 4, 3, 2, 1].map((s) => (
                    <option key={s} value={s}>
                      {s} star{s > 1 ? "s" : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <Toggle
              label="A proper gym"
              hint="Prioritize hotels with a gym"
              checked={profile.wants_gym}
              onChange={(v) => setProfile({ ...profile, wants_gym: v })}
            />
            <Toggle
              label="Room to unwind"
              hint="Prioritize hotels with a spa"
              checked={profile.wants_spa}
              onChange={(v) => setProfile({ ...profile, wants_spa: v })}
            />
            <label>
              Anything else to keep in mind?
              <textarea
                value={profile.destination_notes}
                maxLength={1000}
                rows={3}
                placeholder="Quiet neighborhoods, seafood, contemporary art…"
                onChange={(e) =>
                  setProfile({ ...profile, destination_notes: e.target.value })
                }
              />
            </label>
            <Toggle
              label="Trip reminders"
              hint={
                connections.data?.email?.ready
                  ? "An email before your journey from your connected account"
                  : "Connect Gmail with sending permission to receive reminders"
              }
              disabled={!connections.data?.email?.ready}
              checked={!!connections.data?.email?.ready && profile.reminders}
              onChange={(v) => setProfile({ ...profile, reminders: v })}
            />
          </section>
          <ErrorNotice error={error} />
          {notice && (
            <div className="success-notice inline" role="status">
              <Check size={17} />
              {notice}
            </div>
          )}
          <button className="button primary" disabled={busy}>
            {busy ? (
              <Spinner label="Saving" />
            ) : (
              <>
                Save my preferences
                <Check size={16} />
              </>
            )}
          </button>
        </form>
        <aside>
          <section className="settings-card connection-card">
            <span className="settings-icon">
              <Mail size={20} />
            </span>
            <h2>Connect your booking emails.</h2>
            <p>
              Import airline confirmations into My Trips. Incomplete details
              stay in review.
            </p>
            <div className="connection-status">
              <b>Gmail</b>
              <Badge
                tone={
                  connections.data?.gmail.status === "connected" ? "green" : ""
                }
              >
                {connections.data?.gmail.status.replaceAll("_", " ") ||
                  "Not connected"}
              </Badge>
            </div>
            {connections.isPending ? (
              <Spinner />
            ) : connections.data?.gmail.status === "connected" ? (
              <>
                <button
                  className="button primary full"
                  disabled={busy}
                  onClick={sync}
                >
                  <RefreshCw size={15} />
                  Check for bookings
                </button>
                <button className="button secondary full" onClick={disconnect}>
                  <Unplug size={15} />
                  Disconnect Gmail
                </button>
                {connections.data.gmail.sync_in_progress && (
                  <p className="fine-print">
                    Initial import is in progress. The worker continues checking
                    older messages automatically.
                  </p>
                )}
                {session.features.gmail_send &&
                  !connections.data.gmail.can_send && (
                    <button
                      className="button secondary full"
                      onClick={() => connect(true)}
                    >
                      Enable Gmail reminders
                    </button>
                  )}
                {connections.data.gmail.can_send && (
                  <>
                    <p className="fine-print">
                      Trip emails are sent from your connected Gmail account to{" "}
                      {session.account.email}.
                    </p>
                    <button
                      className="button secondary full"
                      disabled={
                        busy ||
                        ["queued", "sending"].includes(
                          testEmail.data?.state || "",
                        )
                      }
                      onClick={sendTestEmail}
                    >
                      Send a test email
                    </button>
                    {testEmail.data && (
                      <p role="status" className="fine-print">
                        {testEmail.data.state === "sent"
                          ? "Gmail accepted your test email. Check your inbox."
                          : testEmail.data.message ||
                            "Your test email is queued for delivery."}
                      </p>
                    )}
                    <ErrorNotice error={testEmail.error} />
                  </>
                )}
                {connections.data.gmail.last_synced_at && (
                  <p className="fine-print">
                    Last checked{" "}
                    {new Date(
                      connections.data.gmail.last_synced_at,
                    ).toLocaleString()}
                  </p>
                )}
              </>
            ) : (
              <>
                {session.features.gmail_send && (
                  <Toggle
                    label="Also send my trip reminders from Gmail"
                    checked={gmailReminders}
                    onChange={setGmailReminders}
                    hint="Google will ask for separate email sending permission."
                  />
                )}
                <button
                  className="button primary full"
                  onClick={() => connect()}
                  disabled={
                    !connections.data?.gmail.configured ||
                    session.account.is_demo
                  }
                >
                  <Link2 size={15} />
                  Connect Gmail
                </button>
              </>
            )}
            <p className="fine-print">
              Google asks for mailbox read access so we can find booking-related
              messages. If you choose Gmail reminders, it also asks for
              permission to send email. We do not request permission to delete
              mail. You can disconnect at any time.
            </p>
            {(!connections.data?.gmail.configured ||
              session.account.is_demo) && (
              <p className="setup-note">
                {session.account.is_demo
                  ? "Mailbox connections are disabled in the preview."
                  : "Secure Gmail authorization needs to be configured before connecting."}
              </p>
            )}
            <p className="fine-print">
              This private Google pilot may require reconnection after seven
              days.
            </p>
            <ErrorNotice error={connections.error} />
          </section>
          <section className="settings-card">
            <h3>Or send it our way.</h3>
            <p className="muted">
              Forward a confirmation to your private trip inbox.
            </p>
            {connections.data?.forwarding_address ? (
              <button
                className="forwarding-address"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(
                      connections.data!.forwarding_address!,
                    );
                    setNotice("Forwarding address copied.");
                  } catch {
                    setError(new Error("Copy the address shown above."));
                  }
                }}
              >
                {connections.data.forwarding_address}
                <Copy size={14} />
              </button>
            ) : (
              <p className="setup-note">
                Your private forwarding address will appear after inbound email
                is configured.
              </p>
            )}
            <p className="fine-print">
              Pasting a confirmation or entering a trip manually is always
              available in My Trips.
            </p>
          </section>
          <section className="concierge-note">
            <Leaf size={22} />
            <h3>Yours, by design.</h3>
            <p>
              Your preferences, itineraries, and connections belong to your
              account.
            </p>
            <button
              className="text-button danger-text"
              onClick={() => setDeleteOpen(true)}
            >
              Delete my travel data
            </button>
          </section>
        </aside>
      </div>
      <Modal
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete your travel data?"
        description="This permanently removes your trips, searches, imports, and connections from this app. It does not cancel airline bookings. Export your calendar first if you want a copy."
      >
        <button className="button danger full" onClick={deleteData}>
          Permanently delete travel data
        </button>
        <button
          className="button secondary full"
          onClick={() => setDeleteOpen(false)}
        >
          Keep my data
        </button>
      </Modal>
    </div>
  );
}
