# นิดเดียว Badminton Club — Web App

Badminton club management app: public member list / ranking / hall of fame / match history, plus an Admin panel for billing (PromptPay QR) and ELO-based matchmaking.

See [`ISSUE_beerminton_webapp.md`](./ISSUE_beerminton_webapp.md) for the full spec and decisions log.

## Stack

- **Frontend**: Vue 3 + TypeScript + Vite + TailwindCSS + PWA — `frontend/`
- **Backend**: FastAPI + Python (PDM) — `backend/`
- **Database**: Supabase (Postgres + Storage) — SQL migrations in `db/migrations/`
- **Deploy**: Cloudflare Pages (frontend) + Render (backend) — configs in `deploy/`

The frontend **never** talks to Supabase directly — all data access goes through the FastAPI backend, which holds the Supabase service-role key.

## Local development

### Backend

```bash
cd backend
pdm install
cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, JWT_SECRET
pdm run uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Health check: `GET /health`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Frontend runs at `http://localhost:5173`.

### Database

Apply `db/migrations/*.sql` in order via the Supabase SQL editor or `supabase db execute`. Optionally load `db/seed/seed_dev.sql` for local dev fixtures.

## Deploy

Not yet deployed — see `deploy/ENV_SETUP.md` for what to configure once Supabase / Render / Cloudflare Pages accounts exist.
