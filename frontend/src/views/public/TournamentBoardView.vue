<script setup lang="ts">
/**
 * The board for a TV in the hall: /tournament/board, opened full screen on
 * a laptop plugged into the screen. Every court and who is on it, the
 * matches coming up, the latest results — big enough to read from the far
 * end of the hall, following the desk every 15 seconds. Nothing to tap: it
 * keeps the screen awake and runs all day. With ?t=<id> it shows that
 * tournament instead of the current one — a draft set up to rehearse.
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getPublicTournament, type CupMatch, type MatchSlot, type PublicTournament } from '@/api/tournament'
import { usePolling } from '@/composables/usePolling'
import { clock, roundLabel, sideLabel } from '@/utils/cupMatch'

const { t } = useI18n()
const route = useRoute()
const previewId = typeof route.query.t === 'string' ? route.query.t : undefined
const cup = ref<PublicTournament | null>(null)
const loaded = ref(false)
const failed = ref(false)

usePolling(async () => {
  try {
    cup.value = await getPublicTournament(previewId)
    failed.value = false
  } catch {
    failed.value = true // keep the last board up; say it's behind
  } finally {
    loaded.value = true
  }
}, 15000)

// the clock in the corner, and "called N min ago"
const now = ref(Date.now())
let tick: ReturnType<typeof setInterval> | undefined
// a TV left on all day: ask the browser not to dim it
let lock: { release: () => Promise<void> } | null = null
async function stayAwake(): Promise<void> {
  try {
    const nav = navigator as Navigator & { wakeLock?: { request: (k: 'screen') => Promise<{ release: () => Promise<void> }> } }
    lock = (await nav.wakeLock?.request('screen')) ?? null
  } catch {
    /* not offered here: the TV's own settings will do */
  }
}
const onVisible = (): void => {
  if (document.visibilityState === 'visible') void stayAwake()
}
onMounted(() => {
  tick = setInterval(() => (now.value = Date.now()), 15000)
  void stayAwake()
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  clearInterval(tick)
  void lock?.release()
  document.removeEventListener('visibilitychange', onVisible)
})
const time = computed(() => clock(new Date(now.value).toISOString()))

const matches = computed(() => cup.value?.matches ?? [])
const courtCount = computed(() => Math.max(cup.value?.courts ?? 0, ...matches.value.map((m) => (m.status === 'on_court' ? (m.court ?? 0) : 0))))
const courts = computed(() =>
  Array.from({ length: courtCount.value }, (_, i) => ({ n: i + 1, match: matches.value.find((m) => m.status === 'on_court' && m.court === i + 1) ?? null })),
)
const NEXT = 6
const upNext = computed(() =>
  matches.value
    .filter((m) => m.status === 'scheduled' && m.a.team_id && m.b.team_id)
    .sort((a, b) => a.match_no - b.match_no)
    .slice(0, NEXT),
)
const LATEST = 5
const latest = computed(() =>
  matches.value
    .filter((m) => m.status === 'done')
    .sort((a, b) => (b.finished_at ?? '').localeCompare(a.finished_at ?? '') || b.match_no - a.match_no)
    .slice(0, LATEST),
)
const champions = computed(() =>
  matches.value
    .filter((m) => m.stage === 'ko' && m.round === 2 && m.status === 'done' && (m.winner === 'a' || m.winner === 'b'))
    .map((m) => ({ id: m.id, level: m.level_name, bracket: m.bracket, team: m[m.winner as 'a' | 'b'] })),
)
const allDone = computed(() => matches.value.length > 0 && matches.value.every((m) => m.status === 'done'))

const minutesAgo = (iso: string | null): number => (iso ? Math.max(0, Math.round((now.value - new Date(iso).getTime()) / 60000)) : 0)
const names = (s: MatchSlot): string => s.players.map((p) => p.nickname).join(' · ')
const score = (m: CupMatch): string => (m.walkover ? t('cup.view.wo') : (m.sets ?? []).map(([a, b]) => `${a}-${b}`).join('  '))
const winnerName = (m: CupMatch): string => (m.winner === 'a' || m.winner === 'b' ? sideLabel(m[m.winner], t) : t('cup.board.draw'))
const loserName = (m: CupMatch): string => (m.winner === 'a' ? sideLabel(m.b, t) : m.winner === 'b' ? sideLabel(m.a, t) : '')
</script>

<template>
  <div class="board min-h-dvh text-white">
    <header class="flex items-center gap-[1.5vw] px-[2.5vw] pt-[2vh] pb-[1.5vh]">
      <p class="font-display text-[clamp(20px,2.6vw,56px)] leading-none font-bold tracking-wide text-[#ffe14d]">NIDDEAW CUP</p>
      <p class="min-w-0 truncate text-[clamp(14px,1.5vw,32px)] text-white/70">{{ cup?.name }}</p>
      <p v-if="failed" class="rounded-full bg-[#ffd34d]/20 px-3 py-1 text-[clamp(12px,1vw,20px)] text-[#ffd34d]">{{ t('cup.board.behind') }}</p>
      <p class="ml-auto font-display text-[clamp(22px,3vw,64px)] leading-none font-bold tabular-nums">{{ time }}</p>
    </header>

    <p v-if="loaded && !cup" class="px-[2.5vw] pt-[20vh] text-center text-[clamp(20px,3vw,60px)] text-white/70">{{ t('cup.board.none') }}</p>
    <p v-else-if="cup && !cup.schedule_published" class="px-[2.5vw] pt-[20vh] text-center text-[clamp(20px,3vw,60px)] text-white/70">{{ t('cup.board.notYet') }}</p>

    <main v-else-if="cup" class="grid gap-[1.5vw] px-[2.5vw] pb-[2vh] lg:h-[calc(100dvh-9vh)] lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <!-- the courts -->
      <section :aria-label="t('cup.board.courts')" class="min-h-0">
        <!-- the finals are played: the champions take the screen -->
        <div v-if="allDone && champions.length" class="champs grid gap-[1vw] rounded-[1.4vw] border border-[#ffe14d]/50 p-[1.5vw]" :class="champions.length > 2 ? 'grid-cols-2' : ''">
          <p class="col-span-full text-center font-display text-[clamp(20px,2.4vw,52px)] font-bold text-[#ffe14d]">{{ t('cup.board.champions') }}</p>
          <div v-for="c in champions" :key="c.id" class="rounded-[1vw] bg-black/25 p-[1vw] text-center">
            <p class="text-[clamp(12px,1.1vw,24px)] text-[#ff9fd6]">{{ c.level }} · {{ t(`cup.bracket.${c.bracket ?? 'upper'}`) }}</p>
            <p class="font-display text-[clamp(18px,2vw,44px)] font-bold">{{ c.team.team_name }}</p>
            <p class="text-[clamp(12px,1.1vw,24px)] text-white/70">{{ names(c.team) }}</p>
          </div>
        </div>
        <div v-else class="grid gap-[1vw] lg:h-full lg:auto-rows-fr" :class="courtCount > 4 ? 'grid-cols-2 xl:grid-cols-3' : 'grid-cols-2'">
          <article
            v-for="c in courts"
            :key="c.n"
            class="flex flex-col rounded-[1.2vw] border p-[1.1vw]"
            :class="c.match ? 'border-[#7ff0b4]/60 bg-[#7ff0b4]/8' : 'border-white/12 bg-white/4'"
          >
            <header class="flex items-baseline gap-[0.8vw]">
              <b class="shrink-0 font-display text-[clamp(18px,2.2vw,48px)] leading-none whitespace-nowrap" :class="c.match ? 'text-[#7ff0b4]' : 'text-white/45'">{{ t('cup.day.court', { n: c.n }) }}</b>
              <span v-if="c.match" class="ml-auto min-w-0 truncate text-right text-[clamp(11px,1vw,22px)] text-white/55">#{{ c.match.match_no }} · {{ t('cup.board.ago', { m: minutesAgo(c.match.called_at) }) }}</span>
              <span v-else class="ml-auto text-[clamp(12px,1.2vw,26px)] text-white/40">{{ t('cup.day.free') }}</span>
            </header>
            <template v-if="c.match">
              <p class="mt-[0.6vh] truncate text-[clamp(11px,1vw,22px)] text-[#ff9fd6]">{{ c.match.level_name }} · {{ roundLabel(c.match, t) }}</p>
              <div class="mt-[0.8vh] flex flex-1 flex-col justify-center gap-[0.4vh]">
                <div v-for="side in (['a', 'b'] as const)" :key="side">
                  <p class="truncate font-display text-[clamp(16px,1.9vw,42px)] leading-tight font-bold">{{ sideLabel(c.match[side], t) }}</p>
                  <p class="truncate text-[clamp(11px,1.05vw,23px)] text-white/65">{{ names(c.match[side]) }}</p>
                  <p v-if="side === 'a'" class="my-[0.3vh] text-[clamp(10px,0.9vw,20px)] font-bold tracking-widest text-white/35">VS</p>
                </div>
              </div>
            </template>
          </article>
        </div>
      </section>

      <aside class="flex flex-col gap-[1.5vw]">
        <!-- what's coming up -->
        <section class="rounded-[1.2vw] border border-white/12 bg-white/4 p-[1.1vw]">
          <h2 class="mb-[0.8vh] font-display text-[clamp(16px,1.6vw,36px)] font-bold text-[#ffe14d]">{{ t('cup.board.next') }}</h2>
          <ol class="flex flex-col gap-[0.9vh]">
            <li v-for="m in upNext" :key="m.id" class="flex items-center gap-[0.8vw]">
              <b class="w-[3.6em] shrink-0 font-display text-[clamp(13px,1.2vw,26px)] text-white/60">#{{ m.match_no }}</b>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[clamp(13px,1.25vw,28px)] font-semibold">{{ sideLabel(m.a, t) }} <span class="text-white/40">vs</span> {{ sideLabel(m.b, t) }}</span>
                <span class="block truncate text-[clamp(10px,0.9vw,20px)] text-white/50">{{ m.level_name }} · {{ roundLabel(m, t) }}</span>
              </span>
            </li>
            <li v-if="!upNext.length" class="text-[clamp(12px,1.1vw,24px)] text-white/45">{{ t('cup.board.nothingNext') }}</li>
          </ol>
        </section>

        <!-- what just finished -->
        <section class="rounded-[1.2vw] border border-white/12 bg-white/4 p-[1.1vw]">
          <h2 class="mb-[0.8vh] font-display text-[clamp(16px,1.6vw,36px)] font-bold text-[#ff9fd6]">{{ t('cup.board.latest') }}</h2>
          <ol class="flex flex-col gap-[0.9vh]">
            <li v-for="m in latest" :key="m.id">
              <p class="flex items-baseline gap-[0.6vw]">
                <span class="min-w-0 flex-1 truncate text-[clamp(13px,1.25vw,28px)] font-semibold text-[#7ff0b4]">{{ winnerName(m) }}</span>
                <b class="shrink-0 font-display text-[clamp(12px,1.15vw,26px)] tabular-nums">{{ score(m) }}</b>
              </p>
              <p class="truncate text-[clamp(10px,0.9vw,20px)] text-white/50">
                <template v-if="loserName(m)">{{ t('cup.board.beat', { team: loserName(m) }) }} · </template>{{ m.level_name }} · #{{ m.match_no }}
              </p>
            </li>
            <li v-if="!latest.length" class="text-[clamp(12px,1.1vw,24px)] text-white/45">{{ t('cup.board.noResults') }}</li>
          </ol>
        </section>

        <p class="text-center text-[clamp(11px,1vw,22px)] text-white/55">{{ t('cup.board.follow') }} <b class="text-white">niddeaw.fyi/tournament</b></p>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.board {
  background:
    radial-gradient(90% 60% at 50% -10%, rgb(155 44 255 / 0.35), transparent 70%),
    linear-gradient(180deg, #160828, #0a0416);
}
.champs {
  background: radial-gradient(120% 90% at 50% 0%, rgb(255 225 77 / 0.2), rgb(29 11 58 / 0.9) 70%);
}
</style>
