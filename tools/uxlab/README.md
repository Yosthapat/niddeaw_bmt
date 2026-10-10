# uxlab

Runs the real backend against an in-memory database so the UI can be driven
and photographed without a Supabase project, a network, or a real club night.
Used by the `critic-ux` skill, and handy on its own for checking a change by
hand.

Nothing here is deployed. `lab.py` imports the real `app.main`, so every
route, guard and calculation is the production one — only the database
underneath is a stand-in (`minisupabase.py`, a small PostgREST emulator:
filters, inserts, updates, deletes and column projection all apply).

## Running it

```bash
# 1. the API, seeded with a club night in progress
python tools/uxlab/lab.py          # http://127.0.0.1:5399, admin / uxlab

# 2. a build that talks to it instead of production
VITE_API_BASE_URL=http://127.0.0.1:5399 npm --prefix frontend run build

# 3. every screen, logged in, at phone width
python tools/uxlab/shoot.py --width 430 --out /tmp/ux
python tools/uxlab/shoot.py --width 1280 --height 900 --out /tmp/ux-desktop
```

`lab.py` needs the backend's own environment (`backend/.venv`); `shoot.py`
needs `playwright` and a Chromium (`UXLAB_CHROMIUM` to point at one).

`GET /__uxlab/state` returns every table, so a check can assert on what was
stored rather than only on what was drawn.

## Rebuilding for production afterwards

The build in step 2 is pointed at localhost. Before deploying anything,
rebuild normally:

```bash
npm --prefix frontend run build
```
