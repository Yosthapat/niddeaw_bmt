# Cloudflare Pages setup

This is a plain Vite SPA build — no Cloudflare Workers runtime needed, so
there's no `wrangler.toml` here. Configure a Pages project directly from
the Cloudflare dashboard (or `wrangler pages deploy` once you have an
account) with:

| Setting | Value |
|---|---|
| Framework preset | Vite |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `frontend/dist` |
| Environment variable | `VITE_API_BASE_URL` = your Render backend URL (e.g. `https://niddeaw-bmt-backend.onrender.com`) |

`frontend/public/_redirects` (already in the repo, copied into `dist/` on
build) handles SPA routing — `/* /index.html 200` — so refreshing on
`/admin/billing` etc. doesn't 404.

Set `VITE_API_BASE_URL` per environment (Preview vs Production) if you want
preview deploys to hit a staging backend instead of production.
