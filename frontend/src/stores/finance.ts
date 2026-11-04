import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { DailyRevenue, Expense, OtherIncome, ShopRevenue } from '@/types'
import type { CreditSummary } from '@/api/admin'

/**
 * The money feeds the dashboard's charts are built from, fetched once and
 * shared: session dues, expenses, other income and the shop's sales.
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
  /** null until loaded. Fetched with the rest, not apart: a balance that
   * silently left out the shop would be a wrong number, not a smaller one. */
  const shop = ref<ShopRevenue | null>(null)
  /** Cash taken for club credit, and the credit members still hold. */
  const credit = ref<CreditSummary | null>(null)
  /** The credit figures failed on their own. Unlike the shop, they don't
   * take the charts down with them: the charts still draw dues, expenses
   * and the shop, and say that credit top-ups are missing from the total. */
  const creditError = ref<unknown>(null)
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
    creditError.value = null
    // Asked for at the same time as the rest, but not waited on with it:
    // the charts draw as soon as dues, expenses and the shop are in, and the
    // credit figures join them when they arrive (or say they couldn't).
    const creditSummary = adminApi.getCreditSummary().then(
      (summary) => {
        credit.value = summary
      },
      (e: unknown) => {
        credit.value = null
        creditError.value = e
      },
    )
    try {
      const [revenue, expenseList, income, shopRevenue] = await Promise.all([
        adminApi.getRevenue(),
        adminApi.getExpenses(),
        adminApi.getOtherIncome(),
        adminApi.getShopRevenue(),
      ])
      dailyRevenue.value = revenue
      expenses.value = expenseList
      otherIncome.value = income
      shop.value = shopRevenue
    } catch (e) {
      // Held rather than thrown: both charts await the same promise, so a
      // rejection would surface as an unhandled rejection in whichever one
      // didn't attach a catch first.
      error.value = e
    } finally {
      loading.value = false
    }
    await creditSummary
  }

  return { dailyRevenue, expenses, otherIncome, shop, credit, creditError, loading, error, refresh }
})
