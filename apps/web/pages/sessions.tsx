import { useEffect, useState } from "react";

type ApplicationEvent = {
  id: string;
  event_type: string;
  field_name: string | null;
  selector: string | null;
  created_at: string;
};

type ApplicationSession = {
  id: string;
  profile_slot: string;
  page_url: string;
  origin: string;
  state: string;
  final_result: string | null;
  submitted_at: string | null;
  created_at: string;
  events: ApplicationEvent[];
};

export default function SessionsPage() {
  const [sessions, setSessions] = useState<ApplicationSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/application-sessions")
      .then((res) => res.json())
      .then((json) => setSessions(json.data ?? []))
      .catch(() => setError("Could not load application sessions"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading application sessions…</p>;
  if (error) return <p style={{ color: "var(--error)" }}>{error}</p>;

  return (
    <div className="stack-lg">
      <div className="card card--immersive">
        <h2>Application Sessions</h2>
        <p style={{ color: "var(--text-muted)", marginTop: "0.4rem" }}>
          Every extension-assisted autofill attempt is tracked here so you can review the page,
          slot used, current state, and recent field activity.
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="card card--immersive">
          <p style={{ color: "var(--text-muted)" }}>
            No application sessions yet. Open a job application page and use the extension to create one.
          </p>
        </div>
      ) : (
        <div className="stack-md">
          {sessions.map((session) => (
            <div key={session.id} className="card card--immersive">
              <div className="card__header">
                <div>
                  <span className="card__title">{session.profile_slot}</span>
                  <h3 style={{ marginTop: "0.4rem", fontSize: "1rem" }}>{session.page_url}</h3>
                </div>
                <span className={`badge badge-${session.state === "completed" ? "greenhouse" : "unknown"}`}>
                  {session.state}
                </span>
              </div>
              <div className="info-grid">
                <div className="info-card">
                  <span className="section-label">Origin</span>
                  <p>{session.origin}</p>
                </div>
                <div className="info-card">
                  <span className="section-label">Result</span>
                  <p>{session.final_result ?? "Pending"}</p>
                </div>
                <div className="info-card">
                  <span className="section-label">Started</span>
                  <p>{new Date(session.created_at).toLocaleString()}</p>
                </div>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <span className="section-label">Recent Events</span>
                {session.events.length === 0 ? (
                  <p style={{ color: "var(--text-muted)", marginTop: "0.5rem" }}>No field events recorded yet.</p>
                ) : (
                  <ul className="event-list">
                    {session.events.slice(-8).map((event) => (
                      <li key={event.id}>
                        <strong>{event.event_type}</strong>
                        {event.field_name ? ` · ${event.field_name}` : ""}
                        {event.selector ? ` · ${event.selector}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
