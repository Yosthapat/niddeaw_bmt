# Service Overview

นิดเดียว Badminton Club webapp. Clone of bmbad.com's club features (member list, ranking, hall of fame, match history) plus new Admin billing (PromptPay QR) and ELO-based matchmaking. Full spec in `/ISSUE_beerminton_webapp.md`.

## Architecture

- `frontend/` — Vue 3 + TS + Vite + Tailwind v4 + PWA. **Never talks to Supabase directly** — all data access goes through the FastAPI backend. `frontend/.env.example` deliberately contains only `VITE_API_BASE_URL` as an enforceable proof of this boundary.
- `backend/` — FastAPI + PDM. Holds the Supabase service-role key (backend-only). Routers split into `routers/public/*` (unauthenticated) and `routers/admin/*` (JWT-protected via `Depends(get_current_admin)` at the router level).
- `db/migrations/` — raw SQL applied manually via Supabase SQL editor/CLI, no ORM migration tool.
- `deploy/` — Render (backend) + Cloudflare Pages (frontend) configs, not yet deployed.

## Key decisions (don't relitigate without re-reading the issue doc's "Decisions Resolved" section)

1. **No player login in Phase 1.** Public site is fully read-only. Admin does all check-in/checkout and match recording from the Admin panel.
2. **Polling, not WebSockets/Realtime**, for live screens (`usePolling` composable, 7-8s interval).
3. **Match scores as sets** (`sets: [[21,15],[18,21],[21,19]]`), `winner` always derived server-side from the sets, never trusted from the client.
4. **ELO**: flat K=32 (no provisional-K ramp — kept simple). Doubles team rating = average of the two players; the same delta is applied to both teammates (a known, documented simplification — a low-rated player benefits from a strong partner).
5. **Matchmaking fairness**: `pairing_history` table tracks teammate/opponent pairs per round; suggestion cost = ELO imbalance + fairness penalty (teammate repeats weighted higher than opponent repeats) over the last 3 rounds. Confirmation is a separate `POST /confirm` step from the pure `GET /suggest` — suggestions have no side effects, confirming does.
6. **Billing**: round up to nearest 30-min block with a 5-min grace period (hardcoded constants in `billing_service.py`, not admin-configurable — avoid over-engineering a knob nobody asked for).
7. **PromptPay QR**: self-implemented EMVCo TLV + CRC-16/CCITT-FALSE encoder in `promptpay_service.py` (not a third-party pip package) — verified byte-for-byte against dtinth/promptpay-qr's published test vectors (see `backend/tests/test_promptpay_service.py`). Static-amount display QR only, no live payment webhook.
8. **Auth**: bcrypt hashing via the `bcrypt` package directly — **do not reintroduce passlib**, its bcrypt backend detection is broken with bcrypt>=4.1 (`AttributeError: module 'bcrypt' has no attribute '__about__'`).

## Not yet done

Real deployment (needs user-provisioned Supabase/Render/Cloudflare accounts — see `deploy/ENV_SETUP.md`). No automated CI. No test suite beyond backend pytest units (pure-function services only).
