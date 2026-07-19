# Cloudflare deployment (Workers static assets)

Cloudflare has unified Pages into the "Workers & Pages" dashboard flow,
which now deploys static sites via a `wrangler.jsonc` (Workers static
assets) instead of the old dashboard root-directory/output-directory
fields. That config lives at the **repo root**: `/wrangler.jsonc`, pointing
`assets.directory` at `./frontend/dist`.

## Dashboard setup

1. **Workers & Pages → Create → Connect to Git** → select this repo.
2. **Build command**: `cd frontend && npm install && npm run build`
   (the build must `cd` into `frontend/` itself since there's no separate
   root-directory field in this flow — the repo-root `wrangler.jsonc`
   then finds `frontend/dist` via its relative path).
3. **Deploy command**: leave as default (`npx wrangler deploy`, uses the
   repo-root `wrangler.jsonc` automatically).
4. **Environment variable**: `VITE_API_BASE_URL` = your Render backend URL
   (e.g. `https://niddeaw-bmt.onrender.com`) — must be set at **build**
   time since Vite bakes `import.meta.env.VITE_*` values in at build, not
   runtime. Look for an "Environment Variables" section on the same setup
   screen, or under **Settings → Build & deploy** after the project is
   created if it's not visible upfront.

`not_found_handling: "single-page-application"` in `wrangler.jsonc`
replaces the old `_redirects` `/* /index.html 200` trick — it's still kept
in `frontend/public/_redirects` for compatibility with the classic Pages
build path, but isn't required with this config.
