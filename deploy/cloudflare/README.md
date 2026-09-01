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
replaces the old `_redirects` `/* /index.html 200` trick — **do not** add
a `frontend/public/_redirects` file back. Having both active at once
causes a "Line 1: Infinite loop detected in this rule" deploy failure,
since the two SPA-fallback mechanisms fight each other.

## Node version

`vite@8` requires Node `^20.19.0 || >=22.12.0` and fails outright on older
runtimes. Every build since Cloudflare's default build-image Node version
fell below that (all commits after `2c4d8a1`, silently — the app kept
running on the last successful deploy while every push after it failed)
broke because of this. `.nvmrc` (repo root and `frontend/`) plus
`engines.node` in `frontend/package.json` now pin it explicitly; if builds
ever fail again with a `vite requires Node.js` message, bump those two
files' version rather than guessing at the dashboard's `NODE_VERSION`
build variable.
