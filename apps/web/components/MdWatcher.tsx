import { useEffect, useState } from "react";

interface WatcherStatus {
  enabled: boolean;
  path: string | null;
  state: "idle" | "syncing";
  last_synced_at: string | null;
  urls_found: number;
  sync_progress: { current: number; total: number };
  new_job_ids: string[];
}

interface Props {
  onNewJobIds: (ids: string[]) => void;
  onJobsChanged: () => void | Promise<void>;
}

const EMPTY_STATUS: WatcherStatus = {
  enabled: false,
  path: null,
  state: "idle",
  last_synced_at: null,
  urls_found: 0,
  sync_progress: { current: 0, total: 0 },
  new_job_ids: [],
};

export default function MdWatcher({ onNewJobIds, onJobsChanged }: Props) {
  const [status, setStatus] = useState<WatcherStatus>(EMPTY_STATUS);
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    try {
      const res = await fetch("/api/watcher/status");
      const json = await res.json();
      const next = (json.data ?? EMPTY_STATUS) as WatcherStatus;
      setStatus(next);
      onNewJobIds(next.new_job_ids ?? []);
    } catch {
      setError("Watcher unavailable");
    }
  }

  useEffect(() => {
    loadStatus();
    const interval = window.setInterval(loadStatus, 5000);
    return () => window.clearInterval(interval);
  }, []);

  async function handleSavePath() {
    setError(null);
    try {
      const res = await fetch("/api/watcher/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const json = await res.json();
      setStatus(json.data ?? EMPTY_STATUS);
    } catch {
      setError("Could not save watcher path");
    }
  }

  async function handleSync() {
    setError(null);
    try {
      const res = await fetch("/api/watcher/sync", { method: "POST" });
      const json = await res.json();
      const next = (json.data ?? EMPTY_STATUS) as WatcherStatus;
      setStatus(next);
      onNewJobIds(next.new_job_ids ?? []);
      await onJobsChanged();
    } catch {
      setError("Could not sync markdown watcher");
    }
  }

  const progress =
    status.sync_progress.total > 0
      ? (status.sync_progress.current / status.sync_progress.total) * 100
      : 0;

  return (
    <div className={`card card--immersive watcher-card${status.state === "syncing" ? " watcher-card--syncing" : ""}`}>
      <div className="card__header">
        <div>
          <span className="card__title">Markdown Watcher</span>
          <h3 style={{ marginTop: "0.35rem", fontSize: "1.1rem" }}>
            Sync a local markdown file into the job intake stream
          </h3>
        </div>
        <div className="drawer__actions" style={{ marginTop: 0 }}>
          <span className={`watcher-dot watcher-dot--${status.state}`} />
          <span style={{ color: "var(--text-muted)" }}>{status.state}</span>
        </div>
      </div>

      <div className="form-grid">
        <label className="form-field form-field--full">
          <span>Markdown file path</span>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder={status.path ?? "/Users/you/Documents/jobs.md"}
          />
        </label>
      </div>

      <div className="console-actions">
        <span className="console-hint">
          {status.path ? `Current path: ${status.path}` : "No markdown file configured yet"}
        </span>
        <div className="drawer__actions" style={{ marginTop: 0 }}>
          <button className="btn btn-ghost" onClick={handleSavePath} disabled={!path.trim()}>
            Save Path
          </button>
          <button className="btn btn-primary" onClick={handleSync}>
            Sync Now
          </button>
        </div>
      </div>

      <div className="progress-bar">
        <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="info-grid">
        <div className="info-card">
          <span className="section-label">URLs found</span>
          <p>{status.urls_found}</p>
        </div>
        <div className="info-card">
          <span className="section-label">Last synced</span>
          <p>{status.last_synced_at ? new Date(status.last_synced_at).toLocaleString() : "Never"}</p>
        </div>
        <div className="info-card">
          <span className="section-label">New jobs</span>
          <p>{status.new_job_ids.length}</p>
        </div>
      </div>

      {error && <p className="console-error">{error}</p>}
    </div>
  );
}
