# Active Context

## Current Task
- Implemented cross-group rotation for matchmaking (user picked option 2 of the two proposed fixes) — pushing now

## Done Last Session
- Explained why repeat pairings happen despite the fairness penalty working correctly: with a small/ELO-stable checked-in pool, `suggest_doubles_pairings` locked players into rigid non-overlapping ELO-sorted windows of 4, so only the 3 possible 2v2 splits *within* that fixed foursome could rotate — the fairness penalty had no way to change *who* was in the group
- User chose: allow cross-group swaps (not expanding the 3-round lookback)
- `matchmaking_service.py`: replaced the fixed-window grouping with `_best_group_from_pool` — the highest-ELO remaining player anchors a group, and its 3 groupmates are chosen from the best-cost foursome+split combination out of a widened pool (`GROUP_SEARCH_WINDOW = 7` next-closest-ELO remaining players, not rigidly the next 3). For small checked-in counts (≤8, matching the user's real test group) this window covers everyone remaining, so the search is effectively global
- Added `backend/tests/test_matchmaking_service.py` (new file, no matchmaking-specific tests existed before): confirms clearly-separated ELO clusters still group together with no history (baseline unchanged), and confirms a player with 3 recent partners gets grouped with different people when equal-ELO zero-penalty alternatives exist within the window (the actual regression case reported)
- mypy + pytest (27/27, up from 25) clean; no frontend changes needed — pure backend algorithm change, `suggest_doubles_pairings`'s signature is unchanged so `queue_service.py`'s call site needed no updates

## Next Steps
- Push and confirm live
- No SQL/migration needed for this one — pure application logic

## Last Updated
- Claude Code — 2026-07-23

## Checkpoint (auto)
- 01:27 — edited active.md
- 01:25 — edited matchmaking_service.py
- 01:25 — edited matchmaking_service.py
- 01:23 — edited active.md