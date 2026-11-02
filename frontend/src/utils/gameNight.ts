// When the club next plays: every Friday, 20:00 to midnight, Thai time —
// the same night the home page's "ทุกวันศุกร์ · 20:00–00:00" says. Worked
// out in Thai time whatever the reader's own clock is set to, so a member
// abroad still counts down to the club's Friday, not their own.
//
// Thailand keeps UTC+7 all year (no daylight saving), so a fixed offset is
// exact.

const HOUR = 3_600_000
const DAY = 24 * HOUR
const THAI_OFFSET = 7 * HOUR
const FRIDAY = 5
const STARTS_AT_HOUR = 20
const LASTS = 4 * HOUR

export interface GameNight {
  /** Epoch ms of this or the next night's 20:00. */
  start: number
  /** Epoch ms of its midnight. */
  end: number
  /** The night is on right now. */
  on: boolean
}

/** The game night that is on at `now`, or else the next one. */
export function gameNight(now: number): GameNight {
  const thai = new Date(now + THAI_OFFSET)
  // Midnight at the start of today in Thailand, as epoch ms.
  const thaiMidnight = Date.UTC(thai.getUTCFullYear(), thai.getUTCMonth(), thai.getUTCDate()) - THAI_OFFSET
  const daysToFriday = (FRIDAY - thai.getUTCDay() + 7) % 7
  let start = thaiMidnight + daysToFriday * DAY + STARTS_AT_HOUR * HOUR
  if (start + LASTS <= now) start += 7 * DAY
  return { start, end: start + LASTS, on: now >= start }
}

/** Whole days, hours, minutes and seconds from `now` until `until`. */
export function timeLeft(until: number, now: number): { days: number; hours: number; minutes: number; seconds: number } {
  const total = Math.max(0, Math.floor((until - now) / 1000))
  return {
    days: Math.floor(total / 86_400),
    hours: Math.floor((total % 86_400) / 3600),
    minutes: Math.floor((total % 3600) / 60),
    seconds: total % 60,
  }
}
