import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

export class ApiError extends Error {
  readonly status: number
  /** Seconds the server asked us to wait, from its Retry-After header.
   * Only ever set on a 429 — null everywhere else. */
  readonly retryAfterSeconds: number | null

  constructor(status: number, message: string, retryAfterSeconds: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfterSeconds = retryAfterSeconds
  }
}

/** Retry-After as a whole number of seconds, or null if absent or in the
 * HTTP-date form the backend doesn't use. */
function retryAfter(response: Response): number | null {
  const raw = response.headers.get('Retry-After')
  if (raw === null) return null
  const seconds = Number(raw)
  return Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : null
}

// A read that fails on the way — the phone's signal dropped, the database
// connection behind the server dropped (500), or the free server was
// restarting or waking up (502/503/504 from the host in front of it) — is
// asked again a couple of times before the page says it couldn't load.
// Only reads: a write that failed may already have gone through, and
// sending it twice could bill someone twice.
const RETRY_DELAYS_MS = [800, 2500]
const RETRY_STATUSES = new Set([500, 502, 503, 504])

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  const isRead = (init.method ?? 'GET').toUpperCase() === 'GET'
  for (let attempt = 0; ; attempt++) {
    const last = !isRead || attempt >= RETRY_DELAYS_MS.length
    try {
      const response = await fetch(url, init)
      if (last || !RETRY_STATUSES.has(response.status)) return response
    } catch (e) {
      // fetch only throws when no answer came back at all — or when the
      // caller cancelled it, which is never asked again
      if (last || init.signal?.aborted || !(e instanceof TypeError)) throw e
    }
    await sleep(RETRY_DELAYS_MS[attempt])
  }
}

/**
 * Thin fetch wrapper shared by api/public.ts and api/admin.ts.
 * Attaches `Authorization: Bearer <token>` automatically when the Pinia
 * auth store holds a token — callers never handle the header themselves.
 */
async function send(path: string, options: RequestInit): Promise<Response> {
  const authStore = useAuthStore()

  const headers = new Headers(options.headers)
  // FormData sets its own multipart boundary — never force JSON on it.
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  // Remembered, because a 401 means something different depending on it:
  // with a token it's *our* token being rejected; without one it's just an
  // endpoint that wanted auth.
  const sentToken = authStore.token !== null
  if (sentToken) {
    headers.set('Authorization', `Bearer ${authStore.token}`)
  }

  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    // A token the server has rejected will be rejected again by every
    // subsequent call, so the admin is already logged out in practice —
    // they just can't tell. Until now nothing acted on that: the route
    // guard only runs on navigation, so an admin sitting on a page past
    // their token's 12-hour life got a generic error from every button
    // and no way to understand why. Drop the dead token and send them to
    // log in again.
    if (response.status === 401 && sentToken) {
      authStore.logout()
      if (router.currentRoute.value.name !== 'admin-login') {
        void router.push({ name: 'admin-login' })
      }
    }
    const body = await response.text()
    throw new ApiError(response.status, body || response.statusText, retryAfter(response))
  }
  return response
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await send(path, options)
  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

/** A file the server sends back (e.g. the backup ZIP) rather than JSON. */
export async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const response = await send(path, options)
  return response.blob()
}
