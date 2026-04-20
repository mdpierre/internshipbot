# applybot

An open-source pipeline that turns job posting URLs into a structured workflow:
scrape → normalize → (optionally) apply → log → review via dashboard.

## ⚠️ Ethical Use

This tool is for **personal, educational use only**. Automated job applications
can violate terms of service. Always review what the tool does before running it
against live sites. **Never use it to spam employers.**

## Quickstart

```bash
# 1. Clone and configure
cp .env.example .env          # edit if needed

# 2. Start Postgres + Redis
docker compose up -d

# 3. Run the API
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. Run the Dashboard
cd apps/web
npm install
npm run dev
```

Verify the API is up:

```bash
curl http://localhost:8000/health
```

## Repo Structure

```
apps/api/       FastAPI backend (routes, services, db, config)
apps/web/       Next.js dashboard (Pages Router)
docs/           Architecture docs and roadmap
profiles/       Local-only PII (gitignored)
```

See [docs/architecture.md](docs/architecture.md) for the full mental model and
[docs/roadmap.md](docs/roadmap.md) for what's planned.

## Privacy

- `.env` and `profiles/` are gitignored — no PII is ever committed.
- `.env.example` shows required variables with safe placeholders.
- All personal data (resumes, autofill profiles) stays on your machine.
