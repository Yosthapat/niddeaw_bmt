import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { Session } from '@/types'

const CURRENT_SESSION_STORAGE_KEY = 'niddeaw_bmt_current_session_id'

/**
 * Shared "which session is the admin currently working" state — the
 * Check-in, Matchmaking, Match Record, and Billing admin views all operate
 * on one session at a time, so this lives in Pinia instead of being
 * re-picked on every view.
 */
export const useSessionsStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(
    localStorage.getItem(CURRENT_SESSION_STORAGE_KEY),
  )
  // Set once the very first refresh() of this store instance (i.e. this
  // page load) has picked a starting session — see the comment in
  // refresh() for why this matters.
  let hasPickedInitialSession = false

  const currentSession = computed(
    () => sessions.value.find((s) => s.id === currentSessionId.value) ?? null,
  )
  const openSessions = computed(() => sessions.value.filter((s) => s.status === 'open'))

  function setCurrentSession(sessionId: string | null): void {
    currentSessionId.value = sessionId
    if (sessionId) {
      localStorage.setItem(CURRENT_SESSION_STORAGE_KEY, sessionId)
    } else {
      localStorage.removeItem(CURRENT_SESSION_STORAGE_KEY)
    }
  }

  async function refresh(): Promise<void> {
    sessions.value = await adminApi.getSessions()
    const stillValid = sessions.value.some((s) => s.id === currentSessionId.value)

    // On the very first refresh after this store was created (i.e. the
    // admin just opened/reloaded the app), a *closed* session persisted
    // in localStorage from a previous day shouldn't come back as the
    // default — it just sits there looking "still open" until the admin
    // notices and switches manually. Bump to the newest open session (or
    // none) instead. Once that initial pick is made, later refresh()
    // calls (e.g. switching between admin tabs) leave a deliberately
    // picked closed session alone, so reviewing an old session's billing
    // still works without getting yanked back on every tab switch.
    const isStale = !hasPickedInitialSession && currentSession.value?.status === 'closed'
    if (!stillValid || isStale) {
      setCurrentSession(openSessions.value[0]?.id ?? null)
    }
    hasPickedInitialSession = true
  }

  async function createSession(input: {
    date: string
    location: string
    court_fee_per_person: number
    shuttlecock_price_per_game: number
  }): Promise<Session> {
    const session = await adminApi.createSession(input)
    sessions.value.unshift(session)
    setCurrentSession(session.id)
    return session
  }

  async function deleteSession(sessionId: string): Promise<void> {
    await adminApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      setCurrentSession(openSessions.value[0]?.id ?? null)
    }
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    openSessions,
    setCurrentSession,
    refresh,
    createSession,
    deleteSession,
  }
})
