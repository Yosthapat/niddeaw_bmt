import { ref } from 'vue'
import type { EloTier } from '@/types'

// Singleton module state (not Pinia — this is pure UI state, nothing to
// persist or share across tabs) so any TierMascot instance anywhere on the
// site can open the same modal, mounted once in App.vue.
const activeTier = ref<EloTier | null>(null)

export function useTierInfoModal() {
  return {
    activeTier,
    open(tier: EloTier): void {
      activeTier.value = tier
    },
    close(): void {
      activeTier.value = null
    },
  }
}
