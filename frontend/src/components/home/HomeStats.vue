<script setup lang="ts">
// The club's two numbers as a card in the desktop grid: matches played
// (polled, so it moves on a Friday night) and members. The phone keeps
// ClubMatchCounter, the pill that folds up beside the member photos.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMatchCount, getPlayerCount } from '@/api/public'
import { usePolling } from '@/composables/usePolling'
import CountUp from '@/components/common/CountUp.vue'

const { t } = useI18n()
const matches = ref<number | null>(null)
const members = ref<number | null>(null)
const thousands = (n: number): string => n.toLocaleString('th-TH')

// 15s, as ClubMatchCounter: a match takes ten minutes at the least.
usePolling(async () => {
  try {
    matches.value = (await getMatchCount()).completed
  } catch {
    // keep the last good number
  }
}, 15000)
onMounted(async () => {
  try {
    members.value = (await getPlayerCount()).active
  } catch {
    // the match count alone still reads fine
  }
})
</script>

<template>
  <section class="world-card flex flex-col justify-center gap-4 p-6" :aria-label="t('home.stats.label')">
    <div>
      <CountUp v-if="matches !== null" :value="matches" :format="thousands" class="font-display text-[44px] leading-none font-bold text-brand-pink-light" />
      <span v-else class="font-display text-[44px] leading-none font-bold text-white/25">—</span>
      <p class="mt-1.5 text-sm text-white/65">{{ t('home.clubMatchesLabel') }}</p>
    </div>
    <div class="h-px bg-white/12" aria-hidden="true" />
    <div>
      <CountUp v-if="members !== null" :value="members" :format="thousands" class="font-display text-[44px] leading-none font-bold" />
      <span v-else class="font-display text-[44px] leading-none font-bold text-white/25">—</span>
      <p class="mt-1.5 text-sm text-white/65">{{ t('home.clubMembersLabel') }}</p>
    </div>
  </section>
</template>
