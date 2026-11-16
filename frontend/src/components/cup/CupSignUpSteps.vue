<script setup lang="ts">
/**
 * Where a sign-up stands, as four steps: signed up → partner accepted →
 * both paid → confirmed. Done steps are ticked, the current one lit, and
 * under the bar the one thing to do next — so nobody has to wonder whether
 * they're in yet.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  /** 0 before signing up; then the team's status. */
  status: 'none' | 'invited' | 'awaiting_payment' | 'slip_review' | 'confirmed' | 'waitlist' | string
  /** Both halves paid or slips sent — step 3 is behind them. */
  bothSent?: boolean
  role?: 'captain' | 'partner' | null
}>()
const { t } = useI18n()

const STEPS = ['signUp', 'partner', 'pay', 'confirmed'] as const
/** Index of the step being worked on now; 4 when all are done. */
const current = computed(() => {
  if (props.status === 'none') return 0
  if (props.status === 'invited') return 1
  if (props.status === 'confirmed') return 4
  if (props.bothSent || props.status === 'waitlist') return 3
  return 2
})
const next = computed(() => {
  if (props.status === 'waitlist') return t('cup.steps.next.waitlist')
  const key = ['signUp', props.role === 'partner' ? 'partnerMe' : 'partner', 'pay', 'check', 'done'][current.value]
  return t(`cup.steps.next.${key}`)
})
</script>

<template>
  <div class="rounded-2xl border border-white/12 bg-black/20 p-3">
    <ol class="grid grid-cols-4" :aria-label="t('cup.steps.label')">
      <li v-for="(s, i) in STEPS" :key="s" class="relative flex flex-col items-center gap-1 text-center" :aria-current="i === current ? 'step' : undefined">
        <!-- the line to the next step -->
        <span
          v-if="i < STEPS.length - 1"
          class="absolute top-[13px] left-1/2 h-[2px] w-full"
          :class="i < current ? 'bg-[#7ff0b4]' : 'bg-white/15'"
          aria-hidden="true"
        />
        <span
          class="relative z-[1] flex h-7 w-7 items-center justify-center rounded-full font-display text-xs font-bold"
          :class="
            i < current
              ? 'bg-[#7ff0b4] text-[#0a2a1a]'
              : i === current
                ? 'bg-[#ff6cc0] text-[#1a0838] ring-4 ring-[#ff6cc0]/25'
                : 'bg-white/10 text-white/50'
          "
        >
          <svg v-if="i < current" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg>
          <template v-else>{{ i + 1 }}</template>
        </span>
        <span class="text-[11px] leading-[1.5]" :class="i === current ? 'font-semibold text-white' : i < current ? 'text-[#7ff0b4]' : 'text-white/50'">
          {{ status === 'waitlist' && s === 'confirmed' ? t('cup.steps.waitlist') : t(`cup.steps.${s}`) }}
        </span>
      </li>
    </ol>
    <p class="mt-2.5 rounded-xl px-3 py-2 text-center text-sm" :class="current === 4 ? 'bg-[#7ff0b4]/15 font-semibold text-[#c8ffe3]' : 'bg-white/6 text-white/85'">
      {{ next }}
    </p>
  </div>
</template>
