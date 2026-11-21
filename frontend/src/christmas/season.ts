/**
 * The club's Christmas dress-up: on from 21 November to 4 January, Thai
 * time, and off the rest of the year. Everything that is only for the
 * season lives in this folder (src/christmas/) and in public/xmas/, so
 * the whole of it can be found, and taken out, in one place.
 *
 * `?xmas=1` on any page shows it outside the season (to try it before
 * December); `?xmas=0` switches it off. Either is remembered for the rest
 * of that tab's visit, so it survives moving between pages.
 */

const HOUR = 3_600_000
// Thailand keeps UTC+7 all year (see utils/gameNight.ts).
const THAI_OFFSET = 7 * HOUR
const STORAGE_KEY = 'niddeaw_xmas'

/** The first day of the season, in November (the club wanted it up early). */
const FIRST_NOVEMBER_DAY = 21
/** The last day of the season, in January. */
const LAST_JANUARY_DAY = 4

interface ThaiDay {
  y: number
  /** 1–12 */
  m: number
  d: number
  /** 0 Sunday … 6 Saturday */
  wd: number
}

export function thaiDay(ms: number): ThaiDay {
  const t = new Date(ms + THAI_OFFSET)
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate(), wd: t.getUTCDay() }
}

/** Whether `now` falls inside the season by the calendar alone. */
export function inSeason(now: number = Date.now()): boolean {
  const { m, d } = thaiDay(now)
  return (m === 11 && d >= FIRST_NOVEMBER_DAY) || m === 12 || (m === 1 && d <= LAST_JANUARY_DAY)
}

function override(): boolean | null {
  let stored: string | null = null
  try {
    const asked = new URLSearchParams(window.location.search).get('xmas')
    if (asked === '1' || asked === '0') sessionStorage.setItem(STORAGE_KEY, asked)
    stored = sessionStorage.getItem(STORAGE_KEY)
  } catch {
    // private mode or blocked storage: the calendar decides
  }
  return stored === '1' ? true : stored === '0' ? false : null
}

/**
 * Worked out once, when the app starts. A tab left open across midnight on
 * 4 January keeps its snow until it is reloaded, which is fine.
 */
export const xmasOn: boolean = override() ?? inSeason()

/** The two club nights the season is built around. */
export type SpecialNight = 'xmas' | 'newyear'

/** Christmas night or New Year's night, if the game night starting at `startMs` is one. */
export function specialNight(startMs: number): SpecialNight | null {
  if (!xmasOn) return null
  const { m, d } = thaiDay(startMs)
  if (m === 12 && d === 25) return 'xmas'
  if (m === 1 && d === 1) return 'newyear'
  return null
}

/**
 * The special night the season is heading for at `now`: Christmas until
 * Christmas night is over, then New Year's until that one is. Only a night
 * the club actually plays (a Friday) counts; in a year when the 25th is a
 * Wednesday there is no "Christmas Night" to count down to. Null once both
 * are past, or when neither is a Friday.
 */
export function nextSpecialNight(now: number = Date.now()): { kind: SpecialNight; start: number } | null {
  if (!xmasOn) return null
  const { y, m } = thaiDay(now)
  // The season's December: this one, or last year's in January.
  const decYear = m === 1 ? y - 1 : y
  const nights: { kind: SpecialNight; start: number }[] = [
    { kind: 'xmas', start: Date.UTC(decYear, 11, 25, 20) - THAI_OFFSET },
    { kind: 'newyear', start: Date.UTC(decYear + 1, 0, 1, 20) - THAI_OFFSET },
  ]
  for (const n of nights) {
    if (thaiDay(n.start).wd !== 5) continue
    if (n.start + 4 * HOUR > now) return n
  }
  return null
}

/** New Year's from 26 December (Thai time) to the end of the season,
 *  Christmas before that (and in a preview outside the season). */
export function seasonPhase(now: number = Date.now()): SpecialNight {
  const { m, d } = thaiDay(now)
  return (m === 12 && d > 25) || m === 1 ? 'newyear' : 'xmas'
}

/**
 * The words the home hero and the phone's banner wear in the season: the
 * shout, and the line about when the club plays, pointing at Christmas or
 * New Year's night when the club plays on it.
 */
export function heroCopy(t: (key: string) => string, now: number = Date.now()): { line1: string; line2: string; when: string; whenShort: string; line1Short: string } {
  const phase = seasonPhase(now)
  const next = nextSpecialNight(now)?.kind ?? 'season'
  return {
    line1: t(phase === 'xmas' ? 'xmas.hero.line1' : 'xmas.hero.newYear1'),
    line1Short: t(phase === 'xmas' ? 'xmas.banner.line1' : 'xmas.banner.newYear1'),
    line2: t('xmas.hero.line2'),
    when: t(`xmas.when.${next}`),
    whenShort: t(`xmas.whenShort.${next}`),
  }
}

/** The reader asked for less motion: no snow, no bursts. */
export function reducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
