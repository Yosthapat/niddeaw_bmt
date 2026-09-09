export type IncomeSource = 'sponsor' | 'investment' | 'other'

/** Mirrors backend app/models/other_income.py OtherIncome. */
export interface OtherIncome {
  id: string
  income_date: string
  source: IncomeSource
  source_name: string
  amount: number
  note: string | null
  slip_url: string | null
  created_by: string
  created_at: string
}
