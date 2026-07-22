# Active Context

## Current Task
- Replaced hand-drawn SVG tier mascots with the user's 7 illustrated character images — pushing now

## Done Last Session
- Denormalized player stats fully verified in prod: submit_result increments games/wins/draws/losses correctly, ranking/hall-of-fame/match-detail/list_players all read the denormalized columns correctly, /members pagination works, cleanup of the verification match/session completed
- User provided 7 mascot character images (milk/beer/highball/wine/soju/whisky/vodka), each 1536x1024 with ~600-870KB opaque near-black backgrounds and lots of padding around the character
- Cropped each to its content bbox (+6% padding), padded into a square black canvas, resized to 320x320, converted to WebP — 600-870KB down to 5.5-11KB each (~98% smaller)
- Kept the opaque black square background as-is rather than attempting transparency — a naive near-black chroma-key threshold risked eating into the artwork's own dark outlines/linework; the shade difference between pure black and the site's --color-brand-black (#0a0406) is imperceptible at the small sizes (20-64px) these render at
- Rewrote `TierMascot.vue`: replaced the ~230-line inline-SVG-per-tier template with a single `<img :src="/tiers/{tier}.webp">`, sized via the existing `size` prop — since every page (home, member list, profile, match cards, ranking, hall of fame, admin) already goes through this one shared component, the swap applies everywhere at once
- Confirmed the tier order the user wants (Milk < Beer < Highball < Wine < Soju < Whisky < Vodka) already matches what's live from the earlier wine-tier reordering — no reordering work needed
- `vue-tsc -b && vite build` clean; old TierMascot JS chunk disappeared entirely (now just a tiny img tag)

## Next Steps
- Push and confirm live, spot-check the mascots render correctly across a few pages (home tier legend, member list, profile)

## Last Updated
- Claude Code — 2026-07-23

## Checkpoint (auto)
- 01:05 — edited active.md
- 01:02 — edited active.md