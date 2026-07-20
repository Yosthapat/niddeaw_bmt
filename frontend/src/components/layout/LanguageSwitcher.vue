<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { currentLocale, setLocale, type Locale } from '@/i18n'

const options: { locale: Locale; flag: string; label: string }[] = [
  { locale: 'th', flag: '🇹🇭', label: 'TH' },
  { locale: 'en', flag: '🇬🇧', label: 'EN' },
]

const open = ref(false)
const active = ref<Locale>(currentLocale())
const rootEl = ref<HTMLElement | null>(null)

function choose(locale: Locale): void {
  setLocale(locale)
  active.value = locale
  open.value = false
}

function onClickOutside(event: MouseEvent): void {
  if (rootEl.value && !rootEl.value.contains(event.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>

<template>
  <div ref="rootEl" class="relative">
    <button
      type="button"
      class="hud-panel flex items-center gap-1.5 border border-brand-pink/25 bg-brand-surface px-2.5 py-1.5 text-xs font-semibold text-white/70 hover:border-brand-pink/50 hover:text-white"
      @click="open = !open"
    >
      <span>{{ options.find((o) => o.locale === active)?.flag }}</span>
      <span>{{ options.find((o) => o.locale === active)?.label }}</span>
    </button>

    <div
      v-if="open"
      class="hud-panel absolute right-0 z-20 mt-1.5 min-w-[6.5rem] border border-brand-pink/25 bg-brand-surface-raised py-1 shadow-lg"
    >
      <button
        v-for="opt in options"
        :key="opt.locale"
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs font-semibold transition-colors"
        :class="opt.locale === active ? 'text-brand-pink' : 'text-white/60 hover:text-white'"
        @click="choose(opt.locale)"
      >
        <span>{{ opt.flag }}</span>
        <span>{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>
