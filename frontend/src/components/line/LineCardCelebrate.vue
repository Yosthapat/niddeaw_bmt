<script setup lang="ts">
/**
 * A new pink or black card, celebrated once when the member opens LINE:
 * the card rises out of the dark, turns once, and settles in its aura
 * while light rays turn behind it. "Keep it" puts it away, and that card
 * (its `since`) is remembered on this phone so it isn't shown again; a new
 * card later (black after pink, or a fresh one after the credit ran out)
 * is celebrated in its turn. With reduced motion it only fades in.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getCredit, type CreditCardState } from '@/api/line'
import CreditCardFace from '@/components/credit/CreditCardFace.vue'

const props = defineProps<{ token: string; name: string }>()
const { t } = useI18n()
const KEY = 'niddeaw.creditCard.seen'

const card = ref<CreditCardState | null>(null)

function seen(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

onMounted(async () => {
  try {
    const c = (await getCredit(props.token)).card
    if (c && seen() !== c.since) card.value = c
  } catch {
    // offline, or credit not set up: nothing to celebrate
  }
})

function keep(): void {
  if (card.value) {
    try {
      localStorage.setItem(KEY, card.value.since)
    } catch {
      // private mode: it may show again next time, which is harmless
    }
  }
  card.value = null
}
</script>

<template>
  <Teleport to="body">
    <div v-if="card" class="celebrate" :class="card.tier" role="dialog" aria-modal="true" :aria-label="t('creditCard.got', { card: t(`creditCard.${card.tier}`) })" @keydown.esc="keep">
      <div class="rays" aria-hidden="true" />
      <p class="world-eyebrow">{{ card.tier === 'black' ? 'BLACK CARD' : 'PINK CARD' }}</p>
      <h2 class="world-title text-3xl">{{ t('creditCard.got', { card: t(`creditCard.${card.tier}`) }) }}</h2>
      <div class="lift">
        <CreditCardFace :tier="card.tier" :name="name" :width="290" />
      </div>
      <p class="max-w-[30ch] text-center text-sm text-white/75">{{ t('creditCard.lasts') }}</p>
      <button type="button" class="keep" autofocus @click="keep">{{ t('creditCard.keep') }}</button>
    </div>
  </Teleport>
</template>

<style scoped>
.celebrate {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  overflow: hidden;
  padding: 24px max(16px, env(safe-area-inset-right, 0px)) calc(24px + env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px));
  background: radial-gradient(70% 50% at 50% 50%, rgb(60 20 70 / 0.85), rgb(8 4 12 / 0.96));
  backdrop-filter: blur(6px);
  animation: fade 0.35s ease-out both;
  text-align: center;
}
.black {
  background: radial-gradient(70% 50% at 50% 50%, rgb(50 30 90 / 0.85), rgb(4 3 8 / 0.97));
}
.rays {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 160vmax;
  height: 160vmax;
  translate: -50% -50%;
  pointer-events: none;
  background: repeating-conic-gradient(from 0deg, rgb(255 143 208 / 0.12) 0deg 8deg, transparent 8deg 24deg);
  mask: radial-gradient(closest-side, #000 20%, transparent 70%);
  animation: spin 24s linear infinite;
}
.black .rays {
  background: repeating-conic-gradient(from 0deg, rgb(242 193 78 / 0.12) 0deg 8deg, rgb(155 107 255 / 0.08) 8deg 14deg, transparent 14deg 24deg);
}
.celebrate > :not(.rays) {
  position: relative;
}
.lift {
  display: flex;
  justify-content: center;
  padding: 18px 0;
  perspective: 900px;
  animation: rise 1.4s cubic-bezier(0.2, 0.9, 0.25, 1.05) both;
}
.keep {
  min-height: 48px;
  min-width: 200px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ff8fd0, #ea4ca4);
  padding: 0 28px;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: #1a0410;
  box-shadow: 0 6px 20px rgb(234 76 164 / 0.5);
}
.black .keep {
  background: linear-gradient(180deg, #ffe39a, #f2c14e);
  color: #1a1206;
  box-shadow: 0 6px 20px rgb(242 193 78 / 0.4);
}
.keep:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 3px;
}
@keyframes fade {
  from {
    opacity: 0;
  }
}
@keyframes spin {
  to {
    rotate: 360deg;
  }
}
@keyframes rise {
  0% {
    opacity: 0;
    transform: translateY(60vh) rotateY(-180deg) scale(0.6);
  }
  60% {
    opacity: 1;
    transform: translateY(-12px) rotateY(20deg) scale(1.05);
  }
  100% {
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .rays,
  .lift {
    animation: none;
  }
}
</style>
