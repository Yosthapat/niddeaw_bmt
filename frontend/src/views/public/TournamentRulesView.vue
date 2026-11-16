<script setup lang="ts">
/**
 * The rule book: every rule of the tournament in one place, a chapter at a
 * time, opened from the button on /tournament and the LINE page. Each
 * chapter leads with the one line most people need, then the detail. The
 * numbers — fees, coupons, prices, rest, the levels and their sizes — are
 * the tournament's own settings, so the book never says what the day won't do.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getPublicTournament, type PublicLevel, type PublicTournament } from '@/api/tournament'
import { formatDateTime, formatDateWithWeekday, money } from '@/utils/format'
import type { Locale } from '@/i18n'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

const { t, locale } = useI18n()
const router = useRouter()
/** Back to where they came from — the LINE page or /tournament — else /tournament. */
function back(): void {
  if (window.history.state?.back) router.back()
  else void router.push('/tournament')
}
const cup = ref<PublicTournament | null>(null)
const loaded = ref(false)
onMounted(async () => {
  try {
    cup.value = await getPublicTournament()
  } finally {
    loaded.value = true
  }
})

const perPlayer = computed(() => (cup.value ? Math.ceil((cup.value.entry_fee + cup.value.shuttle_fee) / 2) : 0))
const when = (iso: string): string => formatDateTime(iso, locale.value as Locale)
const day = (iso: string): string => formatDateWithWeekday(iso, locale.value as Locale)

function range(lv: PublicLevel): string {
  if (lv.min_elo === null && lv.max_elo !== null) return t('cup.eloBelow', { n: lv.max_elo })
  if (lv.min_elo !== null && lv.max_elo === null) return t('cup.eloFrom', { n: lv.min_elo })
  if (lv.min_elo !== null && lv.max_elo !== null) return `ELO ${lv.min_elo}–${lv.max_elo - 1}`
  return t('cup.admin.eloAny')
}
function bracketsOf(lv: PublicLevel): string {
  if (lv.max_teams === 24) return lv.cut_24 ? t('cup.admin.br24cut') : t('cup.admin.br24')
  return t('cup.admin.brEven', { n: lv.max_teams / 2 })
}
/** Levels that share a format, said once: four levels of 16 make one line. */
const formats = computed(() => {
  const out: { key: string; names: string[]; level: PublicLevel }[] = []
  for (const lv of cup.value?.levels ?? []) {
    const key = `${lv.max_teams}-${lv.max_teams === 24 && lv.cut_24}`
    const same = out.find((f) => f.key === key)
    if (same) same.names.push(lv.name)
    else out.push({ key, names: [lv.name], level: lv })
  }
  return out
})
function whoGoesWhere(lv: PublicLevel): string {
  if (lv.max_teams === 24) return lv.cut_24 ? t('cup.rules.ko.where24cut') : t('cup.rules.ko.where24')
  return t('cup.rules.ko.whereEven')
}

const CHAPTERS = [
  { id: 'entry', icon: 'M9 7h6M9 11h6M9 15h4M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z' },
  { id: 'levels', icon: 'M4 20V10M10 20V4M16 20v-7M22 20H2' },
  { id: 'groups', icon: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
  { id: 'ko', icon: 'M4 6h5v4H4zM4 14h5v4H4zM15 10h5v4h-5zM9 8h3v8H9M12 12h3' },
  { id: 'day', icon: 'M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z' },
  { id: 'court', icon: 'M3 4h18v16H3zM3 12h18M12 4v16' },
  { id: 'coupons', icon: 'M3 8a2 2 0 0 0 0 4v4h18v-4a2 2 0 0 0 0-4V4H3zM9 4v12' },
] as const
function jump(id: string): void {
  menuOpen.value = false
  document.getElementById(`rule-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/* The contents sit at the top as a grid that fits a phone without sliding
 * sideways. Once it scrolls away, a small button stays at the top saying
 * which chapter this is ("3/7 รอบแบ่งกลุ่ม"); a tap opens the whole list. */
const contents = ref<HTMLElement | null>(null)
const contentsGone = ref(false)
const active = ref<string>(CHAPTERS[0].id)
const activeIndex = computed(() => CHAPTERS.findIndex((c) => c.id === active.value))
const menuOpen = ref(false)
let watchers: IntersectionObserver[] = []
function observe(): void {
  watchers.forEach((w) => w.disconnect())
  watchers = []
  if (contents.value) {
    const w = new IntersectionObserver(([e]) => {
      contentsGone.value = !e.isIntersecting && e.boundingClientRect.top < 0
      if (!contentsGone.value) menuOpen.value = false
    })
    w.observe(contents.value)
    watchers.push(w)
  }
  // the chapter crossing a line a third of the way down the screen is "this one"
  const w = new IntersectionObserver(
    (entries) => {
      for (const e of entries) if (e.isIntersecting) active.value = e.target.id.replace('rule-', '')
    },
    { rootMargin: '-30% 0px -65% 0px' },
  )
  for (const c of CHAPTERS) {
    const el = document.getElementById(`rule-${c.id}`)
    if (el) w.observe(el)
  }
  watchers.push(w)
}
watch(cup, () => void nextTick(observe))
const onKey = (e: KeyboardEvent): void => {
  if (e.key === 'Escape') menuOpen.value = false
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  watchers.forEach((w) => w.disconnect())
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <main class="relative isolate overflow-x-clip">
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="absolute inset-0 bg-[radial-gradient(80%_40%_at_50%_0%,#5a1a7a_0%,#1a0838_55%,#0a0416_85%)]" />
    </div>
    <div class="mx-auto flex max-w-2xl flex-col gap-4 px-4 pt-4 pb-14">
      <button type="button" class="inline-flex min-h-11 items-center gap-1 self-start text-sm text-white/75 hover:text-white" @click="back">
        <span aria-hidden="true">←</span> NIDDEAW CUP
      </button>

      <header class="flex items-center gap-3">
        <span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#ffe14d]/15 ring-1 ring-[#ffe14d]/40">
          <svg viewBox="0 0 24 24" fill="none" stroke="#ffe14d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-8 w-8" aria-hidden="true">
            <path d="M4 5a2 2 0 0 1 2-2h6v18H6a2 2 0 0 0-2 2zM20 5a2 2 0 0 0-2-2h-6v18h6a2 2 0 0 1 2 2z" />
          </svg>
        </span>
        <div class="min-w-0">
          <h1 class="font-display text-2xl leading-tight font-bold">{{ t('cup.rules.title') }}</h1>
          <p v-if="cup" class="truncate text-sm text-white/70">{{ cup.name }} · {{ day(cup.starts_on) }}</p>
        </div>
      </header>

      <template v-if="!loaded">
        <HudSkeletonBlock class="h-12" />
        <HudSkeletonBlock v-for="i in 3" :key="i" class="h-40" :delay="i * 80" />
      </template>

      <section v-else-if="!cup" class="r-card text-center text-sm text-white/70">{{ t('cup.rules.none') }}</section>

      <template v-else>
        <!-- the chapters, one tap away: a grid that fits without sliding sideways -->
        <nav ref="contents" class="r-card !gap-2 !p-3" :aria-label="t('cup.rules.contents')">
          <p class="px-1 text-xs font-semibold tracking-wide text-white/55">{{ t('cup.rules.contents') }}</p>
          <ol class="grid grid-cols-4 gap-1.5 sm:grid-cols-7">
            <li v-for="(c, i) in CHAPTERS" :key="c.id">
              <button
                type="button"
                class="flex h-full min-h-[76px] w-full flex-col items-center justify-center gap-1 rounded-xl bg-white/5 px-1 py-2 text-center hover:bg-white/10"
                @click="jump(c.id)"
              >
                <span class="relative flex h-8 w-8 items-center justify-center rounded-full bg-[#ffe14d]/12">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#ffe14d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-[18px] w-[18px]" aria-hidden="true"><path :d="c.icon" /></svg>
                  <span class="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#ffe14d] font-display text-[10px] font-bold text-[#1a0838]">{{ i + 1 }}</span>
                </span>
                <span class="text-[12px] leading-[1.5] text-white/85">{{ t(`cup.rules.${c.id}.title`) }}</span>
              </button>
            </li>
          </ol>
        </nav>

        <!-- once the grid is gone: which chapter this is, and the list a tap away -->
        <Transition name="r-float">
          <div v-if="contentsGone" class="fixed top-[calc(var(--header-h)+8px)] left-1/2 z-30 w-[min(92vw,420px)] -translate-x-1/2">
            <button
              type="button"
              class="flex min-h-11 w-full items-center gap-2 rounded-full border border-white/15 bg-[#1a0838]/95 px-4 text-left text-sm shadow-lg backdrop-blur"
              :aria-expanded="menuOpen"
              aria-controls="rule-menu"
              @click="menuOpen = !menuOpen"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="#ffe14d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0" aria-hidden="true"><path :d="CHAPTERS[activeIndex].icon" /></svg>
              <span class="font-display text-xs text-[#ffe14d]">{{ activeIndex + 1 }}/{{ CHAPTERS.length }}</span>
              <span class="min-w-0 flex-1 truncate font-semibold">{{ t(`cup.rules.${active}.title`) }}</span>
              <span class="shrink-0 text-xs text-white/55">{{ t('cup.rules.contents') }}</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="h-4 w-4 shrink-0 text-white/60 transition-transform" :class="menuOpen ? 'rotate-180' : ''" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
            </button>
            <ol v-if="menuOpen" id="rule-menu" class="mt-1.5 overflow-hidden rounded-2xl border border-white/15 bg-[#1a0838]/97 p-1 shadow-2xl backdrop-blur">
              <li v-for="(c, i) in CHAPTERS" :key="c.id">
                <button
                  type="button"
                  class="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm"
                  :class="c.id === active ? 'bg-[#ffe14d]/12 font-semibold text-white' : 'text-white/80 hover:bg-white/8'"
                  :aria-current="c.id === active ? 'location' : undefined"
                  @click="jump(c.id)"
                >
                  <span class="w-4 text-center font-display text-xs text-[#ffe14d]">{{ i + 1 }}</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 shrink-0 text-white/60" aria-hidden="true"><path :d="c.icon" /></svg>
                  {{ t(`cup.rules.${c.id}.title`) }}
                </button>
              </li>
            </ol>
          </div>
        </Transition>
        <div v-if="menuOpen" class="fixed inset-0 z-20" aria-hidden="true" @click="menuOpen = false" />

        <!-- 1 · entering -->
        <section id="rule-entry" class="r-card">
          <h2 class="r-head"><span class="r-num">1</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[0].icon" /></svg>{{ t('cup.rules.entry.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.entry.gist', { amount: money(perPlayer) }) }}</p>
          <div class="grid grid-cols-2 gap-2">
            <div class="r-stat"><span>{{ t('cup.rules.entry.fee') }}</span><b>{{ money(perPlayer) }}</b><small>{{ t('cup.rules.entry.feeNote', { entry: money(cup.entry_fee), shuttle: money(cup.shuttle_fee) }) }}</small></div>
            <div class="r-stat"><span>{{ t('cup.rules.entry.closes') }}</span><b class="text-[17px]">{{ when(cup.closes_at) }}</b></div>
          </div>
          <ul class="r-list">
            <li>{{ t('cup.rules.entry.who', { n: cup.min_games }) }}</li>
            <li>{{ t('cup.rules.entry.pair') }}</li>
            <li>{{ t('cup.rules.entry.pay') }}</li>
            <li>{{ t('cup.rules.entry.full') }}</li>
            <li>{{ t('cup.rules.entry.withdraw') }}</li>
          </ul>
        </section>

        <!-- 2 · levels -->
        <section id="rule-levels" class="r-card">
          <h2 class="r-head"><span class="r-num">2</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[1].icon" /></svg>{{ t('cup.rules.levels.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.levels.gist') }}</p>
          <ul class="grid gap-1.5 sm:grid-cols-2">
            <li v-for="lv in cup.levels" :key="lv.id" class="rounded-xl bg-white/6 px-3 py-2.5">
              <p class="flex items-baseline gap-2"><b class="font-display">{{ lv.name }}</b><span class="text-xs text-white/60">{{ range(lv) }}</span></p>
              <p class="mt-0.5 text-xs text-white/60">
                {{ t('cup.rules.levels.size', { n: lv.max_teams }) }}
                <span v-if="lv.rules" class="ml-1 rounded-full bg-[#ffd34d]/15 px-2 py-0.5 text-[#ffd34d]">{{ lv.rules }}</span>
              </p>
            </li>
          </ul>
          <ul class="r-list">
            <li>{{ t('cup.rules.levels.stronger') }}</li>
            <li>{{ t('cup.rules.levels.one') }}</li>
            <li>{{ t('cup.rules.levels.noElo') }}</li>
          </ul>
        </section>

        <!-- 3 · groups -->
        <section id="rule-groups" class="r-card">
          <h2 class="r-head"><span class="r-num">3</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[2].icon" /></svg>{{ t('cup.rules.groups.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.groups.gist') }}</p>
          <ul class="r-list">
            <li>{{ t('cup.rules.groups.draw') }}</li>
            <li>{{ t('cup.rules.groups.sameName') }}</li>
            <li>{{ t('cup.rules.groups.everyone') }}</li>
          </ul>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="r-chip"><b>2</b>{{ t('cup.rules.groups.sets') }}</div>
            <div class="r-chip"><b>21</b>{{ t('cup.rules.groups.points') }}</div>
            <div class="r-chip"><b>{{ t('cup.rules.groups.noDeuceShort') }}</b>{{ t('cup.rules.groups.noDeuce') }}</div>
          </div>
          <p class="text-sm text-white/75">{{ t('cup.rules.groups.drawOk') }}</p>
          <div>
            <p class="mb-1.5 text-xs font-semibold text-white/60">{{ t('cup.rules.groups.scoring') }}</p>
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="r-chip !border-[#7ff0b4]/40"><b class="text-[#7ff0b4]">2</b>{{ t('cup.rules.groups.win') }}</div>
              <div class="r-chip"><b>1</b>{{ t('cup.rules.groups.tie') }}</div>
              <div class="r-chip"><b class="text-white/60">0</b>{{ t('cup.rules.groups.loss') }}</div>
            </div>
          </div>
          <div>
            <p class="mb-1.5 text-xs font-semibold text-white/60">{{ t('cup.rules.groups.tiebreak') }}</p>
            <ol class="flex flex-col gap-1 text-sm">
              <li v-for="(k, i) in ['tb1', 'tb2', 'tb3', 'tb4', 'tb5']" :key="k" class="flex items-center gap-2">
                <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 font-display text-xs">{{ i + 1 }}</span>
                {{ t(`cup.rules.groups.${k}`) }}
              </li>
            </ol>
          </div>
        </section>

        <!-- 4 · knockout -->
        <section id="rule-ko" class="r-card">
          <h2 class="r-head"><span class="r-num">4</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[3].icon" /></svg>{{ t('cup.rules.ko.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.ko.gist') }}</p>
          <!-- who goes where, per level -->
          <ul class="flex flex-col gap-1.5">
            <li v-for="f in formats" :key="f.key" class="rounded-xl bg-white/6 px-3 py-2.5 text-sm">
              <b class="font-display">{{ formats.length === 1 && cup.levels.length > 1 ? t('cup.rules.ko.allLevels') : f.names.join(' · ') }}</b>
              <span class="text-xs text-white/60"> · {{ t('cup.rules.levels.size', { n: f.level.max_teams }) }} · {{ bracketsOf(f.level) }}</span>
              <p class="mt-0.5 text-xs text-white/70">{{ whoGoesWhere(f.level) }}</p>
            </li>
          </ul>
          <!-- the draw, drawn -->
          <div class="rounded-xl border border-white/10 p-3">
            <p class="mb-2 text-xs font-semibold text-white/60">{{ t('cup.rules.ko.drawTitle') }}</p>
            <div class="flex items-center gap-2 text-sm">
              <span class="r-seed border-[#ffe14d]/50 text-[#ffe14d]">{{ t('cup.rules.ko.seed') }}</span>
              <span class="font-display text-xs text-[#ff6cc0]">VS</span>
              <span class="r-seed border-dashed border-white/30 text-white/80">{{ t('cup.rules.ko.drawn') }}</span>
            </div>
            <p class="mt-2 text-xs text-white/65">{{ t('cup.rules.ko.drawHow') }}</p>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="r-chip"><b>2/3</b>{{ t('cup.rules.ko.bestOf') }}</div>
            <div class="r-chip"><b>21</b>{{ t('cup.rules.groups.points') }}</div>
            <div class="r-chip"><b>30</b>{{ t('cup.rules.ko.cap') }}</div>
          </div>
          <ul class="r-list">
            <li>{{ t('cup.rules.ko.deuce') }}</li>
            <li>{{ t('cup.rules.ko.out') }}</li>
            <li>{{ t('cup.rules.ko.champions') }}</li>
          </ul>
        </section>

        <!-- 5 · the day -->
        <section id="rule-day" class="r-card">
          <h2 class="r-head"><span class="r-num">5</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[4].icon" /></svg>{{ t('cup.rules.day.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.day.gist') }}</p>
          <ul class="r-list">
            <li>{{ t('cup.rules.day.times') }}</li>
            <li>{{ t('cup.rules.day.rest', { n: cup.rest_minutes }) }}</li>
            <li class="!text-[#ffb3c7]">{{ t('cup.rules.day.walkover') }}</li>
            <li>{{ t('cup.rules.day.score') }}</li>
          </ul>
        </section>

        <!-- 6 · on court: play and spirit -->
        <section id="rule-court" class="r-card">
          <h2 class="r-head"><span class="r-num">6</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[5].icon" /></svg>{{ t('cup.rules.court.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.court.gist') }}</p>
          <div class="grid grid-cols-2 gap-2 text-center">
            <div class="r-chip"><b>3 {{ t('cup.rules.court.min') }}</b>{{ t('cup.rules.court.warmupShort') }}</div>
            <div class="r-chip"><b>2 × / 10 {{ t('cup.rules.court.min') }}</b>{{ t('cup.rules.court.injuryShort') }}</div>
          </div>
          <ul class="r-list">
            <li>{{ t('cup.rules.court.warmup') }}</li>
            <li>{{ t('cup.rules.court.injury') }}</li>
            <li>{{ t('cup.rules.court.stray') }}</li>
            <li>{{ t('cup.rules.court.inOut') }}</li>
          </ul>
          <p class="rounded-xl border border-[#7ff0b4]/30 bg-[#7ff0b4]/10 px-3 py-2.5 text-sm text-[#c8ffe3]">{{ t('cup.rules.court.spirit') }}</p>
        </section>

        <!-- 7 · shuttles and coupons -->
        <section id="rule-coupons" class="r-card">
          <h2 class="r-head"><span class="r-num">7</span><svg viewBox="0 0 24 24" class="r-icon" aria-hidden="true"><path :d="CHAPTERS[6].icon" /></svg>{{ t('cup.rules.coupons.title') }}</h2>
          <p class="r-gist">{{ t('cup.rules.coupons.gist', { n: cup.coupons_per_set }) }}</p>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="r-chip"><b>{{ cup.coupons_per_set }}</b>{{ t('cup.rules.coupons.given') }}</div>
            <div class="r-chip"><b>{{ money(cup.extra_set_price) }}</b>{{ t('cup.rules.coupons.extra') }}</div>
            <div class="r-chip"><b>{{ money(cup.coupon_refund_price) }}</b>{{ t('cup.rules.coupons.back') }}</div>
          </div>
          <ul class="r-list">
            <li>{{ t('cup.rules.coupons.perShuttle') }}</li>
            <li>{{ t('cup.rules.coupons.start') }}</li>
            <li>{{ t('cup.rules.coupons.returned') }}</li>
            <li>{{ t('cup.rules.coupons.buy', { price: money(cup.extra_set_price), n: cup.coupons_per_set }) }}</li>
            <li>{{ t('cup.rules.coupons.refund', { price: money(cup.coupon_refund_price) }) }}</li>
          </ul>
        </section>

        <button type="button" class="flex min-h-12 items-center justify-center rounded-full border border-white/15 text-sm text-white/85" @click="back">
          ← {{ t('cup.rules.back') }}
        </button>
      </template>
    </div>
  </main>
</template>

<style scoped>
.r-float-enter-active,
.r-float-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.r-float-enter-from,
.r-float-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.r-card {
  display: flex;
  scroll-margin-top: calc(var(--header-h) + 64px);
  flex-direction: column;
  gap: 12px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 18px;
  background: rgb(255 255 255 / 0.06);
  padding: 16px;
  backdrop-filter: blur(10px);
}
.r-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Chakra Petch', sans-serif;
  font-size: 18px;
  font-weight: 700;
}
.r-num {
  display: flex;
  height: 26px;
  width: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #ffe14d;
  color: #2a1a00;
  font-size: 14px;
}
.r-icon {
  height: 20px;
  width: 20px;
  fill: none;
  stroke: #ff6cc0;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* the one line to remember, before the detail */
.r-gist {
  border-left: 3px solid #ff6cc0;
  border-radius: 4px;
  background: rgb(255 108 192 / 0.1);
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 600;
}
.r-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  color: rgb(255 255 255 / 0.82);
}
.r-list li {
  position: relative;
  padding-left: 16px;
}
.r-list li::before {
  position: absolute;
  top: 0.62em;
  left: 2px;
  height: 6px;
  width: 6px;
  border-radius: 999px;
  background: #ff6cc0;
  content: '';
}
.r-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-radius: 14px;
  background: rgb(0 0 0 / 0.25);
  padding: 10px 12px;
}
.r-stat span {
  font-size: 12px;
  color: rgb(255 255 255 / 0.6);
}
.r-stat b {
  font-family: 'Chakra Petch', sans-serif;
  font-size: 22px;
  line-height: 1.15;
}
.r-stat small {
  font-size: 11px;
  color: rgb(255 255 255 / 0.5);
}
.r-chip {
  display: flex;
  flex-direction: column;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 12px;
  padding: 8px 4px;
  font-size: 11px;
  color: rgb(255 255 255 / 0.65);
}
.r-chip b {
  font-family: 'Chakra Petch', sans-serif;
  font-size: 18px;
  color: #fff;
}
.r-seed {
  flex: 1;
  border-width: 1px;
  border-radius: 10px;
  padding: 6px 8px;
  text-align: center;
  font-size: 12px;
}
</style>
