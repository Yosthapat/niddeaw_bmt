/**
 * LINE's LIFF SDK: what lets the /line page, opened inside LINE, know who
 * is using it. Loaded from LINE's own CDN only on that page, so no other
 * page pays for it.
 *
 * https://developers.line.biz/en/reference/liff/
 */

const SDK_URL = 'https://static.line-scdn.net/liff/edge/2/sdk.js'

interface Liff {
  init(config: { liffId: string }): Promise<void>
  isLoggedIn(): boolean
  login(config?: { redirectUri?: string }): void
  logout(): void
  getIDToken(): string | null
  isInClient(): boolean
  closeWindow(): void
}

declare global {
  interface Window {
    liff?: Liff
  }
}

let loading: Promise<Liff> | null = null

function loadSdk(): Promise<Liff> {
  if (window.liff) return Promise.resolve(window.liff)
  loading ??= new Promise<Liff>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SDK_URL
    script.async = true
    script.onload = () => (window.liff ? resolve(window.liff) : reject(new Error('LIFF SDK did not load')))
    script.onerror = () => {
      loading = null
      reject(new Error('LIFF SDK did not load'))
    }
    document.head.appendChild(script)
  })
  return loading
}

/**
 * An ID token for whoever is using LINE, or null when LINE is sending them
 * off to log in first (the page reloads after it).
 */
export async function liffIdToken(liffId: string): Promise<string | null> {
  const liff = await loadSdk()
  await liff.init({ liffId })
  if (!liff.isLoggedIn()) {
    liff.login({ redirectUri: window.location.href })
    return null
  }
  const token = liff.getIDToken()
  // Logged in but no token: the LIFF app was made without the openid scope.
  if (!token) throw new Error('LINE gave no ID token — the LIFF app needs the openid scope')
  return token
}

/**
 * LINE refused the token we had (an ID token lasts about an hour, and a
 * page left open in a browser outlives it): sign in again for a fresh one.
 * Only once per visit, so a token LINE keeps refusing ends on the error
 * screen rather than in a loop of logins.
 */
export function liffSignInAgain(): boolean {
  const liff = window.liff
  const key = 'liff-relogin'
  try {
    if (!liff || sessionStorage.getItem(key)) return false
    sessionStorage.setItem(key, '1')
  } catch {
    return false
  }
  liff.logout()
  liff.login({ redirectUri: window.location.href })
  return true
}

export function liffSignedIn(): void {
  try {
    sessionStorage.removeItem('liff-relogin')
  } catch {
    // private mode: nothing to clear
  }
}

export async function closeLiff(): Promise<void> {
  const liff = window.liff
  if (liff?.isInClient()) liff.closeWindow()
}
