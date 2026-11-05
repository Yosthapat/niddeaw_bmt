<script setup lang="ts">
/**
 * Medals won since the member last opened LINE, celebrated one at a time
 * as they open the page: the medal drops in and spins, sparks burst. At
 * most the three grandest are celebrated (the first visit after launch
 * could otherwise be a dozen in a row); the rest are simply on the shelf.
 * When the last one is put away they are all marked seen, so each is
 * shown once.
 * Emits `count` with how many medals the member holds, for the home button.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMyBadges, markBadgesSeen, type BadgeAward } from '@/api/quests'
import { awardImage, awardMetal, awardName, METAL_RANK, metalName, shelfItems, type BadgeItem } from '@/utils/quests'
import type { Locale } from '@/i18n'
import BadgeInspect from '@/components/quests/BadgeInspect.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ count: [n: number] }>()
const { t, locale } = useI18n()

const queue = ref<BadgeItem[]>([])
const current = ref<BadgeItem | null>(null)
let unseen: BadgeAward[] = []
const MAX_SHOWN = 3

function slotOf(a: BadgeAward): string {
  return a.badge.startsWith('monthly:') ? 'monthly' : a.badge
}

onMounted(async () => {
  try {
    const data = await getMyBadges(props.token)
    if (!data) return
    const items = shelfItems(data, t, locale.value as Locale)
    emit('count', items.filter((i) => !i.locked).length)
    unseen = data.unseen
    // one per quest: its highest new level
    const best = new Map<string, BadgeAward>()
    for (const a of unseen) if ((best.get(a.badge)?.level ?? 0) < a.level) best.set(a.badge, a)
    queue.value = [...best.values()]
      .sort((a, b) => METAL_RANK[awardMetal(b)] - METAL_RANK[awardMetal(a)] || b.earned_at.localeCompare(a.earned_at))
      .slice(0, MAX_SHOWN)
      .reverse()
      .map((a) => {
        const base = items.find((i) => i.id === slotOf(a))
        const m = awardMetal(a)
        return {
          ...(base ?? items[0]!),
          img: awardImage(a),
          name: awardName(t, a, locale.value as Locale),
          metal: m,
          locked: false,
          tierLabel: base?.secret ? t('quests.secret') : metalName(t, m),
          progress: null,
        }
      })
    next()
  } catch {
    // quests not switched on, or offline: nothing to celebrate
  }
})

function next(): void {
  current.value = queue.value.shift() ?? null
  if (!current.value && unseen.length) {
    const items = unseen
    unseen = []
    void markBadgesSeen(props.token, items).catch(() => {})
  }
}
</script>

<template>
  <BadgeInspect :item="current" celebrate @close="next" />
</template>
