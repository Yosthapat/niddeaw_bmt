# Active Context

## Current Task
- none

## Done Last Session
- New Vodka tier mascot artwork committed and pushed (414ae80) — background removed via flood-fill script, resized to 320x320, saved as vodka.webp
- Fixed cramped mobile header: on screens <640px, the "ADMIN LOGIN" button in
  AppHeader.vue collapses to an icon-only lock button (text hidden below
  `sm:`) instead of full text, freeing horizontal space for the 5 nav links
  + language switcher that were all fighting for the same row
- Pending changes ready to deploy: rainbow Absinthe tier (4de6f11), new
  Vodka mascot (414ae80), mobile header fix (not yet committed — next step)

## Next Steps
- Commit + push the AppHeader.vue mobile fix
- User deploys to Cloudflare Workers when ready: `export CLOUDFLARE_API_TOKEN="your-token" && cd "/Users/tabby/For work/niddeaw_bmt" && npx wrangler deploy`
- No browser tool available in this environment to visually confirm the mobile fix — worth a quick look on a real phone once deployed

## Blockers
- none

## Last Updated
- Claude Code — 2026-08-04

## Checkpoint (auto)
- 02:21 — edited active.md
- 02:21 — edited AppHeader.vue
- 02:18 — edited active.md