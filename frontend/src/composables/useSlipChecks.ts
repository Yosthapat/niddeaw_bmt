/**
 * What each slip's QR said (backend services/slip_check.py), fetched for
 * all the slips on screen in one request: a badge asks for its own, and the
 * asks made in the same tick go together. Kept per slip image, so a member
 * sending a new slip is read afresh.
 */
import { ref, type Ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { SlipCheck, SlipKind } from '@/api/admin'

const known = new Map<string, Ref<SlipCheck | null>>()
const queued = new Map<SlipKind, Set<string>>()
let timer: ReturnType<typeof setTimeout> | null = null

const key = (kind: SlipKind, id: string, slipUrl: string): string => `${kind}:${id}:${slipUrl}`
const latest = new Map<string, string>() // kind:id -> slip url asked for last

async function flush(): Promise<void> {
  timer = null
  const batches = [...queued.entries()]
  queued.clear()
  for (const [kind, ids] of batches) {
    const list = [...ids]
    for (let i = 0; i < list.length; i += 150) {
      const part = list.slice(i, i + 150)
      try {
        for (const c of await adminApi.getSlipChecks(kind, part)) {
          const url = latest.get(`${kind}:${c.target_id}`)
          const slot = url !== undefined ? known.get(key(kind, c.target_id, url)) : undefined
          if (slot) slot.value = c
        }
      } catch {
        // a badge that can't load says nothing, rather than something wrong
      }
    }
  }
}

export function useSlipCheck(kind: SlipKind, id: string, slipUrl: string): Ref<SlipCheck | null> {
  const k = key(kind, id, slipUrl)
  let found = known.get(k)
  if (!found) {
    found = ref<SlipCheck | null>(null)
    known.set(k, found)
    latest.set(`${kind}:${id}`, slipUrl)
    if (!queued.has(kind)) queued.set(kind, new Set())
    queued.get(kind)!.add(id)
    if (!timer) timer = setTimeout(() => void flush(), 0)
  }
  return found
}

/** After reading old slips, ask again for everything on screen. */
export function forgetSlipChecks(): void {
  known.clear()
  latest.clear()
}
