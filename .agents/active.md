# Active Context

## Current Task
- Home page blank-render bug: fixed, pushing deploy

## Done Last Session
- Diagnosed home page blank/broken bug via user's DevTools console screenshot: `SyntaxError: Invalid linked format` thrown from vue-i18n's message compiler (tokenizer/parser) while rendering HomeView
- Root cause: `home.contactBody` in both `th.ts`/`en.ts` contained a literal `@369iojcn` (LINE OA handle) — vue-i18n reserves unescaped `@` for "linked message" syntax (`@:key`), so any literal `@` breaks compilation of that message the first time it's used
- Verified root cause directly with `@intlify/message-compiler`'s `baseCompile` + throwing `onError` — reproduced "Invalid linked format" for the raw string, confirmed `\@369iojcn` (backslash-escaped) compiles cleanly
- Fixed by escaping to `\\@369iojcn` in both locale files; `npm run build` passes clean
- Ran backend sanity checks: `/health` 200, public endpoints respond correctly, admin routes 401 without token — backend logic unchanged since last full authenticated flow test

## Next Steps
- Commit and push the i18n escape fix, confirm live site renders HomeView again
- Re-run full authenticated admin flow (login → checkin → matchmaking → billing → revenue) if user wants a fresh end-to-end pass
- Clean up any QA test data created during verification

## Blockers
- none

## Last Updated
- Claude Code — 2026-07-21

## Checkpoint (auto)
- 05:21 — edited active.md
- 05:20 — edited en.ts
- 05:20 — edited th.ts
- 05:19 — edited active.md