<script setup lang="ts">
// The latest medals won in the club, silver and up (plus every secret and
// monthly one): a nudge that the quests are there. Gone entirely when
// there is nothing to show or quests aren't switched on.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getRecentBadges, type BadgeFeedItem } from '@/api/quests'
import { awardImage, awardMetal, awardName, metalName } from '@/utils/quests'
import { formatDayMonth } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const items = ref<BadgeFeedItem[]>([])

onMounted(async () => {
  try {
    items.value = await getRecentBadges(8)
  } catch {
    items.value = []
  }
})
</script>

<template>
  <section v-if="items.length" class="world-card p-5 sm:p-6" aria-labelledby="home-badges">
    <p class="world-eyebrow">BADGES</p>
    <h2 id="home-badges" class="world-title mt-1 text-2xl">{{ t('quests.feed') }}</h2>
    <ul class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <li v-for="it in items" :key="`${it.player_id}-${it.badge}-${it.level}`">
        <RouterLink
          :to="`/members/${it.player_id}`"
          class="flex min-h-14 items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 transition-colors hover:bg-white/[0.08]"
        >
          <img :src="awardImage(it)" alt="" width="64" height="64" loading="lazy" class="h-12 w-12 shrink-0 object-contain drop-shadow-[0_3px_4px_rgb(0_0_0/0.6)]" />
          <span class="min-w-0 flex-1 text-sm leading-snug">
            <b class="font-display font-bold">{{ it.nickname }}</b>
            {{ t('quests.feedGot') }}
            <span class="text-[#f2c14e]">{{ awardName(t, it, locale as Locale) }}<template v-if="!it.badge.startsWith('monthly:') && !it.badge.startsWith('secret_')"> · {{ metalName(t, awardMetal(it)) }}</template></span>
            <span class="block text-xs text-white/50">{{ formatDayMonth(it.earned_at, locale as Locale) }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
