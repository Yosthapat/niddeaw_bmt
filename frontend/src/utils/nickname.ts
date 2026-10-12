/** The nickname rules, mirrored from backend/app/services/nickname_service.py.
 *
 *  The API is the guarantee — both add forms end up calling it, and a
 *  browser is not where a rule is enforced. This is here so the admin finds
 *  out while typing rather than after a round trip, and the two must say
 *  the same thing: the pattern, the length and the messages are copied
 *  deliberately, and a change to one belongs in the other. */

export const NICKNAME_PATTERN = /^[A-Z][A-Za-z'-]*(?: [A-Za-z'-]+)*$/
export const NICKNAME_MAX_LENGTH = 40

const ENGLISH_ISH = /^[A-Za-z][A-Za-z'\- ]*$/

/** Trim the ends and collapse runs of whitespace, so "  Big   Boy " and
 *  "Big Boy" are the same name. */
export function normaliseNickname(raw: string): string {
  return raw.trim().split(/\s+/).join(' ')
}

/** The key of the reason this nickname is not allowed, or null if it is.
 *  The caller turns the key into a message through i18n, so the rule reads
 *  in whichever language the admin is using. */
export function nicknameProblem(raw: string): 'empty' | 'tooLong' | 'notEnglish' | 'notCapitalised' | null {
  const name = normaliseNickname(raw)
  if (!name) return 'empty'
  if (name.length > NICKNAME_MAX_LENGTH) return 'tooLong'
  if (NICKNAME_PATTERN.test(name)) return null
  // A name that is already English and merely starts lowercase is told
  // about the capital: "must be English" would send them looking for the
  // wrong thing.
  if (ENGLISH_ISH.test(name)) return 'notCapitalised'
  return 'notEnglish'
}

/** Whether `raw` is the name of someone already on the list, ignoring case
 *  and ignoring the member being edited. The API checks this against the
 *  database; this catches it against the roster already on screen. */
export function nicknameTaken(
  raw: string,
  existing: { id: string; nickname: string }[],
  excludeId?: string,
): boolean {
  const name = normaliseNickname(raw).toLowerCase()
  if (!name) return false
  return existing.some((p) => p.id !== excludeId && p.nickname.toLowerCase() === name)
}
