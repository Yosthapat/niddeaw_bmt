import i18n from '@/i18n'
import { ApiError } from './client'

// The backend's own sentences, mapped to something an admin at the side of
// a court can act on. Several are English because they started as developer
// messages; the Thai ones are already written for the admin and pass
// through as they are. Anything not listed here falls back to the screen's
// own "couldn't save" line rather than showing the raw text.
const KNOWN: Record<string, string> = {
  'Session not found': 'apiErrors.sessionGone',
  'No fields to update': 'apiErrors.nothingChanged',
  'Too many failed login attempts': 'apiErrors.tooManyLogins',
  'Invalid username or password': 'apiErrors.badLogin',
  'Checkin not found': 'apiErrors.checkinGone',
  'category_other is required when category is "other"': 'apiErrors.categoryOtherRequired',
  'Expense not found': 'apiErrors.rowGone',
  'Income entry not found': 'apiErrors.rowGone',
  'Billing row not found': 'apiErrors.rowGone',
  'Locked pair not found': 'apiErrors.rowGone',
  'Match not found': 'apiErrors.matchGone',
  'Player not found': 'apiErrors.playerGone',
  'Receipt file too large (max 5MB)': 'apiErrors.fileTooLarge5',
  'QR file too large (max 5MB)': 'apiErrors.fileTooLarge5',
  'Slip file too large (max 5MB)': 'apiErrors.fileTooLarge5',
  'Avatar file too large (max 2MB) — resize before uploading': 'apiErrors.fileTooLarge2',
  'Logo file too large (max 5MB)': 'apiErrors.fileTooLarge5',
  'Sponsor not found': 'apiErrors.rowGone',
  'Unsupported image type': 'apiErrors.badImage',
  'Club settings not seeded': 'apiErrors.settingsMissing',
  'Club settings not configured — set them in Admin > Settings first': 'apiErrors.settingsMissing',
  'PromptPay ID not configured — set it in Admin > Settings first': 'apiErrors.promptpayMissing',
  'Bank account not configured — set it in Admin > Settings first': 'apiErrors.bankMissing',
  'No QR code uploaded — upload one in Admin > Settings first': 'apiErrors.qrMissing',
  'One of these players is already locked with someone else this session': 'apiErrors.alreadyLocked',
  'Only a queued match can be edited': 'apiErrors.matchMoved',
  'Only a queued or in-progress match can be cancelled': 'apiErrors.matchMoved',
  'Only a queued match can be started': 'apiErrors.matchMoved',
}

const THAI = /[฀-๿]/

/** The detail FastAPI put in the body, or null when there's nothing a
 * person should read — a 422's field list, an HTML error page, an empty
 * body. */
function detailOf(raw: string): string | null {
  let detail: unknown
  try {
    detail = (JSON.parse(raw) as { detail?: unknown }).detail
  } catch {
    return null
  }
  if (typeof detail !== 'string') return null
  const key = KNOWN[detail]
  if (key) return i18n.global.t(key)
  return THAI.test(detail) ? detail : null
}

/** One line for a failed request: what failed (the screen's own wording)
 * and, when it's known, why and what to do — never a status code or a
 * JSON body. */
export function apiErrorMessage(e: unknown, fallback: string): string {
  const { t } = i18n.global
  if (!(e instanceof ApiError)) {
    // fetch() only throws on its own when the request never got an answer.
    return e instanceof TypeError ? `${fallback} — ${t('apiErrors.offline')}` : fallback
  }
  if (e.status === 401) return `${fallback} — ${t('apiErrors.signedOut')}`
  if (e.status === 429) {
    return e.retryAfterSeconds
      ? `${fallback} — ${t('apiErrors.waitSeconds', { n: e.retryAfterSeconds })}`
      : `${fallback} — ${t('apiErrors.tooManyLogins')}`
  }
  if (e.status >= 500) return `${fallback} — ${t('apiErrors.server')}`
  if (e.status === 422) return `${fallback} — ${t('apiErrors.invalid')}`
  const detail = detailOf(e.message)
  return detail ? `${fallback} — ${detail}` : fallback
}
