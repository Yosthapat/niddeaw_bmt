---
name: critic-ux
description: Score this app's UI from 0 to 10 on five axes — complexity, self-explanatory, consistency, steps per operation, responsive — from real screenshots of every screen, and say what to change to move each number. Use when asked to review or critique the UI/UX, to check whether a change made the UI better or worse, or when a goal is phrased as a target score.
---

# critic-ux

Judge the UI the way the person at the court meets it: one admin, one phone,
one hand, a club night happening around them. Not from the code.

## The one rule

**Score only what you have looked at.** Take the screenshots first, open
every one of them, and let every finding point at a screen by name. A score
reasoned out of source files is a guess wearing a number, and it will be
wrong in the direction that flatters whoever wrote the code.

## Getting the screenshots

`tools/uxlab/` runs the real backend against an in-memory database seeded
with a night in progress, so no screen is empty and nothing touches
production. Its README has the three commands; the short version:

```bash
python tools/uxlab/lab.py &
VITE_API_BASE_URL=http://127.0.0.1:5399 npm --prefix frontend run build
python tools/uxlab/shoot.py --width 430 --out /tmp/ux
```

430px is the real device. Shoot 1280 too only when the question is about
desktop. Rebuild the frontend normally afterwards — the lab build points at
localhost.

Then **read every PNG**. Page errors printed by `shoot.py` are findings, not
noise.

## The five axes

Each is 0–10. Score the whole admin flow, not the best screen in it.

### 1. Complexity
How much is on screen before the work starts, and how much of it is chrome.

- **9–10** — every screen opens on its own job; navigation costs a strip.
- **7–8** — one layer of chrome above the content, consistent, predictable.
- **5–6** — chrome eats a third of the first screenful; controls the admin
  needs twice a night sit beside the ones they need twenty times.
- **0–4** — the content is below the fold on arrival.

Measure it: in the screenshot, how many pixels until the first thing the
admin came to do? Over a third of the viewport costs points.

### 2. Self-explanatory
Whether someone who was not told can tell what will happen.

- **9–10** — every state names itself; empty states say what to do next;
  destructive actions say what they destroy.
- **7–8** — mostly obvious; a couple of labels assume the backstory.
- **5–6** — a screen needs explaining out loud to be used.
- **0–4** — a message is actively wrong about the state it is describing.

A string that says one thing while the data says another is the worst
finding on this axis. Look for it specifically: trigger the awkward states
(nobody checked in, everybody busy, session closed, nothing billed yet).

### 3. Consistency within its domain
Whether the app agrees with itself.

Check: page titles in one language; headings with counts or none, not both;
the primary button in the same place; one confirm dialog, not two kinds; the
same component for the same object everywhere; search boxes in the same
position; destructive actions styled one way.

- **9–10** — a screen you have not seen behaves exactly as the others taught.
- **7–8** — small drifts a stranger would not notice.
- **5–6** — two conventions live side by side.
- **0–4** — each screen was clearly built alone.

### 4. Steps per operation
Count real taps for the jobs this app exists for, from arriving on the page.

Count them explicitly and write the count down: check a member in, pair a
match, start it, record its result, correct a wrong result, bill one person,
close the night, find one person among sixteen.

- **9–10** — every nightly job is one or two taps, none needs a detour
  through a screen built for someone else.
- **7–8** — the common jobs are short; a rarer one wanders.
- **5–6** — a nightly job takes four or more taps, or leaves the admin area
  to finish.
- **0–4** — something cannot be done at all and needs the database.

### 5. Responsive & cross-browser
At 430px: horizontal scroll anywhere is an automatic cap at 6. Then look for
wrapped button rows that strand a control, tap targets under ~40px, text
under 12px, anything cut off at the edge, and layouts that stay phone-shaped
and empty on a wide screen.

Remember the constraint this app ships under: it is opened inside the LINE
webview, so no `oklch()`, no `AbortSignal.timeout()`, and anything exotic
needs a fallback.

## What to hand back

1. **The table**: five axes, each score, one line of reason each, then the
   overall (the mean, rounded to one decimal).
2. **Findings, ordered by how much they cost**, not by severity labels. Each
   one: the screen it is on, what the admin meets, and the fix in a sentence.
   A defect that appears on every screen outranks a worse one that appears on
   a single rare screen — say so when it is why.
3. **What would move the number**: which two or three fixes raise which axes,
   and to what. Be specific enough that the person can decide to skip one.

Keep praise to the sentence it deserves. The point of a score is to be
actionable, and an inflated one is worth nothing twice: once when it is
given, and again when the next review has to walk it back.

## Re-scoring after a change

Shoot the same widths again into a second directory and put the two numbers
side by side, with the before and after screenshot of each screen you claim
improved. If an axis did not move, say it did not move.
