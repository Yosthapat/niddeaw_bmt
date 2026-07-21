# Active Context

## Current Task
- Made the DRAW stamp label consistent with WIN/LOSS (always-English badge convention) — pushing now

## Done Last Session
- Confirmed "Create Custom Match" (สร้างคู่เอง) live in production (commit 802c23e), verified via direct chunk inspection (grep for "createCustom"/"pickPlayer"/"cancelMatch" in the new MatchmakingView-DOvVgtV1.js) after a couple of transient/stale polling reads
- User flagged inconsistency: the WIN/LOSS stamp badges on /matches and /matches/:id are always English ("WIN"/"LOSS", matches.win/matches.loss keys, same in both locales) but the DRAW stamp used `common.draw` which is localized ("เสมอ" in Thai) — visually inconsistent badge style
- Added a new `matches.draw: 'DRAW'` key (English, both locales) matching the matches.win/matches.loss pattern
- Updated the 3 actual stamp/badge usages to use it: MatchHistoryView.vue's two `stamp--draw` spans, MatchDetailView.vue's `statusLabel()` draw case (dropped the now-redundant `.toUpperCase()`)
- Left `common.draw` (localized "เสมอ"/"Draw") untouched everywhere else it's plain prose or a table header, not a badge: MatchRecordView.vue's draw button, PlayerProfileView.vue (x2), MatchDetailView.vue's plain text line under the score, MemberListView.vue's table header
- `vue-tsc -b && vite build` clean

## Next Steps
- Push and confirm live
- Consider adding singles match UI support (backend already supports type: 'single')

## Last Updated
- Claude Code — 2026-07-22

## Checkpoint (auto)
- 06:56 — edited active.md
- 06:54 — edited active.md