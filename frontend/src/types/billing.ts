export type PaidStatus = 'unpaid' | 'paid'

export interface Billing {
  id: string
  session_id: string
  player_id: string
  game_count: number
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

/** Mirrors backend app/models/billing.py DailyRevenue. */
export interface DailyRevenue {
  date: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  session_count: number
  billing_count: number
}

export type PromptPayType = 'phone' | 'national_id' | 'ewallet'
export type PaymentMethod = 'promptpay' | 'bank_account' | 'bank_account_qr' | 'uploaded_qr'

export interface ClubSettings {
  payment_method: PaymentMethod
  promptpay_id: string
  promptpay_type: PromptPayType
  bank_name: string | null
  bank_account_number: string | null
  bank_account_name: string | null
  uploaded_qr_url: string | null
  default_court_fee_per_person: number
  default_shuttlecock_price_per_game: number
}

/** Mirrors backend app/routers/admin/billing.py PaymentInfoResponse. */
export interface PaymentInfoResponse {
  method: PaymentMethod
  amount: number
  data_uri: string | null
  bank_name: string | null
  bank_account_number: string | null
  bank_account_name: string | null
}
