<script setup lang="ts">
/**
 * Members who picked their own name on /line, waiting for an admin to say
 * it really is them. Shown above the member list only while there are
 * any, so most nights it takes no room at all.
 *
 * The LINE picture and display name sit beside the club photo and
 * nickname they claimed: the admin, standing at the court, compares the
 * two and the person in front of them.
 *
 * Below them, sign-ups from people not in the club yet: accepting one
 * creates the member, already linked to their LINE, at the starting tier
 * picked here.
 */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { LineJoinRequest, LineLinkRequest } from '@/api/admin'
import type { EloTier } from '@/types'
import { STARTING_TIERS } from '@/utils/startingTiers'
import TierMascot from '@/components/players/TierMascot.vue'
import { apiErrorMessage } from '@/api/errors'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()

const requests = ref<LineLinkRequest[]>([])
const joins = ref<LineJoinRequest[]>([])
// The starting tier picked for each sign-up; Beer (the club's 1000) until
// the admin says otherwise.
const tierFor = reactive<Record<string, EloTier>>({})
const busyId = ref<string | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  // Either failing means LINE isn't migrated or switched on yet: nothing
  // to show, not an error.
  const [links, signUps] = await Promise.allSettled([adminApi.getLineRequests(), adminApi.getLineJoins()])
  requests.value = links.status === 'fulfilled' ? links.value : []
  joins.value = signUps.status === 'fulfilled' ? signUps.value : []
}

async function decideJoin(req: LineJoinRequest, accept: boolean): Promise<void> {
  busyId.value = req.id
  problem.value = ''
  try {
    if (accept) {
      const score = STARTING_TIERS.find((o) => o.tier === (tierFor[req.id] ?? 'beer'))?.score ?? null
      await adminApi.approveLineJoin(req.id, score)
    } else {
      await adminApi.rejectLineJoin(req.id)
    }
    emit('changed')
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineAdmin.failed'))
  } finally {
    busyId.value = null
    await load()
  }
}

function details(req: LineJoinRequest): string {
  const bits: string[] = []
  if (req.dominant_hand) bits.push(req.dominant_hand === 'left' ? t('lineJoin.leftHanded') : t('lineJoin.rightHanded'))
  if (req.instagram) bits.push(`IG ${req.instagram}`)
  if (req.tiktok) bits.push(`TikTok ${req.tiktok}`)
  return bits.join(' · ')
}

async function decide(req: LineLinkRequest, approve: boolean): Promise<void> {
  busyId.value = req.id
  problem.value = ''
  try {
    if (approve) await adminApi.approveLineRequest(req.id)
    else await adminApi.rejectLineRequest(req.id)
    emit('changed')
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineAdmin.failed'))
  } finally {
    busyId.value = null
    await load()
  }
}

onMounted(load)
defineExpose({ load })
</script>

<template>
  <section v-if="requests.length || joins.length" class="hud-panel mt-4 border border-[#06c755]/40 bg-[#06c755]/[0.06] p-4" aria-labelledby="line-req-title">
    <h2 id="line-req-title" class="flex items-center gap-2 text-sm font-semibold">
      <span class="rounded-md bg-[#06c755] px-1.5 py-0.5 text-[11px] font-bold text-white">LINE</span>
      {{ t('lineAdmin.title') }}
      <span class="rounded-full bg-[#06c755]/25 px-2 text-xs text-[#7dffb0]">{{ requests.length + joins.length }}</span>
    </h2>
    <p v-if="problem" class="mt-2 text-sm text-status-error" role="alert">{{ problem }}</p>
    <p v-if="requests.length" class="mt-1 text-xs text-white/55">{{ t('lineAdmin.sub') }}</p>
    <ul v-if="requests.length" class="mt-3 space-y-2">
      <li v-for="r in requests" :key="r.id" class="rounded-xl border border-white/10 bg-brand-black/60 p-3">
        <div class="flex items-center gap-2.5">
          <span class="line-ring shrink-0 rounded-full">
            <PlayerAvatar :name="r.line_name" :avatar-url="r.line_picture" size="md" round />
          </span>
          <span class="min-w-0 flex-1 text-sm">
            <span class="block truncate font-medium">{{ r.line_name }}</span>
            <span class="block truncate text-xs text-white/55">
              {{ t('lineAdmin.claims') }}
              <b class="font-semibold text-brand-pink">{{ r.player.nickname }}</b>
            </span>
          </span>
          <PlayerAvatar :name="r.player.nickname" :avatar-url="r.player.avatar_url" size="md" />
        </div>
        <div class="mt-2 flex gap-2">
          <button
            type="button"
            class="min-h-11 flex-1 rounded-full bg-[#06c755] px-3 text-sm font-semibold text-white disabled:opacity-50"
            :disabled="busyId !== null"
            @click="decide(r, true)"
          >
            {{ t('lineAdmin.approve') }}
          </button>
          <button
            type="button"
            class="min-h-11 flex-1 rounded-full border border-white/20 px-3 text-sm text-white/70 disabled:opacity-50"
            :disabled="busyId !== null"
            @click="decide(r, false)"
          >
            {{ t('lineAdmin.reject') }}
          </button>
        </div>
      </li>
    </ul>

    <template v-if="joins.length">
      <h3 class="mt-4 flex items-center gap-2 text-sm font-semibold">
        {{ t('lineAdmin.joinsTitle') }}
        <span class="rounded-full bg-brand-pink/25 px-2 text-xs text-brand-pink">{{ joins.length }}</span>
      </h3>
      <p class="mt-1 text-xs text-white/55">{{ t('lineAdmin.joinsSub') }}</p>
      <ul class="mt-3 space-y-2">
        <li v-for="j in joins" :key="j.id" class="rounded-xl border border-white/10 bg-brand-black/60 p-3">
          <div class="flex items-center gap-3">
            <PlayerAvatar :name="j.nickname" :avatar-url="j.photo_url" size="lg" round />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-display text-base font-bold">{{ j.nickname }}</span>
              <span class="flex items-center gap-1 truncate text-xs text-[#7dffb0]">
                <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-[#06c755]" aria-hidden="true" />
                LINE: {{ j.line_name }}
              </span>
              <span v-if="details(j)" class="block truncate text-xs text-white/55">{{ details(j) }}</span>
              <span v-if="j.quote" class="block truncate text-xs text-white/45 italic">“{{ j.quote }}”</span>
            </span>
          </div>
          <p class="mt-3 mb-1.5 text-xs text-white/50">{{ t('lineAdmin.startingTier') }}</p>
          <div class="flex flex-wrap gap-1.5" role="radiogroup" :aria-label="t('lineAdmin.startingTier')">
            <button
              v-for="opt in STARTING_TIERS"
              :key="opt.tier"
              type="button"
              role="radio"
              :aria-checked="(tierFor[j.id] ?? 'beer') === opt.tier"
              class="flex min-h-9 items-center gap-1 rounded-full border px-2.5 text-xs font-semibold"
              :class="(tierFor[j.id] ?? 'beer') === opt.tier ? 'border-brand-pink bg-brand-pink/15 text-white' : 'border-white/15 text-white/50'"
              @click="tierFor[j.id] = opt.tier"
            >
              <TierMascot :tier="opt.tier" :size="18" :interactive="false" />
              {{ opt.label }}
            </button>
          </div>
          <div class="mt-3 flex gap-2">
            <button
              type="button"
              class="min-h-11 flex-1 rounded-full bg-brand-pink px-3 text-sm font-semibold text-brand-black disabled:opacity-50"
              :disabled="busyId !== null"
              @click="decideJoin(j, true)"
            >
              {{ t('lineAdmin.accept') }}
            </button>
            <button
              type="button"
              class="min-h-11 flex-1 rounded-full border border-white/20 px-3 text-sm text-white/70 disabled:opacity-50"
              :disabled="busyId !== null"
              @click="decideJoin(j, false)"
            >
              {{ t('lineAdmin.decline') }}
            </button>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.line-ring {
  box-shadow: 0 0 0 2px #06c755;
}
</style>
