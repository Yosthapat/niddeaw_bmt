import { computed, ref } from 'vue'
import { tournamentAdmin, type Tournament } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'

/**
 * Which tournament the tournament admin screens are on. Shared by the
 * event, teams and money screens so switching on one carries to the others;
 * remembered on this device, and the newest one when nothing is.
 */
const KEY = 'niddeaw_cup_pick'
const all = ref<Tournament[]>([])
const pickedId = ref<string | null>(readPick())
const loading = ref(false)
const problem = ref('')

function readPick(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

function writePick(id: string | null): void {
  try {
    if (id) localStorage.setItem(KEY, id)
    else localStorage.removeItem(KEY)
  } catch {
    /* a private window: the pick lasts this visit */
  }
}

export function useTournamentPick() {
  const picked = computed(() => all.value.find((x) => x.id === pickedId.value) ?? all.value[0] ?? null)

  async function load(): Promise<void> {
    loading.value = true
    problem.value = ''
    try {
      all.value = await tournamentAdmin.list()
    } catch (e) {
      problem.value = apiErrorMessage(e, 'โหลดทัวร์นาเมนต์ไม่สำเร็จ')
    } finally {
      loading.value = false
    }
  }

  function pick(id: string): void {
    pickedId.value = id
    writePick(id)
  }

  /** Put a fresh copy of one tournament back into the list. */
  function replace(updated: Tournament): void {
    const i = all.value.findIndex((x) => x.id === updated.id)
    if (i >= 0) all.value.splice(i, 1, updated)
    else all.value.unshift(updated)
  }

  return { all, picked, loading, problem, load, pick, replace }
}
