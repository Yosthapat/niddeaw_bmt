<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { currentLocale, setLocale, type Locale } from '@/i18n'

// `glass`: round, to sit inside the public site's glass bar (AppHeader.vue).
const props = defineProps<{ glass?: boolean }>()

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
      class="flex min-h-11 items-center gap-1.5 text-xs font-semibold"
      :class="
        props.glass
          ? 'min-w-[52px] justify-center rounded-full border border-white/20 bg-white/10 px-3 text-white hover:bg-white/15'
          : 'hud-panel border border-brand-pink/25 bg-brand-surface px-2.5 text-white/70 hover:border-brand-pink/50 hover:text-white'
      "
      @click="open = !open"
    >
      <span>{{ options.find((o) => o.locale === active)?.flag }}</span>
      <span>{{ options.find((o) => o.locale === active)?.label }}</span>
    </button>

    <div
      v-if="open"
      class="absolute right-0 z-20 mt-1.5 min-w-[6.5rem] py-1 shadow-lg"
      :class="props.glass ? 'glass-bar rounded-2xl' : 'hud-panel border border-brand-pink/25 bg-brand-surface-raised'"
    >
      <button
        v-for="opt in options"
        :key="opt.locale"
        type="button"
        class="flex min-h-11 w-full items-center gap-2 px-3 text-left text-xs font-semibold transition-colors"
        :class="opt.locale === active ? 'text-brand-pink' : 'text-white/60 hover:text-white'"
        @click="choose(opt.locale)"
      >
        <span>{{ opt.flag }}</span>
        <span>{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>
