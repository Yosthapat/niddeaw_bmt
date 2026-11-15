import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_STORAGE_KEY = 'niddeaw_bmt_token'

interface JwtPayload {
  exp?: number
  [key: string]: unknown
}

/**
 * Decodes a JWT's payload segment client-side (base64url) without a library.
 * Only used to check `exp` for UX (hide/redirect before an obviously-expired
 * request). The server always re-verifies the signature independently.
 */
function decodeJwtPayload(token: string): JwtPayload | null {
  const segments = token.split('.')
  if (segments.length !== 3) return null

  try {
    const base64url = segments[1]
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const json = atob(padded)
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}

function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return true
  const nowInSeconds = Date.now() / 1000
  return payload.exp <= nowInSeconds
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_STORAGE_KEY))

  const isAuthenticated = computed(() => {
    return token.value !== null && !isTokenExpired(token.value)
  })

  // The two separate rights the token carries (backend security.py). A
  // token from before they existed has neither claim: the club only. These
  // only choose what to show — every route checks them again on the server.
  const claims = computed(() => (token.value ? decodeJwtPayload(token.value) : null))
  const canClub = computed(() => claims.value?.club !== false)
  const canTournament = computed(() => claims.value?.tour === true)
  /** Where an admin lands: the club if they may run it, else the tournament. */
  const home = computed(() => (canClub.value ? '/admin' : '/admin/tournament'))

  function login(newToken: string): void {
    token.value = newToken
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken)
  }

  function logout(): void {
    token.value = null
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }

  return { token, isAuthenticated, canClub, canTournament, home, login, logout }
})
