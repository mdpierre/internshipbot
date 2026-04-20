import { useCallback, useEffect, useState } from "react";
import JobDrawer, { Job } from "../components/JobDrawer";
import MdWatcher from "../components/MdWatcher";

interface Stats { total: number; greenhouse: number; lever: number; unknown: number; }
interface BulkResult { url: string; success: boolean; job?: Job; skipped?: boolean; error?: string; }

function parseUrls(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("http"));
}

export default function Home() {
  const [urlText, setUrlText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [newJobIds, setNewJobIds] = useState<string[]>([]);

  const urls = parseUrls(urlText);

  async function fetchStats() {
    try {
      const res = await fetch("/api/jobs/stats");
      if (res.ok) setStats(await res.json());
    } catch { /* ignore */ }
  }

  const fetchRecentJobs = useCallback(async () => {
    try {
      const res = await fetch("/api/jobs?limit=20");
      const json = await res.json();
      if (!json.error) setJobs(json.data ?? []);
    } catch { /* ignore */ }
    setLoadingJobs(false);
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRecentJobs();
  }, [fetchRecentJobs]);

  async function handleScrape() {
    if (urls.length === 0) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls }),
      });
      const results: BulkResult[] = await res.json();
      const created = results
        .filter((r) => r.success && r.job && !r.skipped)
        .map((r) => r.job!);
      const errors = results.filter((r) => !r.success);

      if (errors.length > 0) {
        setSubmitError(
          `${errors.length} URL(s) failed. ${created.length} added successfully.`
        );
      }
      if (created.length > 0) {
        setJobs((prev) => [...created, ...prev].slice(0, 20));
        await fetchStats();
        setUrlText("");
      }
    } catch {
      setSubmitError("Request failed. Is the API running?");
    } finally {
      setSubmitting(false);
    }
  }

  const STAT_ITEMS = [
    { label: "Total",      value: stats?.total      ?? "—", color: "var(--accent-purple)" },
    { label: "Greenhouse", value: stats?.greenhouse  ?? "—", color: "var(--success)" },
    { label: "Lever",      value: stats?.lever       ?? "—", color: "var(--accent)" },
    { label: "Unknown",    value: stats?.unknown     ?? "—", color: "var(--text-muted)" },
  ];
  const weekDots = Array.from({ length: 72 }, (_, index) => index < Math.min(jobs.length * 4, 28));

  return (
    <div className="dashboard-grid">
      <section className="control-room">
        <div className="control-room__tabs">
          <span className="control-room__tab control-room__tab--muted">My pipeline</span>
          <span className="control-room__tab control-room__tab--active">Office</span>
          <span className="control-room__tab">Factory</span>
        </div>

        <div className="control-room__body">
          <aside className="control-side">
            <div className="metric-card metric-card--feature">
              <span>Available energy</span>
              <strong>{stats?.total ? `${Math.min(99, stats.total * 11)}%` : "83%"}</strong>
              <small>system readiness</small>
            </div>

            {STAT_ITEMS.map((item) => (
              <div key={item.label} className="metric-card">
                <span>{item.label}</span>
                <strong style={{ color: item.color }}>{item.value}</strong>
                <small>tracked entities</small>
              </div>
            ))}

            <div className="metric-note">
              <p>Run applications after 8 PM to reduce browser noise and keep the extension focused.</p>
              <small>Analysis · 5 min</small>
            </div>
          </aside>

          <div className="stage-panel">
            <div className="stage-panel__copy">
              <span className="card__title">Unified Workflow</span>
              <h2>Desktop-assisted operations for job intake, profile control, and live browser fills.</h2>
            </div>

            <div className="wireframe-room">
              <div className="wireframe-room__frame wireframe-room__frame--rear" />
              <div className="wireframe-room__frame wireframe-room__frame--front" />
              <div className="wireframe-room__line wireframe-room__line--left" />
              <div className="wireframe-room__line wireframe-room__line--right" />
              <div className="wireframe-room__line wireframe-room__line--top-left" />
              <div className="wireframe-room__line wireframe-room__line--top-right" />
              <div className="wireframe-room__desk" />
              <div className="wireframe-room__screen" />
              <div className="wireframe-room__grid" />
              <div className="wireframe-room__glow wireframe-room__glow--left" />
              <div className="wireframe-room__glow wireframe-room__glow--center" />
              <div className="wireframe-room__glow wireframe-room__glow--right" />
            </div>

            <div className="consumption-strip">
              <div className="consumption-strip__header">
                <span>Activity intensity / week</span>
                <span>Mon Tue Wed Thu Fri Sat Sun</span>
              </div>
              <div className="consumption-strip__dots">
                {weekDots.map((active, index) => (
                  <span
                    key={index}
                    className={`consumption-dot${active ? " consumption-dot--active" : ""}`}
                  />
                ))}
              </div>
            </div>
          </div>

          <aside className="signal-side">
            <div className="signal-card">
              <div>
                <span>Job intake</span>
                <strong>{urls.length > 0 ? `${urls.length} queued` : "Ready"}</strong>
              </div>
              <small>{submitting ? "Scraping..." : "Paste one or more URLs to start a run."}</small>
            </div>
            <div className="signal-card">
              <div>
                <span>Live sessions</span>
                <strong>{newJobIds.length > 0 ? `${newJobIds.length} new` : "Standby"}</strong>
              </div>
              <small>Each extension-assisted application will appear in Sessions.</small>
            </div>
            <div className="signal-card">
              <div>
                <span>Profile state</span>
                <strong>3 slots</strong>
              </div>
              <small>Profile 1, Profile 2, and Profile 3 can all be activated from the dashboard.</small>
            </div>
          </aside>
        </div>
      </section>

      <section className="dashboard-lower">
        <div className="card card--immersive">
          <div className="card__header">
            <div>
              <span className="card__title">Intake Console</span>
              <h3 style={{ fontSize: "1.1rem" }}>Add jobs to the control room</h3>
            </div>
          </div>
          <textarea
            className="url-textarea"
            placeholder={"Paste one or more job URLs (one per line)\nhttps://jobs.greenhouse.io/...\nhttps://jobs.lever.co/..."}
            value={urlText}
            onChange={(e) => setUrlText(e.target.value)}
            rows={5}
          />
          <div className="console-actions">
            <span className="console-hint">
              {urls.length > 0 ? `${urls.length} URL${urls.length > 1 ? "s" : ""} detected` : "Waiting for URLs"}
            </span>
            <button
              className="btn btn-primary"
              disabled={urls.length === 0 || submitting}
              onClick={handleScrape}
            >
              {submitting ? "Scraping…" : urls.length > 1 ? `Scrape ${urls.length} URLs` : "Scrape"}
            </button>
          </div>
          {submitError && <p className="console-error">{submitError}</p>}
        </div>

        <div className="stack-lg">
          <MdWatcher
            onNewJobIds={setNewJobIds}
            onJobsChanged={fetchRecentJobs}
          />

          <div className="card card--immersive" style={{ padding: 0, overflow: "hidden" }}>
            <div className="jobs-surface__header">
              <div>
                <span className="card__title">Recent Jobs</span>
                <h3 style={{ fontSize: "1.1rem", marginTop: "0.35rem" }}>Tracked intake stream</h3>
              </div>
            </div>
            {loadingJobs ? (
              <p style={{ padding: "1.25rem", color: "var(--text-muted)" }}>Loading…</p>
            ) : jobs.length === 0 ? (
              <p style={{ padding: "1.25rem", color: "var(--text-muted)" }}>
                No jobs yet. Paste a URL above to populate the system.
              </p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Source</th>
                    <th>Origin</th>
                    <th>Added</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => {
                    const isNew = newJobIds.includes(job.id);
                    return (
                      <tr
                        key={job.id}
                        className={`table-row-clickable${isNew ? " table-row-new" : ""}`}
                        onClick={() => setActiveJob(job)}
                      >
                        <td style={{ maxWidth: 400 }}>
                          <span className="jobs-surface__url">{job.url}</span>
                        </td>
                        <td><span className={`badge badge-${job.source}`}>{job.source}</span></td>
                        <td>
                          <span className={`badge badge-${job.source_type}`}>
                            {isNew ? `${job.source_type} · new` : job.source_type}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                          {new Date(job.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      {activeJob && (
        <JobDrawer
          job={activeJob}
          newJobIds={newJobIds}
          onClose={() => setActiveJob(null)}
          onDeleted={(id) => {
            setJobs((prev) => prev.filter((j) => j.id !== id));
            fetchStats();
          }}
        />
      )}
    </div>
  );
}
