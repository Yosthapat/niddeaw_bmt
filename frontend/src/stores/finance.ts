import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { DailyRevenue, Expense, OtherIncome } from '@/types'

/**
 * The three money feeds the dashboard's charts are built from, fetched once
 * and shared.
 *
 * Both charts used to fetch for themselves, which meant the dashboard asked
 * for /billing/revenue twice on every visit and additionally pulled
 * /expenses/summary for a figure the raw expense rows already answer. They
 * stay self-contained about what they *draw*; only the fetching moved here.
 *
 * Deliberately refresh() on mount rather than a cached ensureLoaded(): an
 * admin who records an expense and comes back to the dashboard should see
 * it. The in-flight promise is what collapses the two charts' simultaneous
 * calls into one round-trip, and it clears as soon as the request settles
 * so a later visit still fetches fresh numbers — same pattern as
 * stores/sessions.ts.
 */
export const useFinanceStore = defineStore('finance', () => {
  const dailyRevenue = ref<DailyRevenue[]>([])
  const expenses = ref<Expense[]>([])
  const otherIncome = ref<OtherIncome[]>([])
  const loading = ref(true)
  /** The raw failure — each chart renders its own message from it, since
   * they word the error differently and one may be on screen without the
   * other. */
  const error = ref<unknown>(null)

  let inFlight: Promise<void> | null = null

  function refresh(): Promise<void> {
    inFlight ??= runRefresh().finally(() => {
      inFlight = null
    })
    return inFlight
  }

  async function runRefresh(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [revenue, expenseList, income] = await Promise.all([
        adminApi.getRevenue(),
        adminApi.getExpenses(),
        adminApi.getOtherIncome(),
      ])
      dailyRevenue.value = revenue
      expenses.value = expenseList
      otherIncome.value = income
    } catch (e) {
      // Held rather than thrown: both charts await the same promise, so a
      // rejection would surface as an unhandled rejection in whichever one
      // didn't attach a catch first.
      error.value = e
    } finally {
      loading.value = false
    }
  }

  return { dailyRevenue, expenses, otherIncome, loading, error, refresh }
})
