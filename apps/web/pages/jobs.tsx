import { useEffect, useState } from "react";
import JobDrawer, { Job } from "../components/JobDrawer";

type FilterSource = "all" | "greenhouse" | "lever" | "unknown";

const TABS: { label: string; value: FilterSource }[] = [
  { label: "All", value: "all" },
  { label: "Greenhouse", value: "greenhouse" },
  { label: "Lever", value: "lever" },
  { label: "Unknown", value: "unknown" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterSource>("all");
  const [activeJob, setActiveJob] = useState<Job | null>(null);

  useEffect(() => {
    fetch("/api/jobs")
      .then((res) => res.json())
      .then((json) => {
        if (json.error) setError(json.error);
        else setJobs(json.data ?? []);
      })
      .catch(() => setError("Failed to fetch jobs"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "all" ? jobs : jobs.filter((j) => j.source === filter);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;
  if (error) return <p style={{ color: "var(--error)" }}>{error}</p>;

  return (
    <div>
      <h2 style={{ marginBottom: "1.25rem" }}>Jobs</h2>

      <div className="filter-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            className={`filter-tab${filter === tab.value ? " filter-tab--active" : ""}`}
            onClick={() => setFilter(tab.value)}
          >
            {tab.label}
            <span style={{ marginLeft: "0.4rem", color: "var(--text-muted)", fontWeight: 400 }}>
              ({tab.value === "all" ? jobs.length : jobs.filter((j) => j.source === tab.value).length})
            </span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>
          {jobs.length === 0
            ? "No jobs yet. Add some from the Home page."
            : "No jobs match this filter."}
        </p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Source</th>
                <th>Origin</th>
                <th>Status</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => (
                <tr
                  key={job.id}
                  className="table-row-clickable"
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
                  <td><span className={`badge badge-${job.source_type}`}>{job.source_type}</span></td>
                  <td style={{ color: "var(--text-muted)" }}>{job.status}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                    {new Date(job.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeJob && (
        <JobDrawer
          job={activeJob}
          newJobIds={[]}
          onClose={() => setActiveJob(null)}
          onDeleted={(id) => {
            setJobs((prev) => prev.filter((j) => j.id !== id));
            setActiveJob(null);
          }}
        />
      )}
    </div>
  );
}
