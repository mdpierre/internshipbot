import { useEffect, useState } from "react";

export interface Job {
  id: string;
  url: string;
  source: string;
  source_type: string;
  status: string;
  extracted_text: string | null;
  created_at: string;
  updated_at: string;
}

interface Props {
  job: Job;
  newJobIds: string[];
  onClose: () => void;
  onDeleted: (id: string) => void;
}

export default function JobDrawer({ job, newJobIds, onClose, onDeleted }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleDelete() {
    setDeleting(true);
    try {
      const res = await fetch(`/api/jobs/${job.id}`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        onDeleted(job.id);
        onClose();
      }
    } finally {
      setDeleting(false);
    }
  }

  const isNew = newJobIds.includes(job.id);

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer__header">
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
              {isNew && <span style={{ color: "var(--accent-purple)", marginRight: "0.5rem" }}>● new</span>}
              {new Date(job.created_at).toLocaleDateString("en-US", {
                year: "numeric", month: "short", day: "numeric",
              })}
            </p>
            <p style={{
              fontSize: "0.875rem",
              color: "var(--text-muted)",
              maxWidth: 600,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {job.url}
            </p>
          </div>
          <button className="btn btn-ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="drawer__meta">
          <span className={`badge badge-${job.source}`}>{job.source}</span>
          <span className={`badge badge-${job.source_type}`}>{job.source_type}</span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{job.status}</span>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ marginLeft: "auto", fontSize: "0.8rem", color: "var(--accent-purple)" }}
          >
            ↗ open job
          </a>
        </div>

        <div className="drawer__text">
          {job.extracted_text ?? (
            <span style={{ color: "var(--text-muted)" }}>No extracted text available.</span>
          )}
        </div>

        <div className="drawer__actions">
          {!confirmDelete ? (
            <button className="btn btn-danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </button>
          ) : (
            <>
              <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Really delete?</span>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? "Deleting…" : "Confirm"}
              </button>
              <button className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
