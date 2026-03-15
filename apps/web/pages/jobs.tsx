import { useEffect, useState } from "react";

interface Job {
  id: string;
  url: string;
  source: string;
  status: string;
  extracted_text: string | null;
  created_at: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/jobs")
      .then((res) => res.json())
      .then((json) => {
        if (json.error) {
          setError(json.error);
        } else {
          setJobs(json.data ?? []);
        }
      })
      .catch(() => setError("Failed to fetch jobs"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;
  if (error) return <p style={{ color: "var(--error)" }}>{error}</p>;

  return (
    <div>
      <h2 style={{ marginBottom: "1rem" }}>Jobs</h2>

      {jobs.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>
          No jobs yet. POST a URL to /api/jobs to get started.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>URL</th>
              <th>Source</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      maxWidth: 400,
                      display: "inline-block",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {job.url}
                  </a>
                </td>
                <td>
                  <span className={`badge badge-${job.source}`}>
                    {job.source}
                  </span>
                </td>
                <td>{job.status}</td>
                <td style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                  {new Date(job.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
