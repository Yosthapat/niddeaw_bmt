<script setup lang="ts">
// "The club has played N matches" — a live tally above the home page
// banner. Polls rather than loading once: on a Friday night the number
// moves every time a match is recorded, and the whole point is that it
// keeps up without a refresh.
//
// 15s rather than the 7s LiveView uses. A match takes ten minutes at the
// very least, so a faster poll would only double the request rate on the
// most-visited page of the site to show the same number.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMatchCount } from '@/api/public'
import { usePolling } from '@/composables/usePolling'
import CountUp from '@/components/common/CountUp.vue'

const { t } = useI18n()

// null = not known yet. Kept distinct from 0 so a slow first response
// shows nothing rather than briefly claiming the club has played none.
const total = ref<number | null>(null)

function formatCount(value: number): string {
  return value.toLocaleString('th-TH')
}

async function refresh(): Promise<void> {
  try {
    total.value = (await getMatchCount()).completed
  } catch {
    // Keep the last good number on screen. This is a flourish above the
    // banner — a cold-starting backend must not put an error on the home
    // page over it, and the next poll will pick the count back up.
  }
}

usePolling(refresh, 15000)
</script>

<template>
  <!-- Hidden until there is something to report: a club with no recorded
       matches yet shouldn't lead its home page with a zero. -->
  <p
    v-if="total !== null && total > 0"
    class="mb-5 text-center text-xs tracking-wide text-white/45 sm:mb-6"
  >
    {{ t('home.clubMatchesLabel') }}
    <span class="font-display text-base font-bold text-brand-pink">
      <CountUp :value="total" :format="formatCount" />
    </span>
    {{ t('home.clubMatchesUnit') }}
  </p>
</template>
