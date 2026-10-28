/** The bounds backend/app/models/fields.py enforces, mirrored so a form
 *  can say what is wrong next to the field instead of after a round trip.
 *  The API is the guarantee; a change to one belongs in the other. */

export const MAX_BAHT = 1_000_000
export const MAX_NAME = 120
export const MAX_HANDLE = 100
export const MAX_NOTE = 500
export const MAX_ELO = 4000

export type BahtProblem = 'empty' | 'notNumber' | 'negative' | 'zero' | 'tooLarge'

/** Why `raw` is not a usable amount of baht, or null when it is. A number
 *  input bound with v-model.number hands back '' when cleared, so empty
 *  and not-a-number are both real cases here. */
export function bahtProblem(raw: unknown, opts: { allowZero: boolean }): BahtProblem | null {
  if (raw === '' || raw === null || raw === undefined) return 'empty'
  const value = typeof raw === 'number' ? raw : Number(raw)
  if (!Number.isFinite(value)) return 'notNumber'
  if (value < 0) return 'negative'
  if (value === 0 && !opts.allowZero) return 'zero'
  if (value > MAX_BAHT) return 'tooLarge'
  return null
}

const PROMPTPAY_DIGITS = { phone: 10, national_id: 13, ewallet: 15 } as const

/** Mirrors promptpay_service.id_problem: the digit count each kind of id
 *  must have for the QR to be payable. Spaces and dashes are allowed, as
 *  people type phone numbers with them. */
export function promptpayIdProblem(raw: string, kind: keyof typeof PROMPTPAY_DIGITS): boolean {
  const digits = raw.replace(/[\s-]/g, '')
  if (!/^\d+$/.test(digits) || digits.length !== PROMPTPAY_DIGITS[kind]) return true
  return kind === 'phone' && !digits.startsWith('0')
}

/** Today's date where the admin is standing, as YYYY-MM-DD.
 *  toISOString() is UTC: in Bangkok it still says yesterday until 07:00,
 *  so a session opened just after midnight was filed under the wrong day. */
export function localToday(): string {
  const now = new Date()
  const pad = (n: number): string => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
