export default function Home() {
  return (
    <div>
      <h2 style={{ marginBottom: "1rem" }}>Dashboard</h2>
      <p style={{ color: "var(--text-muted)", maxWidth: 600 }}>
        Applybot turns job posting URLs into a structured pipeline: scrape,
        normalize, apply, and review. Use the <strong>Jobs</strong> tab to view
        scraped postings or the <strong>Runs</strong> tab to track application
        attempts.
      </p>
    </div>
  );
}
