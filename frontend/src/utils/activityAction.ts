/**
 * What an admin did, in words, from the request the log recorded.
 *
 * The backend already labels each write as it happens
 * (app/services/activity_log_service.py) and stores that label on the row.
 * This mirrors the same table on the way out for two reasons: rows written
 * before a label existed are stored as "PATCH /api/admin/matchmaking/
 * matches/2b2febfb-…/result", and reading them off the method and the path
 * repairs the history that is already in the database rather than only the
 * entries from here on; and the stored label is Thai, so English stays
 * English only if the words are chosen at display time.
 *
 * Keep in step with the backend table. A row whose shape is not listed
 * falls back to whatever the backend stored, which is never nothing.
 */

import { orderNo } from '@/types'
import { money } from '@/utils/format'

/** [method, path pattern, i18n key under `activityLog.actions`] */
const ROUTES: [string, RegExp, string][] = [
  ['POST', /^\/api\/admin\/sessions$/, 'createSession'],
  ['PATCH', /^\/api\/admin\/sessions\/[^/]+$/, 'editSession'],
  ['DELETE', /^\/api\/admin\/sessions\/[^/]+$/, 'deleteSession'],
  ['POST', /^\/api\/admin\/checkins$/, 'checkin'],
  ['POST', /^\/api\/admin\/checkins\/[^/]+\/checkout$/, 'checkout'],
  ['POST', /^\/api\/admin\/matchmaking\/locked-pairs$/, 'lockPair'],
  ['DELETE', /^\/api\/admin\/matchmaking\/locked-pairs\/[^/]+$/, 'unlockPair'],
  ['POST', /^\/api\/admin\/matchmaking\/confirm$/, 'confirmPair'],
  ['PATCH', /^\/api\/admin\/matchmaking\/matches\/[^/]+$/, 'editQueuedMatch'],
  ['DELETE', /^\/api\/admin\/matchmaking\/matches\/[^/]+$/, 'cancelMatch'],
  ['POST', /^\/api\/admin\/matchmaking\/matches\/[^/]+\/start$/, 'startMatch'],
  ['POST', /^\/api\/admin\/matchmaking\/matches\/[^/]+\/result$/, 'recordResult'],
  ['PATCH', /^\/api\/admin\/matchmaking\/matches\/[^/]+\/result$/, 'editResult'],
  ['POST', /^\/api\/admin\/billing\/close-session\/[^/]+$/, 'closeSession'],
  ['POST', /^\/api\/admin\/billing\/player\/[^/]+\/[^/]+$/, 'billPlayer'],
  ['PATCH', /^\/api\/admin\/billing\/[^/]+\/adjust$/, 'adjustBill'],
  ['PATCH', /^\/api\/admin\/billing\/[^/]+\/paid-status$/, 'billPaidStatus'],
  ['POST', /^\/api\/admin\/expenses$/, 'addExpense'],
  ['PATCH', /^\/api\/admin\/expenses\/[^/]+$/, 'editExpense'],
  ['DELETE', /^\/api\/admin\/expenses\/[^/]+$/, 'deleteExpense'],
  ['POST', /^\/api\/admin\/expenses\/[^/]+\/pay$/, 'payExpense'],
  ['POST', /^\/api\/admin\/expenses\/[^/]+\/receipt$/, 'uploadReceipt'],
  ['POST', /^\/api\/admin\/income$/, 'addIncome'],
  ['PATCH', /^\/api\/admin\/income\/[^/]+$/, 'editIncome'],
  ['DELETE', /^\/api\/admin\/income\/[^/]+$/, 'deleteIncome'],
  ['POST', /^\/api\/admin\/income\/[^/]+\/slip$/, 'uploadSlip'],
  ['POST', /^\/api\/admin\/shop\/products$/, 'addProduct'],
  ['PATCH', /^\/api\/admin\/shop\/products\/[^/]+$/, 'editProduct'],
  ['DELETE', /^\/api\/admin\/shop\/products\/[^/]+$/, 'deleteProduct'],
  ['POST', /^\/api\/admin\/shop\/products\/[^/]+\/images$/, 'addProductImage'],
  ['DELETE', /^\/api\/admin\/shop\/products\/[^/]+\/images$/, 'removeProductImage'],
  ['POST', /^\/api\/admin\/shop\/products\/[^/]+\/video$/, 'setProductVideo'],
  ['DELETE', /^\/api\/admin\/shop\/products\/[^/]+\/video$/, 'removeProductVideo'],
  ['POST', /^\/api\/admin\/shop\/products\/[^/]+\/details$/, 'addProductDetail'],
  ['DELETE', /^\/api\/admin\/shop\/products\/[^/]+\/details$/, 'removeProductDetail'],
  ['PATCH', /^\/api\/admin\/shop\/orders\/[^/]+$/, 'updateShopOrder'],
  ['PATCH', /^\/api\/admin\/shop\/orders\/[^/]+\/items\/[^/]+$/, 'editShopOrderItem'],
  ['POST', /^\/api\/admin\/shop\/orders\/[^/]+\/delete$/, 'deleteShopOrder'],
  ['POST', /^\/api\/admin\/sponsors$/, 'addSponsor'],
  ['PATCH', /^\/api\/admin\/sponsors\/[^/]+$/, 'editSponsor'],
  ['DELETE', /^\/api\/admin\/sponsors\/[^/]+$/, 'deleteSponsor'],
  ['POST', /^\/api\/admin\/sponsors\/[^/]+\/logo$/, 'sponsorLogo'],
  ['PUT', /^\/api\/admin\/sponsors\/order$/, 'reorderSponsors'],
  ['POST', /^\/api\/admin\/players$/, 'addPlayer'],
  ['PATCH', /^\/api\/admin\/players\/[^/]+$/, 'editPlayer'],
  ['DELETE', /^\/api\/admin\/players\/[^/]+$/, 'deletePlayer'],
  ['POST', /^\/api\/admin\/players\/[^/]+\/avatar$/, 'uploadAvatar'],
  ['PUT', /^\/api\/admin\/settings$/, 'editSettings'],
  ['POST', /^\/api\/admin\/settings\/qr$/, 'uploadQr'],
  ['PUT', /^\/api\/admin\/quests\/settings$/, 'questSettings'],
  ['POST', /^\/api\/admin\/line\/requests\/[^/]+\/approve$/, 'approveLineLink'],
  ['POST', /^\/api\/admin\/line\/requests\/[^/]+\/reject$/, 'rejectLineLink'],
  ['POST', /^\/api\/admin\/line\/players\/[^/]+\/unlink$/, 'unlinkLine'],
  ['POST', /^\/api\/admin\/line\/joins\/[^/]+\/approve$/, 'approveLineJoin'],
  ['POST', /^\/api\/admin\/line\/joins\/[^/]+\/reject$/, 'rejectLineJoin'],
  ['POST', /^\/api\/admin\/line\/checkin-qr\/rotate$/, 'rotateCheckinQr'],
  ['PUT', /^\/api\/admin\/line\/checkin-spot$/, 'pinCheckinSpot'],
  ['DELETE', /^\/api\/admin\/line\/checkin-spot$/, 'unpinCheckinSpot'],
  ['POST', /^\/api\/admin\/billing\/[^/]+\/reject-slip$/, 'rejectBillSlip'],
  ['POST', /^\/api\/admin\/credit\/topups\/[^/]+\/approve$/, 'approveTopup'],
  ['POST', /^\/api\/admin\/credit\/topups\/[^/]+\/reject$/, 'rejectTopup'],
  ['POST', /^\/api\/admin\/credit\/players\/[^/]+\/adjust$/, 'adjustCredit'],
  ['POST', /^\/api\/admin\/credit\/packages$/, 'createCreditPackage'],
  ['PATCH', /^\/api\/admin\/credit\/packages\/[^/]+$/, 'updateCreditPackage'],
  ['DELETE', /^\/api\/admin\/credit\/packages\/[^/]+$/, 'deleteCreditPackage'],
  ['POST', /^\/api\/admin\/backup$/, 'downloadBackup'],
  ['POST', /^\/api\/admin\/sheets\/sync$/, 'syncSheets'],
  ['POST', /^\/api\/admin\/stats-audit\/repair$/, 'repairStats'],
]

export function actionKey(method: string, path: string): string | null {
  for (const [candidate, pattern, key] of ROUTES) {
    if (candidate === method && pattern.test(path)) return key
  }
  return null
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * The detail a row carries is the request's path parameters, which today
 * are all ids — a bare UUID under a sentence that already says what
 * happened, telling the reader nothing. They are dropped rather than the
 * whole line, so a parameter that is not an id still shows.
 */
export function readableDetail(
  detail: Record<string, unknown> | null,
  // Words for a bare count — "17 tables", "1,234 rows" — which need the
  // page's language; without it the number shows alone.
  count?: (key: 'tables' | 'rows', n: number) => string,
): string {
  if (!detail) return ''
  // A deleted order's record says what it was: S-0012, who, what, how much.
  return Object.entries(detail)
    .filter(([key, value]) => key !== 'status' && !UUID.test(String(value)))
    .map(([key, value]) => {
      if (key === 'order_no') return orderNo(Number(value))
      if (key === 'total') return money(Number(value))
      if (count && (key === 'tables' || key === 'rows')) return count(key, Number(value))
      return Array.isArray(value) ? value.join(' + ') : String(value)
    })
    .join(', ')
}
