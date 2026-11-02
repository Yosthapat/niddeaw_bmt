<script setup lang="ts">
// The club's people: a drifting strip of member photos and the way to all
// of them. On a phone the match counter folds up beside the strip; on a
// desktop the counter is a card of its own (HomeStats) and the strip has
// the whole width.
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import ClubMatchCounter from './ClubMatchCounter.vue'
import MemberMarquee from './MemberMarquee.vue'

defineProps<{ counter?: boolean }>()
const { t } = useI18n()
</script>

<template>
  <section v-reveal class="world-card p-4 sm:p-5" aria-labelledby="home-members">
    <div class="flex items-end justify-between gap-3">
      <div>
        <p class="world-eyebrow">MEMBERS</p>
        <h2 id="home-members" class="world-title text-xl sm:text-2xl">{{ t('home.memberMarqueeLabel') }}</h2>
      </div>
      <RouterLink to="/members" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/75 hover:text-white">
        {{ t('home.seeAll') }} <span aria-hidden="true">→</span>
      </RouterLink>
    </div>
    <!-- Marquee takes whatever width the counter leaves; min-w-0 lets
         it actually shrink instead of forcing the row wider. -->
    <div class="mt-3 flex items-center gap-3">
      <MemberMarquee class="flex-1" />
      <ClubMatchCounter v-if="counter" />
    </div>
  </section>
</template>
