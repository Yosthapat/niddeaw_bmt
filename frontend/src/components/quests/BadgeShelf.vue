<script setup lang="ts">
/**
 * A member's medals: one slot per quest, the highest level earned (or the
 * first, greyed, with a lock). Dots under each say how many levels are
 * won. Gold medals catch a sweep of light now and then. Tapping a slot
 * opens BadgeInspect, which flies the medal up from where it sits.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BadgeItem } from '@/utils/quests'
import BadgeInspect from './BadgeInspect.vue'

const props = defineProps<{ items: BadgeItem[]; title?: string }>()
const { t } = useI18n()

const earned = computed(() => props.items.filter((i) => !i.locked).length)
const open = ref<BadgeItem | null>(null)
const source = ref<HTMLElement | null>(null)

function pick(item: BadgeItem, e: MouseEvent): void {
  source.value = (e.currentTarget as HTMLElement).querySelector('.medal-wrap')
  open.value = item
}
</script>

<template>
  <section class="shelf" :aria-label="title ?? t('quests.shelf')">
    <div class="shelf-head">
      <h2 class="font-display text-base font-bold">{{ title ?? t('quests.shelf') }}</h2>
      <span class="text-xs text-white/55">{{ t('quests.count', { n: earned, total: items.length }) }}</span>
    </div>
    <div class="grid grid-cols-4 gap-x-1.5 gap-y-2">
      <button
        v-for="(item, i) in items"
        :key="item.id"
        type="button"
        class="slot"
        :class="{ locked: item.locked, gold: !item.locked && (item.metal === 'g' || item.metal === 'p') }"
        :aria-label="`${item.name} · ${item.tierLabel}`"
        @click="pick(item, $event)"
      >
        <span class="medal-wrap" :style="{ visibility: open?.id === item.id ? 'hidden' : 'visible' }">
          <img :src="item.img" alt="" width="256" height="256" decoding="async" />
          <span class="shine" :style="{ '--m': `url(${item.img})`, '--d': `${(i % 5) * 1.1}s` }" aria-hidden="true" />
          <span v-if="item.locked" class="lock" aria-hidden="true">
            <svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
          </span>
        </span>
        <span class="name">{{ item.name }}</span>
        <span class="pips" aria-hidden="true">
          <i v-for="(p, j) in item.pips" :key="j" :class="p ?? ''" />
        </span>
      </button>
    </div>
    <slot />
    <BadgeInspect :item="open" :source="source" @close="open = null" />
  </section>
</template>

<style scoped>
.shelf {
  border-radius: 22px;
  border: 1px solid rgb(255 255 255 / 0.12);
  background: linear-gradient(180deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.02));
  padding: 14px 12px 14px;
  backdrop-filter: blur(12px);
}
.shelf-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin: 0 2px 10px;
}
.slot {
  all: unset;
  cursor: pointer;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border-radius: 14px;
  padding: 4px 2px 6px;
  -webkit-tap-highlight-color: transparent;
}
.slot:focus-visible {
  outline: 2px solid #f2c14e;
  outline-offset: 2px;
}
.medal-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  transition: transform 0.18s ease;
}
.slot:hover .medal-wrap {
  transform: translateY(-2px) scale(1.04);
}
.slot:active .medal-wrap {
  transform: scale(0.94);
}
.medal-wrap img {
  display: block;
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 6px 8px rgb(0 0 0 / 0.5));
}
.slot.locked img {
  filter: grayscale(1) brightness(0.42) contrast(0.9) drop-shadow(0 4px 6px rgb(0 0 0 / 0.5));
}
.name {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  font-size: 11px;
  line-height: 1.25;
  color: rgb(255 255 255 / 0.9);
}
.slot.locked .name {
  color: rgb(255 255 255 / 0.5);
}
.pips {
  display: flex;
  height: 6px;
  gap: 3px;
}
.pips i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.16);
}
.pips i.b { background: #c98a55; }
.pips i.s { background: #dfe5ee; }
.pips i.g { background: #f2c14e; box-shadow: 0 0 6px #f2c14e; }
.pips i.p { background: #ff8fd0; box-shadow: 0 0 6px #ff8fd0; }
.shine {
  position: absolute;
  inset: 0;
  pointer-events: none;
  -webkit-mask: var(--m) center / contain no-repeat;
  mask: var(--m) center / contain no-repeat;
  background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.55) 50%, transparent 60%);
  background-size: 260% 100%;
  background-position: 150% 0;
}
.slot.gold .shine {
  animation: sweep 6s ease-in-out infinite;
  animation-delay: var(--d, 0s);
}
@keyframes sweep {
  0%, 70% { background-position: 150% 0; }
  100% { background-position: -60% 0; }
}
.lock {
  position: absolute;
  right: 4%;
  bottom: 6%;
  display: flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid rgb(255 255 255 / 0.2);
  background: #1a1424;
}
.lock svg {
  width: 12px;
  height: 12px;
  fill: none;
  stroke: rgb(255 255 255 / 0.6);
  stroke-width: 2.4;
}
@media (prefers-reduced-motion: reduce) {
  .slot.gold .shine { animation: none; }
}
</style>
