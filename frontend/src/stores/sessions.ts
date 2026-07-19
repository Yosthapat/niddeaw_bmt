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
    // Default to the most recent open session if nothing (valid) is selected.
    const stillValid = sessions.value.some((s) => s.id === currentSessionId.value)
    if (!stillValid) {
      setCurrentSession(openSessions.value[0]?.id ?? null)
    }
  }

  async function createSession(input: {
    date: string
    location: string
    rate_per_hour: number
  }): Promise<Session> {
    const session = await adminApi.createSession(input)
    sessions.value.unshift(session)
    setCurrentSession(session.id)
    return session
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    openSessions,
    setCurrentSession,
    refresh,
    createSession,
  }
})
