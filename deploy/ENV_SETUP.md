# Environment setup checklist (once you have real accounts)

## 1. Supabase

1. Create a new Supabase project.
2. Run `db/migrations/0001` through `0005` in order via the SQL editor (or `supabase db execute -f <file>` with the CLI).
3. Confirm the `avatars` Storage bucket exists (created by `0005_storage_bucket.sql`) and is public.
4. Copy **Project URL** and **service_role key** (Settings → API) — these go to the backend only, never the frontend.
5. Optionally run `db/seed/seed_dev.sql` against a **dev** project only — never against production.

## 2. Render (backend)

1. New Web Service → connect this repo → root directory `backend`.
2. Render should pick up `deploy/render.yaml`; otherwise set manually:
   - Build: `pip install pdm && pdm install --prod --no-editable`
   - Start: `pdm run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
3. Set env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET` (generate a long random string, e.g. `openssl rand -hex 32`), `CORS_ORIGINS` (your Cloudflare Pages URL).
4. Note the Render URL once deployed — you'll need it for the frontend's `VITE_API_BASE_URL`.

## 3. Cloudflare Pages (frontend)

See `deploy/cloudflare/README.md`. Set `VITE_API_BASE_URL` to the Render URL from step 2.

## 4. cron-job.org (anti cold-start)

Render's free tier sleeps after 15 minutes of no traffic. Create a cron-job.org job pinging `https://<your-render-url>/health` every 10 minutes to keep it warm.

## 5. First admin login

Generate a bcrypt hash for your real admin password:

```bash
cd backend
pdm run python3 -c "from app.security import hash_password; print(hash_password('YOUR_REAL_PASSWORD'))"
```

Insert it directly into the `admins` table via the Supabase SQL editor — there's no public admin-signup endpoint by design.

## 6. Club settings

Log in to `/admin/settings` and set the real PromptPay ID and default rate per hour — these are never hardcoded in the repo.
