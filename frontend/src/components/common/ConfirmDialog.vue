<script setup lang="ts">
// Mounted once in App.vue, matching TierInfoModal.vue's pattern — any
// call site awaits useConfirmDialog().confirm() to pop this same instance
// up instead of the browser's native window.confirm().
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const TITLE_ID = 'confirm-dialog-title'

const { t } = useI18n()
const { state, respond } = useConfirmDialog()

const panel = ref<HTMLElement | null>(null)
const cancelButton = ref<HTMLButtonElement | null>(null)
// Whatever the admin was on before the dialog took focus, so closing puts
// them back there instead of at the top of the document.
let previouslyFocused: HTMLElement | null = null

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    respond(false)
    return
  }
  // Native confirm() traps focus for free; this one has to keep Tab from
  // wandering off into the page sitting behind the backdrop.
  if (e.key !== 'Tab' || !panel.value) return
  const focusables = panel.value.querySelectorAll<HTMLElement>('button')
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement
  const outside = !(active instanceof Node) || !panel.value.contains(active)
  if (e.shiftKey && (outside || active === first)) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && (outside || active === last)) {
    e.preventDefault()
    first.focus()
  }
}

watch(
  () => state.value !== null,
  async (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) {
      previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
      window.addEventListener('keydown', onKeydown)
      await nextTick()
      // Cancel, not confirm — the destructive button shouldn't be one
      // stray Enter away when the dialog appears.
      cancelButton.value?.focus()
    } else {
      window.removeEventListener('keydown', onKeydown)
      previouslyFocused?.focus()
      previouslyFocused = null
    }
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="tier-modal">
      <div
        v-if="state"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
        @click.self="respond(false)"
      >
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="TITLE_ID"
          class="hud-panel relative w-full max-w-sm border border-brand-pink/30 bg-brand-surface p-6"
        >
          <p :id="TITLE_ID" class="font-display text-lg font-bold text-white">{{ state.title }}</p>
          <p class="mt-2 text-sm leading-relaxed whitespace-pre-line text-white/70">{{ state.message }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button
              ref="cancelButton"
              type="button"
              class="rounded-full border border-white/20 px-4 py-1.5 text-sm text-white/70 hover:bg-white/10"
              @click="respond(false)"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="button"
              class="rounded-full px-4 py-1.5 text-sm font-semibold"
              :class="state.danger ? 'bg-status-error text-white' : 'bg-brand-pink text-brand-black'"
              @click="respond(true)"
            >
              {{ state.confirmLabel ?? t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
