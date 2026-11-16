<script setup lang="ts">
/**
 * Niddeaw Pass › dress your profile: the frame round their picture, their
 * profile card's face, and the months-in-a-row track that earns the loyal
 * ones (backend pass_perks). A tap saves at once.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LinePass, PassCard, PassFrame } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { usePassStylesStore } from '@/stores/passStyles'
import { formatDate } from '@/utils/format'
import type { Locale } from '@/i18n'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const props = defineProps<{ token: string; data: LinePass; name: string; avatarUrl?: string | null; tier?: string }>()
const emit = defineEmits<{ saved: [LinePass] }>()
const { t, locale } = useI18n()
const styles = usePassStylesStore()

const FRAMES: { id: PassFrame; months?: number }[] = [
  { id: 'gold' },
  { id: 'neon' },
  { id: 'crown' },
  { id: 'moon', months: 3 },
  { id: 'king', months: 6 },
  { id: 'legend', months: 12 },
]
const CARDS: { id: PassCard; months?: number }[] = [{ id: 'foil' }, { id: 'diamond', months: 12 }]
const MILES = [
  { n: 3, frame: 'moon' as PassFrame, gift: 'loyalGift3' },
  { n: 6, frame: 'king' as PassFrame, gift: 'loyalGift6' },
  { n: 12, frame: 'legend' as PassFrame, gift: 'loyalGift12' },
]

const busy = ref(false)
const problem = ref('')
const justSaved = ref(false)
const running = computed(() => !!props.data.ends_at)
// What shows now: the choice, if it may be worn.
const frameOn = computed(() => (props.data.frame && props.data.frames_open.includes(props.data.frame) ? props.data.frame : null))
const cardOn = computed(() => (props.data.card && props.data.cards_open.includes(props.data.card) ? props.data.card : null))
const fill = computed(() => `${Math.min(100, (props.data.streak / 12) * 100)}%`)

function lockLabel(months?: number): string {
  return months ? `🔒 ${t('passPlus.months', { n: months })}` : `🔒 ${t('passPlus.needPass')}`
}

async function save(frame: PassFrame | null, card: PassCard | null): Promise<void> {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  justSaved.value = false
  try {
    emit('saved', await lineApi.setPassStyle(props.token, { frame, card }))
    justSaved.value = true
    void styles.load(true)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('passPlus.saveFailed'))
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="flex flex-col gap-4">
    <div class="preview">
      <PlayerAvatar :name="name" :avatar-url="avatarUrl" size="lg" round :frame="frameOn" />
      <div class="min-w-0">
        <p class="truncate font-display text-xl font-bold">{{ name }}</p>
        <p class="text-xs text-white/60">
          {{ frameOn ? t(`passPlus.frame.${frameOn}`) : t('passPlus.none') }} ·
          {{ cardOn ? t(`passPlus.card.${cardOn}`) : t('passPlus.plain') }}
        </p>
        <p v-if="justSaved" class="text-xs text-[#7ef0b0]">✓ {{ t('passPlus.saved') }}</p>
      </div>
    </div>
    <p class="-mt-2 text-xs text-white/55">{{ t('passPlus.styleSub') }}</p>

    <div>
      <h3 class="sec">{{ t('passPlus.frames') }} <small>{{ t('passPlus.framesHint') }}</small></h3>
      <div class="grid grid-cols-4 gap-2" role="radiogroup" :aria-label="t('passPlus.frames')">
        <button type="button" role="radio" class="pick" :class="{ on: !frameOn }" :aria-checked="!frameOn" :disabled="busy" @click="save(null, cardOn)">
          <span class="none" aria-hidden="true" />
          {{ t('passPlus.none') }}
        </button>
        <button
          v-for="f in FRAMES"
          :key="f.id"
          type="button"
          role="radio"
          class="pick"
          :class="{ on: frameOn === f.id, lock: !data.frames_open.includes(f.id) }"
          :aria-checked="frameOn === f.id"
          :disabled="busy || !data.frames_open.includes(f.id)"
          @click="save(f.id, cardOn)"
        >
          <PlayerAvatar :name="name" :avatar-url="avatarUrl" size="sm" round :frame="f.id" />
          <span>{{ t(`passPlus.frame.${f.id}`) }}</span>
          <span v-if="!data.frames_open.includes(f.id)" class="text-[10px] text-[#ffe58a]">{{ lockLabel(f.months) }}</span>
        </button>
      </div>
    </div>

    <div>
      <h3 class="sec">{{ t('passPlus.cards') }}</h3>
      <div class="grid grid-cols-3 gap-2" role="radiogroup" :aria-label="t('passPlus.cards')">
        <button type="button" role="radio" class="pick" :class="{ on: !cardOn }" :aria-checked="!cardOn" :disabled="busy" @click="save(frameOn, null)">
          <span class="mini plain"><img :src="`/tiers/${tier ?? 'beer'}.webp`" alt="" /></span>
          {{ t('passPlus.plain') }}
        </button>
        <button
          v-for="c in CARDS"
          :key="c.id"
          type="button"
          role="radio"
          class="pick"
          :class="{ on: cardOn === c.id, lock: !data.cards_open.includes(c.id) }"
          :aria-checked="cardOn === c.id"
          :disabled="busy || !data.cards_open.includes(c.id)"
          @click="save(frameOn, c.id)"
        >
          <span class="mini" :class="c.id"><span class="core"><img :src="`/tiers/${tier ?? 'beer'}.webp`" alt="" /></span></span>
          <span>{{ t(`passPlus.card.${c.id}`) }}</span>
          <span v-if="!data.cards_open.includes(c.id)" class="text-[10px] text-[#ffe58a]">{{ lockLabel(c.months) }}</span>
        </button>
      </div>
    </div>

    <div>
      <h3 class="sec">{{ t('passPlus.loyalTitle') }} <small>{{ t('passPlus.loyalHint') }}</small></h3>
      <div class="track">
        <div class="flex items-baseline justify-between text-sm text-white/75">
          <span>{{ t('passPlus.loyalNow') }}</span>
          <span><b class="font-display text-2xl text-[#ffe58a]">{{ data.streak }}</b> / 12</span>
        </div>
        <div class="bar" aria-hidden="true">
          <span class="fill" :style="{ width: fill }" />
          <span v-for="m in MILES" :key="m.n" class="dot" :class="{ hit: data.best_streak >= m.n }" :style="{ left: `${(m.n / 12) * 100}%` }" />
        </div>
        <div class="mt-4 grid grid-cols-3 gap-2">
          <div v-for="m in MILES" :key="m.n" class="mile" :class="{ done: data.best_streak >= m.n }">
            <PlayerAvatar :name="name" :avatar-url="avatarUrl" size="sm" round :frame="m.frame" />
            <b>{{ t('passPlus.months', { n: m.n }) }}</b>
            <span>{{ t(`passPlus.${m.gift}`) }}</span>
            <em>{{ data.best_streak >= m.n ? t('passPlus.loyalDone') : t('passPlus.loyalLeft', { n: m.n - data.streak }) }}</em>
          </div>
        </div>
        <p v-if="running && data.ends_at" class="mt-3 text-center text-xs text-[#ffe58a]">
          {{ t('passPlus.loyalRenewBy', { when: formatDate(data.ends_at, locale as Locale) }) }}
        </p>
        <p class="mt-2 text-center text-[11px] leading-relaxed text-white/50">{{ t('passPlus.loyalRule') }}</p>
      </div>
    </div>

    <p v-if="problem" role="alert" class="text-sm text-status-error">{{ problem }}</p>
  </section>
</template>

<style scoped>
.preview {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 20px;
  background: linear-gradient(160deg, rgb(255 255 255 / 0.07), rgb(255 255 255 / 0.02));
}
.sec {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 2px 8px;
  font-size: 14px;
  font-weight: 700;
}
.sec small {
  color: rgb(255 255 255 / 0.5);
  font-size: 11px;
  font-weight: 400;
}
.pick {
  position: relative;
  display: flex;
  min-height: 96px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 4px 8px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 16px;
  background: rgb(255 255 255 / 0.05);
  color: rgb(255 255 255 / 0.82);
  font-size: 10.5px;
  line-height: 1.25;
  text-align: center;
}
.pick.on {
  border-color: #ffe58a;
  background: rgb(242 193 78 / 0.13);
  color: #ffe8a3;
  box-shadow:
    0 0 0 1px #ffe58a inset,
    0 6px 18px -6px rgb(242 193 78 / 0.6);
}
.pick.on::after {
  content: '✓';
  position: absolute;
  top: 5px;
  right: 8px;
  color: #ffe58a;
  font-weight: 800;
}
.pick.lock {
  opacity: 0.7;
}
.pick.lock :deep(.pf) {
  filter: grayscale(0.6) brightness(0.8);
}
.none {
  width: 32px;
  height: 32px;
  border: 2px dashed rgb(255 255 255 / 0.3);
  border-radius: 9999px;
}
.mini {
  position: relative;
  display: grid;
  width: 54px;
  height: 72px;
  overflow: hidden;
  place-items: center;
  border-radius: 9px;
}
.mini img {
  width: 40px;
}
.mini.plain {
  border: 2px solid #c9952f;
  background: radial-gradient(circle at 50% 40%, #4a2a10, #1a0d22);
}
.mini.foil {
  background: conic-gradient(from 210deg, #fff3b0, #f2c14e, #ff8fd0, #8ff7ff, #b88cff, #ffe58a, #fff3b0);
}
.mini.diamond {
  background: conic-gradient(from 210deg, #fff, #8ff7ff, #b88cff, #e8fbff, #8fffc1, #ff8fd0, #fff);
}
.mini .core {
  position: absolute;
  inset: 2px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: radial-gradient(circle at 50% 35%, #5a3a0e, #1a0d22 70%);
}
.mini.diamond .core {
  background: radial-gradient(circle at 50% 35%, #1d4a5e, #130d26 70%);
}
.mini .core::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(115deg, transparent 30%, rgb(255 255 255 / 0.35) 42%, rgb(143 247 255 / 0.25) 48%, transparent 62%);
  mix-blend-mode: screen;
}
.track {
  padding: 16px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 20px;
  background: linear-gradient(160deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.02));
}
.bar {
  position: relative;
  height: 8px;
  margin: 14px 8px 0;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.1);
}
.fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #f2c14e, #ffe58a);
  box-shadow: 0 0 10px rgb(242 193 78 / 0.7);
}
.dot {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border: 2px solid rgb(255 255 255 / 0.35);
  border-radius: 9999px;
  background: #2a1440;
  translate: -50% -50%;
}
.dot.hit {
  border-color: #ffe58a;
  background: #f2c14e;
}
.mile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 6px 10px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 16px;
  background: rgb(255 255 255 / 0.05);
  text-align: center;
}
.mile.done {
  border-color: rgb(242 193 78 / 0.55);
  background: rgb(242 193 78 / 0.1);
}
.mile b {
  font-size: 13px;
}
.mile span {
  color: rgb(255 255 255 / 0.62);
  font-size: 10.5px;
  line-height: 1.35;
}
.mile em {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.08);
  color: rgb(255 255 255 / 0.72);
  font-size: 10px;
  font-style: normal;
}
.mile.done em {
  color: #ffe8a3;
}
</style>
