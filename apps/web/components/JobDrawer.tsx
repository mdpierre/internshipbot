import { useState } from "react";

export interface Job {
  id: string;
  url: string;
  source: string;
  source_type: string;
  extracted_text: string | null;
  parsed_json: Record<string, unknown> | null;
  status: string;
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
  const [deleting, setDeleting] = useState(false);
  const isNew = newJobIds.includes(job.id);

  async function handleDelete() {
    setDeleting(true);
    try {
      const res = await fetch(`/api/jobs/${job.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
      onDeleted(job.id);
      onClose();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer__header">
          <div>
            <span className="card__title">Job Detail</span>
            <h3 style={{ marginTop: "0.4rem", fontSize: "1.1rem", maxWidth: 760 }}>{job.url}</h3>
          </div>
          <button className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="drawer__meta">
          <span className={`badge badge-${job.source}`}>{job.source}</span>
          <span className={`badge badge-${job.source_type}`}>
            {isNew ? `${job.source_type} · new` : job.source_type}
          </span>
          <span className="status-pill">{job.status}</span>
        </div>

        <div className="drawer__text">
          {job.extracted_text?.trim() ? (
            job.extracted_text
          ) : (
            "No extracted text is available for this job yet."
          )}
        </div>

        <div className="drawer__actions">
          <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete Job"}
          </button>
          <span style={{ color: "var(--text-faint)", fontSize: "0.8rem" }}>
            Added {new Date(job.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </>
  );
}
