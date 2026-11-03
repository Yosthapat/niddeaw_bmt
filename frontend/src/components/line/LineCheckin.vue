<script setup lang="ts">
/**
 * After scanning tonight's QR: who they are, and one tap to check in.
 *
 * Nothing is checked in by the scan alone — a QR opened by accident, or by
 * someone holding another person's phone, shows the card first. Who is
 * checked in comes from their LINE token on the server, never from here.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineCheckinState } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { formatDateWithWeekday, formatTime } from '@/utils/format'
import type { Locale } from '@/i18n'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const props = defineProps<{
  token: string
  code: string
  initial: LineCheckinState
  /** They picked a name or signed up, and an admin hasn't confirmed yet. */
  waiting: boolean
  canScan: boolean
}>()
const emit = defineEmits<{ link: []; join: []; scan: []; done: [] }>()
const { t, locale } = useI18n()

const now = ref<LineCheckinState>(props.initial)
const sending = ref(false)
const problem = ref('')

const night = computed(() =>
  now.value.night ? formatDateWithWeekday(now.value.night.date, locale.value as Locale) : '',
)

async function checkIn(): Promise<void> {
  if (sending.value) return
  sending.value = true
  problem.value = ''
  try {
    now.value = await lineApi.checkInTonight(props.token, props.code)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineCheckin.failed'))
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <section class="flex flex-1 flex-col items-center gap-4 text-center">
    <!-- ready: their card, and the button -->
    <template v-if="now.state === 'ready' && now.player">
      <p class="world-eyebrow mt-2">TONIGHT · {{ night }}</p>
      <div class="world-card flex w-full flex-col items-center gap-2.5 px-4 py-6">
        <span class="gold-ring rounded-full">
          <PlayerAvatar :name="now.player.nickname" :avatar-url="now.player.avatar_url" size="xl" round />
        </span>
        <span class="font-display text-3xl font-bold">{{ now.player.nickname }}</span>
        <span class="inline-flex items-center gap-1.5 text-sm text-white/70">
          <TierMascot :tier="now.player.elo_level" :size="22" :interactive="false" />
          {{ now.player.member_code }}
        </span>
        <span class="text-sm text-white/60">{{ now.night?.location }}</span>
      </div>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <div class="mt-auto flex w-full flex-col gap-2">
        <button type="button" class="cta min-h-16 rounded-2xl font-display text-lg font-bold" :disabled="sending" @click="checkIn">
          {{ sending ? t('lineCheckin.sending') : t('lineCheckin.checkIn') }}
        </button>
        <p class="text-xs text-white/55">{{ t('lineCheckin.notYou', { name: now.player.nickname }) }}</p>
      </div>
    </template>

    <!-- in -->
    <template v-else-if="now.state === 'in'">
      <span class="done-ring mt-8 flex h-28 w-28 items-center justify-center rounded-full text-[#7ff0b4]" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="60" height="60" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
      </span>
      <h1 class="world-title text-3xl">{{ t('lineCheckin.doneTitle') }}</h1>
      <p class="text-white/80">
        {{ now.player?.nickname }}
        <template v-if="now.checkin_time"> · {{ formatTime(now.checkin_time, locale as Locale) }}</template>
        · {{ t('lineCheckin.doneWait') }}
      </p>
      <ul class="world-card w-full space-y-2 p-4 text-left text-sm">
        <li><span class="text-[#7ff0b4]">●</span> {{ t('lineCheckin.doneSeen') }}</li>
        <li><span class="text-white/40">●</span> {{ t('lineCheckin.doneLive') }}</li>
      </ul>
      <div class="mt-auto flex w-full flex-col gap-2">
        <RouterLink to="/live" class="glass-pill w-full justify-center">{{ t('lineCheckin.toLive') }}</RouterLink>
        <button type="button" class="min-h-11 text-sm text-white/60" @click="emit('done')">{{ t('line.close') }}</button>
      </div>
    </template>

    <!-- this LINE is nobody in the club yet -->
    <template v-else-if="now.state === 'unlinked'">
      <img src="/hero/cat-color.webp" alt="" width="130" height="130" class="mt-6 h-32 w-32 object-contain" />
      <h1 class="world-title text-2xl">{{ t('lineCheckin.unlinkedTitle') }}</h1>
      <p class="text-white/75">{{ waiting ? t('lineCheckin.waitingBody') : t('lineCheckin.unlinkedBody') }}</p>
      <div v-if="!waiting" class="mt-auto flex w-full flex-col gap-2">
        <button type="button" class="cta min-h-14 rounded-2xl font-display text-base font-bold" @click="emit('link')">
          {{ t('lineCheckin.linkMe') }}
        </button>
        <button type="button" class="glass-pill w-full justify-center" @click="emit('join')">{{ t('lineCheckin.joinMe') }}</button>
      </div>
      <button v-else type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('done')">{{ t('line.close') }}</button>
    </template>

    <!-- not tonight's QR -->
    <template v-else>
      <img src="/tiers/milk.webp" alt="" width="120" height="120" class="mt-6 h-28 w-28 object-contain opacity-90" />
      <h1 class="world-title text-2xl">{{ t('lineCheckin.expiredTitle') }}</h1>
      <p class="text-white/75">{{ t('lineCheckin.expiredBody') }}</p>
      <div class="mt-auto flex w-full flex-col gap-2">
        <button v-if="canScan" type="button" class="cta min-h-14 rounded-2xl font-display text-base font-bold" @click="emit('scan')">
          {{ t('lineCheckin.scanAgain') }}
        </button>
        <button type="button" class="glass-pill w-full justify-center" @click="emit('done')">{{ t('line.close') }}</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.gold-ring {
  box-shadow:
    0 0 0 3px #ffc94d,
    0 0 26px rgb(255 201 77 / 0.4);
}
.done-ring {
  background: rgb(127 240 180 / 0.14);
  box-shadow:
    0 0 0 2px #7ff0b4,
    0 0 40px rgb(127 240 180 / 0.35);
}
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
.cta:disabled {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
