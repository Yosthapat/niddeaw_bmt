# Active Context

## Current Task

- Waiting for user to manually fill in PromptPay ID and pricing settings at <https://niddeaw-bmt.yosthapatk-mbai.workers.dev/admin/settings> and click save button

## Done Last Session
- Executed database migration at Supabase SQL Editor (0006_per_game_billing.sql)
- Redeployed backend (Render) with new billing schema (default_court_fee_per_person, default_shuttlecock_price_per_game)
- Redeployed frontend (Cloudflare Pages) with updated admin settings form
- Verified backend and frontend redeploy successful (HTTP 200, correct schema in use)
- Billing model refactor complete: from hourly rate → per-game shuttlecock pricing

## Next Steps
- Fill in PromptPay ID: `0909626989` (type: เบอร์โทรศัพท์)
- Fill in default court fee: `80`
- Fill in default shuttlecock price: `29`
- Click "บันทึกการตั้งค่า" button to save
- Verify settings were saved correctly in database

## Blockers
- None — system is deployed and ready for configuration

## Last Updated
- Claude Code — 2026-07-20

## Checkpoint (auto)
- 04:17 — edited players.py
- 04:16 — edited players.py
- 04:16 — edited test_stats_service.py
- 04:16 — edited test_stats_service.py
- 04:16 — edited stats_service.py
- 04:15 — edited player.py
- 04:03 — edited active.md
- 04:03 — edited active.md
- 03:59 — edited active.md (billing migration completed)
- [continuation] — backend + frontend redeploy verified, awaiting settings input