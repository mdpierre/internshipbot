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

  return (
    <div>
      {/* URL input */}
      <div className="card">
        <div className="card__header">
          <span className="card__title">Add Jobs</span>
        </div>
        <textarea
          className="url-textarea"
          placeholder={"Paste one or more job URLs (one per line)\nhttps://jobs.greenhouse.io/...\nhttps://jobs.lever.co/..."}
          value={urlText}
          onChange={(e) => setUrlText(e.target.value)}
          rows={3}
        />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "0.5rem" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {urls.length > 0 ? `${urls.length} URL${urls.length > 1 ? "s" : ""} detected` : ""}
          </span>
          <button
            className="btn btn-primary"
            disabled={urls.length === 0 || submitting}
            onClick={handleScrape}
          >
            {submitting ? "Scraping…" : urls.length > 1 ? `Scrape ${urls.length} URLs` : "Scrape"}
          </button>
        </div>
        {submitError && (
          <p style={{ color: "var(--error)", fontSize: "0.8rem", marginTop: "0.5rem" }}>{submitError}</p>
        )}
      </div>

      {/* Markdown file watcher */}
      <MdWatcher
        onNewJobIds={setNewJobIds}
        onJobsChanged={fetchRecentJobs}
      />

      {/* Stat cards */}
      <div className="stat-cards">
        {STAT_ITEMS.map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-card__value" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-card__label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Recent jobs table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)" }}>
          <span className="section-label" style={{ margin: 0 }}>Recent Jobs</span>
        </div>
        {loadingJobs ? (
          <p style={{ padding: "1rem", color: "var(--text-muted)" }}>Loading…</p>
        ) : jobs.length === 0 ? (
          <p style={{ padding: "1rem", color: "var(--text-muted)" }}>
            No jobs yet. Paste a URL above to get started.
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
                      <span style={{
                        display: "block",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        color: "var(--accent-purple)",
                      }}>
                        {job.url}
                      </span>
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
