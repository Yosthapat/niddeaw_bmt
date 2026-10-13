/**
 * One place that decides how this app writes a date, a time and a sum.
 *
 * It exists because it did not: the expenses screen alone showed three
 * different date formats within one screenful ("October 2026" from a native
 * month input, "13 ต.ค. 2569" on the row below it, "2026-10" in the history
 * under that), the activity log asked for a date as "mm/dd/yyyy", and money
 * was written "฿1,000" on the dashboard and "฿1109.00" one tab away.
 *
 * Thai dates come back in the Buddhist era because that is what `th-TH`
 * does; English uses `en-GB` rather than `en-US` so the day leads in both
 * languages and no reader has to work out which number is the month.
 */

type Locale = string

function tag(locale: Locale): string {
  return locale === 'th' ? 'th-TH' : 'en-GB'
}

/** `฿1,109.00` — grouped, always two decimals, everywhere money appears. */
export function money(amount: number): string {
  return `฿${amount.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/**
 * `฿1,109` — the same sum where the satang would be noise and the space is
 * tight: chart axes, chart tooltips, a donut's centre.
 */
export function moneyShort(amount: number): string {
  const rounded = Math.round(amount)
  return `${rounded < 0 ? '−' : ''}฿${Math.abs(rounded).toLocaleString('en-US')}`
}

/** `13 ต.ค. 2569` / `13 Oct 2026` — from a date-only or full ISO string. */
export function formatDate(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleDateString(tag(locale), {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** `อ. 13 ต.ค. 2569` — where the day of the week is the point (a club night). */
export function formatDateWithWeekday(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleDateString(tag(locale), {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** `13 ต.ค.` — inside a heading that already says the year, or none needs it. */
export function formatDayMonth(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleDateString(tag(locale), { day: 'numeric', month: 'long' })
}

/** `ต.ค. 2569` — from a `YYYY-MM` string, for the month a screen is showing. */
export function formatMonth(yearMonth: string, locale: Locale): string {
  const [year, month] = yearMonth.split('-').map(Number)
  if (!year || !month) return yearMonth
  // Midday UTC: the date itself is never shown, and midnight would roll
  // back a day in any timezone behind UTC and name the month before it.
  return new Date(Date.UTC(year, month - 1, 1, 12)).toLocaleDateString(tag(locale), {
    month: 'short',
    year: 'numeric',
  })
}

/** `18:23` — 24-hour in both languages, which is how a court books time. */
export function formatTime(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleTimeString(tag(locale), {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/**
 * `13 ต.ค. 2569 18:23` — the two above, in that order.
 *
 * No seconds: a match log and an activity log are read to the minute, and
 * the seconds were the widest part of the line on a phone.
 */
export function formatDateTime(iso: string, locale: Locale): string {
  return `${formatDate(iso, locale)} ${formatTime(iso, locale)}`
}
