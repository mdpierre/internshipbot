import { useEffect, useRef, useState } from "react";

interface SyncProgress { current: number; total: number; }

interface WatcherStatus {
  enabled: boolean;
  path: string | null;
  state: "idle" | "syncing";
  last_synced_at: string | null;
  urls_found: number;
  sync_progress: SyncProgress;
  new_job_ids: string[];
}

interface Props {
  onNewJobIds: (ids: string[]) => void;
  onJobsChanged: () => void;
}

export default function MdWatcher({ onNewJobIds, onJobsChanged }: Props) {
  const [status, setStatus] = useState<WatcherStatus | null>(null);
  const [editingPath, setEditingPath] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [savingPath, setSavingPath] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prevIdsRef = useRef<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/watcher/status");
        if (!res.ok || cancelled) return;
        const data: WatcherStatus = await res.json();
        if (cancelled) return;
        setStatus(data);

        // Notify parent when new job IDs arrive that weren't there before
        const prev = new Set(prevIdsRef.current);
        const fresh = data.new_job_ids.filter((id) => !prev.has(id));
        if (fresh.length > 0) {
          onNewJobIds(data.new_job_ids);
          onJobsChanged();
        }
        prevIdsRef.current = data.new_job_ids;
      } catch {
        // Silently ignore poll failures
      }
    }

    poll();
    const interval = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [onNewJobIds, onJobsChanged]);

  async function savePath() {
    if (!pathInput.trim()) return;
    setSavingPath(true);
    setPathError(null);
    try {
      const res = await fetch("/api/watcher/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: pathInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        setPathError(err.detail ?? "Failed to update path");
        return;
      }
      const updated: WatcherStatus = await res.json();
      setStatus(updated);
      setEditingPath(false);
    } finally {
      setSavingPath(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await fetch("/api/watcher/upload", { method: "POST", body: form });
      onJobsChanged();
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const isSyncing = status?.state === "syncing";
  const pct =
    status && status.sync_progress.total > 0
      ? Math.round((status.sync_progress.current / status.sync_progress.total) * 100)
      : 0;

  return (
    <div className={`card watcher-card${isSyncing ? " watcher-card--syncing" : ""}`}>
      <div className="card__header">
        <span className="card__title">Markdown File</span>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span className={`watcher-dot watcher-dot--${isSyncing ? "syncing" : "idle"}`} />
          <span style={{ fontSize: "0.75rem", color: isSyncing ? "var(--accent-purple)" : "var(--success)" }}>
            {isSyncing ? "syncing…" : status?.enabled ? "watching" : "not configured"}
          </span>
        </div>
      </div>

      {/* Path display / editor */}
      {!editingPath ? (
        <div style={{
          background: "var(--bg-input)",
          border: "1px solid var(--border)",
          borderRadius: "6px",
          padding: "0.5rem 0.75rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.5rem",
          fontSize: "0.875rem",
        }}>
          <span style={{ color: status?.path ? "var(--text)" : "var(--text-muted)" }}>
            {status?.path ?? "No file configured"}
          </span>
          <button
            className="btn btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}
            onClick={() => { setPathInput(status?.path ?? ""); setEditingPath(true); }}
          >
            {status?.path ? "change" : "set path"}
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <input
              type="text"
              value={pathInput}
              onChange={(e) => setPathInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") savePath();
                if (e.key === "Escape") setEditingPath(false);
              }}
              placeholder="~/Documents/job-links.md"
              style={{
                flex: 1,
                background: "var(--bg-input)",
                border: "1px solid var(--accent-purple)",
                borderRadius: "6px",
                color: "var(--text)",
                fontSize: "0.875rem",
                padding: "0.5rem 0.75rem",
              }}
              autoFocus
            />
            <button className="btn btn-primary" onClick={savePath} disabled={savingPath}>
              {savingPath ? "Saving…" : "Save"}
            </button>
            <button className="btn btn-ghost" onClick={() => setEditingPath(false)}>Cancel</button>
          </div>
          {pathError && <p style={{ color: "var(--error)", fontSize: "0.8rem" }}>{pathError}</p>}
        </div>
      )}

      {/* Syncing progress */}
      {isSyncing && (
        <>
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${pct}%` }} />
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Scraping {status!.sync_progress.current} of {status!.sync_progress.total} new URLs…
          </p>
        </>
      )}

      {/* Footer */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: "0.5rem",
        fontSize: "0.8rem",
        color: "var(--text-muted)",
      }}>
        <span>
          {status?.last_synced_at
            ? `Last synced ${new Date(status.last_synced_at).toLocaleTimeString()} · ${status.urls_found} URLs found`
            : "Not yet synced"}
        </span>
        <label style={{ color: "var(--accent-purple)", cursor: "pointer" }}>
          {uploading ? "Uploading…" : "↑ upload .md file"}
          <input
            ref={fileInputRef}
            type="file"
            accept=".md"
            style={{ display: "none" }}
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>
    </div>
  );
}
