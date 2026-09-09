import { ref } from 'vue'

export interface ConfirmOptions {
  title: string
  message: string
  danger?: boolean
}

interface ConfirmState extends ConfirmOptions {
  resolve: (value: boolean) => void
}

// Singleton module state (not Pinia — pure UI state, nothing to persist),
// mirroring useTierInfoModal.ts: any call site can open the same modal
// instance, mounted once in App.vue.
const state = ref<ConfirmState | null>(null)

export function useConfirmDialog() {
  return {
    state,
    /** Promise-based replacement for window.confirm() — resolves true/false
     * once the custom modal's confirm/cancel button (or Escape/backdrop) is
     * used. */
    confirm(options: ConfirmOptions): Promise<boolean> {
      return new Promise((resolve) => {
        state.value = { ...options, resolve }
      })
    },
    respond(value: boolean): void {
      state.value?.resolve(value)
      state.value = null
    },
  }
}
