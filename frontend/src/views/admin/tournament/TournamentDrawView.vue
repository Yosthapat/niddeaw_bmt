<script setup lang="ts">
/**
 * Groups and the day's match list.
 *
 * Each level's confirmed teams are drawn into groups by lot; an admin can
 * move a team by tapping it and then the place it should go (whoever is
 * there swaps). Then the match list is made for all levels at once, with an
 * estimated start for each match from the courts and the minutes below.
 * Players see none of it — the pages say "coming soon" — until it is
 * published. Making the list locks the groups; clearing it unlocks them.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import LevelTabs from '@/components/admin/LevelTabs.vue'
import { tournamentAdmin, type DrawLevel, type DrawState, type DrawTeam } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { clock, roundLabel, sideLabel } from '@/utils/cupMatch'
import { formatDateTime } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const { all, picked, load, pick, replace } = useTournamentPick()

const INPUT = 'w-full rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white'
const state = ref<DrawState | null>(null)
const problem = ref('')
const busy = ref<string | null>(null)
const locked = computed(() => !!state.value?.matches.length)

async function run(key: string, job: () => Promise<DrawState>): Promise<void> {
  busy.value = key
  problem.value = ''
  try {
    state.value = await job()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  } finally {
    busy.value = null
  }
}
async function refresh(): Promise<void> {
  if (picked.value) await run('load', () => tournamentAdmin.draw(picked.value!.id))
}
watch(() => picked.value?.id, refresh)
onMounted(async () => {
  if (!all.value.length) await load()
  await refresh()
})

// --- the day's settings ----------------------------------------------------
const settings = reactive({ courts: '' as number | '', day_start: '09:00', group_minutes: 20, ko_minutes: 30, rest_minutes: 10 })
watch(
  picked,
  (x) => {
    if (!x) return
    Object.assign(settings, {
      courts: x.courts ?? '',
      day_start: (x.day_start ?? '09:00').slice(0, 5),
      group_minutes: x.group_minutes,
      ko_minutes: x.ko_minutes,
      rest_minutes: x.rest_minutes,
    })
  },
  { immediate: true },
)
const savedSettings = ref(false)
async function saveSettings(): Promise<void> {
  if (!picked.value) return
  problem.value = ''
  savedSettings.value = false
  try {
    replace(
      await tournamentAdmin.update(picked.value.id, {
        ...(settings.courts === '' ? {} : { courts: Number(settings.courts) }),
        day_start: settings.day_start,
        group_minutes: Number(settings.group_minutes),
        ko_minutes: Number(settings.ko_minutes),
        rest_minutes: Number(settings.rest_minutes),
      }),
    )
    savedSettings.value = true
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

// --- the draw ----------------------------------------------------------------
async function drawLevel(lv: DrawLevel): Promise<void> {
  if (lv.groups.length) {
    const ok = await confirm({ title: t('cup.draw.redrawTitle'), message: t('cup.draw.redrawBody', { level: lv.level.name }), confirmLabel: t('cup.draw.redraw') })
    if (!ok) return
  }
  await run(lv.level.id, () => tournamentAdmin.drawLevel(picked.value!.id, lv.level.id))
}
async function clearLevel(lv: DrawLevel): Promise<void> {
  await run(lv.level.id, () => tournamentAdmin.clearLevel(picked.value!.id, lv.level.id))
}
function groupOf(lv: DrawLevel, g: string): (DrawTeam | null)[] {
  const size = Math.max(...lv.teams.filter((x) => x.group_label === g).map((x) => x.group_pos ?? 0), 0)
  const places: (DrawTeam | null)[] = []
  for (let p = 1; p <= Math.max(size, lv.teams.filter((x) => x.group_label === g).length); p++) {
    places.push(lv.teams.find((x) => x.group_label === g && x.group_pos === p) ?? null)
  }
  return places
}
const unplaced = (lv: DrawLevel): DrawTeam[] => lv.teams.filter((x) => !x.group_label)

// tap a team, then the place it should go
const moving = ref<DrawTeam | null>(null)
async function tapPlace(g: string, pos: number, holder: DrawTeam | null): Promise<void> {
  if (locked.value) return
  if (!moving.value) {
    if (holder) moving.value = holder
    return
  }
  if (holder?.id === moving.value.id) {
    moving.value = null
    return
  }
  const team = moving.value
  moving.value = null
  await run(team.id, () => tournamentAdmin.place(team.id, g, pos))
}

// --- the match list -----------------------------------------------------------
async function make(): Promise<void> {
  await run('make', () => tournamentAdmin.makeSchedule(picked.value!.id))
}
async function clear(): Promise<void> {
  const ok = await confirm({ title: t('cup.draw.clearTitle'), message: t('cup.draw.clearBody'), confirmLabel: t('cup.draw.clear') })
  if (ok) await run('clear', () => tournamentAdmin.clearSchedule(picked.value!.id))
}
async function publish(on: boolean): Promise<void> {
  const ok = await confirm({
    title: on ? t('cup.draw.publishTitle') : t('cup.draw.hideTitle'),
    message: on ? t('cup.draw.publishBody') : t('cup.draw.hideBody'),
    confirmLabel: on ? t('cup.draw.publish') : t('cup.draw.hide'),
  })
  if (ok) await run('publish', () => tournamentAdmin.publish(picked.value!.id, on))
}

// One level at a time: the first with confirmed teams until one is picked.
const picks = ref('')
const activeId = computed(() => {
  const levels = state.value?.levels ?? []
  return levels.find((x) => x.level.id === picks.value)?.level.id ?? levels.find((x) => x.confirmed > 0)?.level.id ?? levels[0]?.level.id ?? ''
})
const active = computed(() => state.value?.levels.find((x) => x.level.id === activeId.value) ?? null)
const tabs = computed(() =>
  (state.value?.levels ?? []).map((x) => ({
    id: x.level.id,
    name: x.level.name,
    badge: x.groups.length ? t('cup.draw.tabGroups', { n: x.groups.length }) : `${x.confirmed}/${x.level.max_teams}`,
  })),
)
// that level's matches: the group stage, then each bracket
const matchParts = computed(() => {
  const mine = (state.value?.matches ?? []).filter((m) => m.level_id === activeId.value)
  return [
    { key: 'group', label: t('cup.schedule.groupStage'), matches: mine.filter((m) => m.stage === 'group') },
    { key: 'upper', label: t('cup.bracket.upper'), matches: mine.filter((m) => m.stage === 'ko' && m.bracket === 'upper') },
    { key: 'lower', label: t('cup.bracket.lower'), matches: mine.filter((m) => m.stage === 'ko' && m.bracket === 'lower') },
  ].filter((p) => p.matches.length)
})
const when = (iso: string): string => formatDateTime(iso, locale.value as Locale)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tDraw') }}</h1>

    <select
      v-if="all.length"
      :value="picked?.id"
      :aria-label="t('cup.admin.pick')"
      class="min-h-11 w-full rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white"
      @change="pick(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="x in all" :key="x.id" :value="x.id">{{ x.name }} · {{ x.starts_on }}</option>
    </select>
    <p v-else class="text-sm text-white/50">{{ t('cup.admin.noneYet') }}</p>

    <template v-if="picked && state">
      <!-- where it stands -->
      <section class="hud-panel mt-4 border bg-brand-surface p-4" :class="state.published_at ? 'border-status-success/40' : 'border-brand-pink/15'">
        <p class="text-sm font-semibold">
          {{ state.published_at ? t('cup.draw.published') : locked ? t('cup.draw.madeHidden') : t('cup.draw.notMade') }}
        </p>
        <p class="mt-1 text-xs text-white/55">
          {{ state.published_at ? t('cup.draw.publishedHint') : t('cup.draw.hiddenHint') }}
        </p>
        <p v-if="locked && state.est_end" class="mt-1 text-xs text-white/70">
          {{ t('cup.draw.summary', { n: state.matches.length, end: when(state.est_end) }) }}
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button v-if="!locked" type="button" :disabled="busy === 'make'" class="tap rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black disabled:opacity-50" @click="make">
            {{ t('cup.draw.make') }}
          </button>
          <template v-else>
            <button v-if="!state.published_at" type="button" :disabled="busy === 'publish'" class="tap rounded-full bg-status-success px-5 text-sm font-semibold text-brand-black" @click="publish(true)">
              {{ t('cup.draw.publish') }}
            </button>
            <button v-else type="button" class="tap rounded-full border border-white/25 px-4 text-sm text-white/75" @click="publish(false)">{{ t('cup.draw.hide') }}</button>
            <button v-if="!state.published_at" type="button" class="tap rounded-full border border-white/25 px-4 text-sm text-white/75" @click="clear">{{ t('cup.draw.clear') }}</button>
          </template>
        </div>
      </section>

      <!-- the day's settings -->
      <section class="hud-panel mt-4 border border-brand-pink/15 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.draw.settings') }}</h2>
        <div class="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-5">
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.courts') }}<input v-model.number="settings.courts" type="number" min="1" max="60" :disabled="locked" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.draw.dayStart') }}<input v-model="settings.day_start" type="time" :disabled="locked" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.draw.groupMinutes') }}<input v-model.number="settings.group_minutes" type="number" min="5" max="120" :disabled="locked" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.draw.koMinutes') }}<input v-model.number="settings.ko_minutes" type="number" min="5" max="120" :disabled="locked" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.draw.restMinutes') }}<input v-model.number="settings.rest_minutes" type="number" min="0" max="120" :disabled="locked" :class="INPUT" /></label>
        </div>
        <p v-if="locked" class="mt-2 text-xs text-white/50">{{ t('cup.draw.settingsLocked') }}</p>
        <template v-else>
          <p v-if="savedSettings" class="mt-2 text-sm text-status-success" role="status">{{ t('cup.admin.saved') }}</p>
          <button type="button" class="tap mt-3 rounded-full border border-brand-pink/40 px-4 text-xs font-semibold text-brand-pink" @click="saveSettings">{{ t('cup.admin.save') }}</button>
        </template>
      </section>

      <p v-if="problem" class="mt-4 text-sm text-status-error" role="alert">{{ problem }}</p>

      <!-- one level at a time -->
      <LevelTabs :levels="tabs" :model-value="activeId" :label="t('cup.level')" @update:model-value="(id) => { picks = id; moving = null }" />

      <!-- its groups -->
      <section v-for="lv in active ? [active] : []" :key="lv.level.id" class="hud-panel mt-3 border border-brand-pink/15 bg-brand-surface p-4">
        <div class="flex flex-wrap items-baseline gap-2">
          <h2 class="font-display text-base font-bold">{{ lv.level.name }}</h2>
          <span class="text-xs text-white/60">{{ t('cup.draw.confirmed', { n: lv.confirmed, max: lv.level.max_teams }) }}</span>
          <span v-if="lv.not_ready" class="text-xs text-[#ffd34d]">{{ t('cup.draw.notReady', { n: lv.not_ready }) }}</span>
        </div>
        <div v-if="!locked" class="mt-2 flex flex-wrap gap-2">
          <button type="button" :disabled="busy === lv.level.id || lv.confirmed < 2" class="tap rounded-full bg-brand-pink px-4 text-xs font-semibold text-brand-black disabled:opacity-40" @click="drawLevel(lv)">
            {{ lv.groups.length ? t('cup.draw.redraw') : t('cup.draw.draw') }}
          </button>
          <button v-if="lv.groups.length" type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/65" @click="clearLevel(lv)">{{ t('cup.draw.clearGroups') }}</button>
        </div>
        <p v-if="!locked && lv.groups.length" class="mt-2 text-xs text-white/50">{{ moving ? t('cup.draw.pickPlace', { team: moving.name }) : t('cup.draw.moveHint') }}</p>

        <div v-if="lv.groups.length" class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div v-for="g in lv.groups" :key="g" class="rounded-xl border border-white/10 bg-brand-black/40 p-2">
            <p class="mb-1 font-display text-sm font-bold text-brand-pink">{{ t('cup.draw.group', { g }) }}</p>
            <button
              v-for="(holder, i) in groupOf(lv, g)"
              :key="i"
              type="button"
              class="flex min-h-11 w-full items-center gap-1.5 rounded-lg px-1.5 text-left text-xs"
              :class="[moving && holder?.id === moving.id ? 'bg-brand-pink/25 ring-1 ring-brand-pink' : moving ? 'hover:bg-white/8' : '', locked ? 'cursor-default' : '']"
              :disabled="locked"
              @click="tapPlace(g, i + 1, holder)"
            >
              <span class="w-5 shrink-0 font-display text-white/45">{{ g }}{{ i + 1 }}</span>
              <span class="min-w-0 truncate">{{ holder?.name ?? '—' }}</span>
            </button>
          </div>
        </div>
        <p v-if="unplaced(lv).length && lv.groups.length" class="mt-2 text-xs text-[#ffd34d]">
          {{ t('cup.draw.unplaced', { teams: unplaced(lv).map((x) => x.name).join(', ') }) }}
        </p>
        <div v-if="moving && unplaced(lv).some((x) => x.id === moving?.id)" class="mt-1 text-xs text-white/60">{{ t('cup.draw.pickPlace', { team: moving.name }) }}</div>
        <div v-if="!locked && unplaced(lv).length && lv.groups.length" class="mt-1 flex flex-wrap gap-1.5">
          <button v-for="x in unplaced(lv)" :key="x.id" type="button" class="tap rounded-full border border-[#ffd34d]/40 px-3 text-xs text-[#ffd34d]" @click="moving = x">{{ x.name }}</button>
        </div>
      </section>

      <!-- its matches -->
      <section v-if="locked && active" class="mt-6">
        <h2 class="font-display text-lg font-bold">{{ t('cup.schedule.matchesOf', { level: active.level.name }) }}</h2>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.draw.allMatchesHint', { n: state.matches.length }) }}</p>
        <template v-for="part in matchParts" :key="part.key">
          <p class="mt-4 text-xs font-semibold text-white/70">{{ part.label }}</p>
          <ul class="mt-1.5 space-y-1.5">
            <li v-for="m in part.matches" :key="m.id" class="hud-panel flex items-center gap-3 border border-brand-pink/10 bg-brand-surface px-3 py-2">
              <span class="w-10 shrink-0 text-center">
                <b class="block font-display text-sm">#{{ m.match_no }}</b>
                <span class="text-[11px] text-white/50">{{ clock(m.est_start) }}</span>
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm">
                  <span :class="m.a.team_name ? '' : 'text-white/55'">{{ sideLabel(m.a, t) }}</span>
                  <span class="px-1 text-white/40">vs</span>
                  <span :class="m.b.team_name ? '' : 'text-white/55'">{{ sideLabel(m.b, t) }}</span>
                </span>
                <span class="block truncate text-[11px] text-white/50">{{ roundLabel(m, t) }}</span>
              </span>
            </li>
          </ul>
        </template>
        <p v-if="!matchParts.length" class="mt-3 text-sm text-white/45">{{ t('cup.schedule.noneInLevel') }}</p>
      </section>
    </template>
  </main>
</template>
