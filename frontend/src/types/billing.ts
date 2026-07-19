export type PaidStatus = 'unpaid' | 'paid'

export interface Billing {
  id: string
  session_id: string
  player_id: string
  hours_played: number
  amount_calc: number
  amount_adjusted: number | null
  paid_status: PaidStatus
  promptpay_ref: string | null
  updated_at: string
}

/** effective amount owed = amount_adjusted ?? amount_calc (mirrors Billing.effective_amount) */
export function effectiveAmount(billing: Billing): number {
  return billing.amount_adjusted ?? billing.amount_calc
}

export type PromptPayType = 'phone' | 'national_id' | 'ewallet'

export interface ClubSettings {
  promptpay_id: string
  promptpay_type: PromptPayType
  default_rate_per_hour: number
}
