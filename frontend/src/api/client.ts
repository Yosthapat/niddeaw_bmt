import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Thin fetch wrapper shared by api/public.ts and api/admin.ts.
 * Attaches `Authorization: Bearer <token>` automatically when the Pinia
 * auth store holds a token — callers never handle the header themselves.
 */
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

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
    throw new ApiError(response.status, body || response.statusText)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
