<script setup lang="ts">
/**
 * The small pink or black card by a member's name: they
 * bought a credit pack in LINE and still have credit (1,000 pink, 5,000
 * black). Give it `playerId` and it looks the member up in the club-wide
 * list (stores/creditCards), or a `tier` directly. Nothing when there is
 * no card. No aura at this size: it only blurred the name next to it; the
 * full-size card (CreditCardFace) keeps its aura.
 */
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CardTier } from '@/api/line'
import { useCreditCardsStore } from '@/stores/creditCards'

const props = withDefaults(defineProps<{ playerId?: string | null; tier?: CardTier | null; size?: 'sm' | 'md' | 'lg' }>(), {
  playerId: null,
  tier: null,
  size: 'sm',
})
const { t } = useI18n()
const cards = useCreditCardsStore()
onMounted(() => {
  if (props.playerId) void cards.load()
})
const shown = computed<CardTier | null>(() => props.tier ?? cards.tierOf(props.playerId))
const label = computed(() => (shown.value ? t(`creditCard.${shown.value}`) : ''))
</script>

<template>
  <span v-if="shown" class="mark" :class="[shown, size]" role="img" :aria-label="label" :title="label">
    <span class="face">
      <span class="chip" />
      <img src="/credit/cat-sm.webp" alt="" width="96" height="96" />
    </span>
  </span>
</template>

<style scoped>
.mark {
  --w: 22px;
  position: relative;
  display: inline-block;
  flex: none;
  width: var(--w);
  aspect-ratio: 1.586;
  vertical-align: middle;
}
.mark.md {
  --w: 28px;
}
.mark.lg {
  --w: 44px;
}
.face {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: calc(var(--w) * 0.12);
  box-shadow:
    0 1px 3px rgb(0 0 0 / 0.6),
    inset 0 0 0 1px rgb(255 255 255 / 0.25);
}
.pink .face {
  background: linear-gradient(135deg, #ff8fd0 0%, #ff4fa6 45%, #b81f74 100%);
}
.black .face {
  background: linear-gradient(140deg, #2a2530 0%, #0b0a0e 60%, #000 100%);
  /* a thin gold edge, so the black card still reads on a dark page */
  box-shadow:
    0 1px 3px rgb(0 0 0 / 0.6),
    inset 0 0 0 1px rgb(242 193 78 / 0.7);
}
.chip {
  position: absolute;
  left: 12%;
  top: 30%;
  width: 26%;
  aspect-ratio: 1.3;
  border-radius: 2px;
  background: linear-gradient(135deg, #f7dc8a, #c9952f 55%, #f2d27a);
}
.face img {
  position: absolute;
  right: -8%;
  bottom: -18%;
  width: 70%;
  height: auto;
}
</style>
