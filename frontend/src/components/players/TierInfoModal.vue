<script setup lang="ts">
// Mounted once in App.vue. Any TierMascot on the site opens this same
// instance via useTierInfoModal() — clicking a mascot anywhere (home page
// tier strip, ranking rows, member table, profile page) pops up a big
// version of it plus an in-character blurb.
import { computed, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { tierMeta, tierTextStyle } from '@/composables/useEloTier'
import { useTierInfoModal } from '@/composables/useTierInfoModal'
import TierMascot from './TierMascot.vue'
import TypewriterText from '@/components/common/TypewriterText.vue'

const { t } = useI18n()
const { activeTier, close } = useTierInfoModal()

const meta = computed(() => (activeTier.value ? tierMeta(activeTier.value) : null))
const blurb = computed(() => (activeTier.value ? t(`tierInfo.${activeTier.value}`) : ''))

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') close()
}

watch(activeTier, (tier) => {
  document.body.style.overflow = tier ? 'hidden' : ''
  if (tier) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="tier-modal">
      <div
        v-if="meta"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
        @click.self="close"
      >
        <div class="hud-panel relative w-full max-w-sm border border-brand-pink/30 bg-brand-surface p-6 text-center">
          <button
            type="button"
            class="absolute top-3 right-3 text-white/40 hover:text-brand-pink"
            :aria-label="t('tierInfo.close')"
            @click="close"
          >
            ✕
          </button>

          <div class="mascot-bounce-in mx-auto w-fit">
            <TierMascot :tier="meta.tier" :size="140" />
          </div>

          <p
            class="mt-4 font-display text-2xl font-bold tracking-wide uppercase"
            :class="{ 'tier-shimmer': meta.gradient }"
            :style="tierTextStyle(meta.colorVar, meta.gradient)"
          >
            {{ meta.label }}
          </p>

          <p class="mt-3 min-h-32 text-sm leading-relaxed whitespace-pre-line text-white/80">
            <TypewriterText :text="blurb" />
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
