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
  if (authStore.token) {
    headers.set('Authorization', `Bearer ${authStore.token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(response.status, body || response.statusText)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
