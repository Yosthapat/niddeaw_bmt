import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { gameNight, timeLeft } from '@/utils/gameNight'

/**
 * A second hand on the club's next Friday night: whether it is on, and how
 * long until it starts, split for a countdown. The clock only ticks while
 * the page is on screen; a hidden tab catches up the moment it is shown.
 */
export function useGameNight() {
  const { t } = useI18n()
  const now = ref(Date.now())
  let tick: ReturnType<typeof setInterval> | null = null
  const onVisible = (): void => {
    now.value = Date.now()
  }
  onMounted(() => {
    tick = setInterval(() => {
      if (document.visibilityState === 'visible') now.value = Date.now()
    }, 1000)
    document.addEventListener('visibilitychange', onVisible)
  })
  onBeforeUnmount(() => {
    if (tick) clearInterval(tick)
    document.removeEventListener('visibilitychange', onVisible)
  })

  const night = computed(() => gameNight(now.value))
  const countdown = computed(() => {
    const left = timeLeft(night.value.start, now.value)
    return [
      { n: String(left.days), unit: t('home.big.days') },
      { n: String(left.hours).padStart(2, '0'), unit: t('home.big.hours') },
      { n: String(left.minutes).padStart(2, '0'), unit: t('home.big.minutes') },
      { n: String(left.seconds).padStart(2, '0'), unit: t('home.big.seconds') },
    ]
  })
  // "คืนนี้" on the Friday itself, "ศุกร์นี้" any other day of the week.
  const startsAt = computed(() =>
    night.value.start - now.value < 20 * 3_600_000 ? t('home.big.tonightAt') : t('home.big.fridayAt'),
  )
  return { night, countdown, startsAt }
}
