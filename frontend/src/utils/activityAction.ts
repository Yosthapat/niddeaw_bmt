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
  ['POST', /^\/api\/admin\/players$/, 'addPlayer'],
  ['PATCH', /^\/api\/admin\/players\/[^/]+$/, 'editPlayer'],
  ['DELETE', /^\/api\/admin\/players\/[^/]+$/, 'deletePlayer'],
  ['POST', /^\/api\/admin\/players\/[^/]+\/avatar$/, 'uploadAvatar'],
  ['PUT', /^\/api\/admin\/settings$/, 'editSettings'],
  ['POST', /^\/api\/admin\/settings\/qr$/, 'uploadQr'],
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
export function readableDetail(detail: Record<string, string> | null): string {
  if (!detail) return ''
  return Object.values(detail)
    .filter((value) => !UUID.test(String(value)))
    .join(', ')
}
