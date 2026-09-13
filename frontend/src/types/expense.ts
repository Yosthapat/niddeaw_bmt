export type ExpenseCategory = 'court_fee' | 'shuttlecock' | 'jersey' | 'other'

/** Mirrors backend app/models/expense.py Expense. */
export interface Expense {
  id: string
  expense_date: string
  category: ExpenseCategory
  category_other: string | null
  amount: number
  paid_by: string
  receipt_url: string | null
  note: string | null
  is_paid: boolean
  paid_at: string | null
  created_by: string
  created_at: string
}

/** Mirrors backend app/models/expense.py MonthlyExpenseSummary. */
export interface MonthlyExpenseSummary {
  month: string
  total_amount: number
  /** The part already reimbursed to the admin who fronted it — money that has
   * actually left the club's account. `total_amount` includes expenses still
   * owed back, which are a liability, not a withdrawal. */
  paid_amount: number
  by_category: Partial<Record<ExpenseCategory, number>>
  expense_count: number
}
