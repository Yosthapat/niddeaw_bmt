<script setup lang="ts">
// The two doors under the hero, side by side on every screen: the
// tournament that's coming and the club shop. Cards rather than tabs —
// neither is something a member opens every Friday.
//
// The tournament door says what is on: "coming soon" until there is a
// tournament to show, then its name and where it stands — taking entries,
// closed, on today, over.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getPublicTournament, type PublicTournament } from '@/api/tournament'

const { t, locale } = useI18n()
const cup = ref<PublicTournament | null>(null)
onMounted(async () => {
  try {
    cup.value = await getPublicTournament()
  } catch {
    cup.value = null // the door still says "coming soon"
  }
})

function day(iso: string): string {
  // A date-only string is read as local midnight, so the day doesn't slip.
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Intl.DateTimeFormat(locale.value === 'th' ? 'th-TH' : 'en-GB', { weekday: 'short', day: 'numeric', month: 'short' }).format(
    iso.length > 10 ? new Date(iso) : new Date(y, m - 1, d),
  )
}

type Stage = 'soon' | 'open' | 'upcoming' | 'closed' | 'running' | 'done'
const stage = computed<Stage>(() => {
  const c = cup.value
  if (!c) return 'soon'
  if (c.status === 'running') return 'running'
  if (c.status === 'done') return 'done'
  if (c.taking_entries) return 'open'
  if (c.status === 'open' && c.opens_at && new Date(c.opens_at) > new Date()) return 'upcoming'
  return 'closed'
})
const badge = computed(() => (stage.value === 'soon' ? 'COMING SOON' : t(`tournament.card.stage.${stage.value}`)))
const title = computed(() => cup.value?.name ?? t('nav.tournament'))
/** One line each, so a date never breaks across two. */
const sub = computed<string[]>(() => {
  const c = cup.value
  if (!c) return [t('tournament.card.sub')]
  if (stage.value === 'done') return [t('tournament.card.doneSub')]
  const play = t('tournament.card.playSub', { play: day(c.starts_on) })
  if (stage.value === 'open') return [play, t('tournament.card.closeSub', { close: day(c.closes_at) })]
  if (stage.value === 'upcoming' && c.opens_at) return [play, t('tournament.card.upcomingSub', { open: day(c.opens_at) })]
  return [play]
})
</script>

<template>
  <div class="grid grid-cols-2 gap-2.5 sm:gap-4 min-[900px]:gap-5">
    <RouterLink to="/tournament" class="home-card border-[#ffe14d]/50 bg-[linear-gradient(140deg,#3b0f5c,#1a0838_70%)] [--glow:rgb(255_207_63/0.4)]">
      <span
        class="self-start rounded-full border px-2 py-1 font-display text-[10px] leading-none font-bold sm:text-xs"
        :class="[
          stage === 'open' || stage === 'running' ? 'border-[#4ade80] text-[#4ade80]' : 'border-[#ffe14d] text-[#ffe14d]',
          stage === 'soon' || stage === 'open' || stage === 'running' ? 'card-blink' : '',
          stage === 'soon' || locale === 'en' ? 'tracking-[1.5px]' : '',
        ]"
      >
        {{ badge }}
      </span>
      <span class="line-clamp-2 pr-8 font-display font-bold" :class="cup ? 'text-[16px] leading-tight sm:text-xl' : 'text-[19px] sm:text-2xl'">{{ title }}</span>
      <span class="flex flex-col pr-10 text-[11px] font-light text-white/75 sm:text-sm">
        <span v-for="line in sub" :key="line" class="whitespace-nowrap">{{ line }}</span>
      </span>
      <svg viewBox="0 0 24 24" fill="none" stroke="#ffcf3f" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" class="card-art h-10 w-10" aria-hidden="true">
        <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
      </svg>
    </RouterLink>
    <RouterLink to="/shop" class="home-card border-brand-pink/55 bg-[linear-gradient(140deg,#4a0f3a,#1a0838_70%)]">
      <span class="self-start rounded-full bg-[#ffe14d] px-2 py-1 text-[10px] leading-none font-medium text-[#2a1a00] sm:text-xs">
        {{ t('shop.card.tag') }}
      </span>
      <span class="font-display text-[19px] font-bold sm:text-2xl">{{ t('nav.shop') }}</span>
      <span class="pr-10 text-[11px] font-light text-white/75 sm:text-sm">{{ t('shop.card.sub') }}</span>
      <svg viewBox="0 0 120 110" class="card-art h-[42px] w-[46px] rotate-[8deg]" aria-hidden="true">
        <path
          d="M38 8 18 18 4 40l18 10 6-10v64h64V40l6 10 18-10-14-22-20-10c-4 10-12 14-22 14S42 18 38 8Z"
          fill="#ea4ca4"
          stroke="rgb(255 255 255 / 0.6)"
          stroke-width="3"
        />
      </svg>
    </RouterLink>
  </div>
</template>

<style scoped>
/* The hero's glass, tinted: the tournament gold, the shop pink. */
.home-card {
  position: relative;
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.3),
    0 22px 44px -22px var(--glow, rgb(234 76 164 / 0.55)),
    0 10px 28px rgb(6 0 20 / 0.45);
  display: flex;
  min-height: 118px;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  padding: 12px;
  border-width: 1px;
  border-radius: 22px;
  transition: transform 0.15s;
}
.home-card:hover {
  transform: translateY(-2px);
}
.card-art {
  position: absolute;
  right: 8px;
  bottom: 8px;
  opacity: 0.9;
}
@media (min-width: 640px) {
  .home-card {
    min-height: 150px;
    padding: 18px;
    gap: 6px;
  }
  .card-art {
    right: 14px;
    bottom: 14px;
    scale: 1.5;
    transform-origin: 100% 100%;
  }
}
.card-blink {
  animation: card-blink 1.4s ease-in-out infinite;
}
@keyframes card-blink {
  50% {
    opacity: 0.45;
  }
}
/* In the desktop grid the two doors share a row with the podium's lower
   half, so they stand taller and their art grows with them. */
@media (min-width: 900px) {
  .home-card {
    min-height: 190px;
    padding: 24px;
    gap: 8px;
  }
  .card-art {
    right: 22px;
    bottom: 20px;
    scale: 1.9;
  }
}
@media (prefers-reduced-motion: reduce) {
  .card-blink {
    animation: none;
  }
  .home-card {
    transition: none;
  }
}
</style>
