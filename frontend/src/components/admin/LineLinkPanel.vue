<script setup lang="ts">
/**
 * Members who picked their own name on /line, waiting for an admin to say
 * it really is them. Shown above the member list only while there are
 * any, so most nights it takes no room at all.
 *
 * The LINE picture and display name sit beside the club photo and
 * nickname they claimed: the admin, standing at the court, compares the
 * two and the person in front of them.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { LineLinkRequest } from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()

const requests = ref<LineLinkRequest[]>([])
const busyId = ref<string | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    requests.value = await adminApi.getLineRequests()
  } catch {
    // LINE not migrated or switched off yet: nothing to show, not an error.
    requests.value = []
  }
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
  <section v-if="requests.length" class="hud-panel mt-4 border border-[#06c755]/40 bg-[#06c755]/[0.06] p-4" aria-labelledby="line-req-title">
    <h2 id="line-req-title" class="flex items-center gap-2 text-sm font-semibold">
      <span class="rounded-md bg-[#06c755] px-1.5 py-0.5 text-[11px] font-bold text-white">LINE</span>
      {{ t('lineAdmin.title') }}
      <span class="rounded-full bg-[#06c755]/25 px-2 text-xs text-[#7dffb0]">{{ requests.length }}</span>
    </h2>
    <p class="mt-1 text-xs text-white/55">{{ t('lineAdmin.sub') }}</p>
    <p v-if="problem" class="mt-2 text-sm text-status-error" role="alert">{{ problem }}</p>
    <ul class="mt-3 space-y-2">
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
  </section>
</template>

<style scoped>
.line-ring {
  box-shadow: 0 0 0 2px #06c755;
}
</style>
