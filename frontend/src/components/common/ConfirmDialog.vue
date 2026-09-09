<script setup lang="ts">
// Mounted once in App.vue, matching TierInfoModal.vue's pattern — any
// call site awaits useConfirmDialog().confirm() to pop this same instance
// up instead of the browser's native window.confirm().
import { onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const { t } = useI18n()
const { state, respond } = useConfirmDialog()

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') respond(false)
}

watch(
  () => state.value !== null,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
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
        <div class="hud-panel relative w-full max-w-sm border border-brand-pink/30 bg-brand-surface p-6">
          <p class="font-display text-lg font-bold text-white">{{ state.title }}</p>
          <p class="mt-2 text-sm leading-relaxed whitespace-pre-line text-white/70">{{ state.message }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button
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
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
