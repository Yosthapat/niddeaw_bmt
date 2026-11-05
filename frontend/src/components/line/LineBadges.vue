<script setup lang="ts">
/**
 * "My badges" in LINE: the member's own shelf, the same one their profile
 * shows, with how far each quest has to go.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMyBadges } from '@/api/quests'
import { apiErrorMessage } from '@/api/errors'
import { shelfItems, type BadgeItem } from '@/utils/quests'
import type { Locale } from '@/i18n'
import BadgeShelf from '@/components/quests/BadgeShelf.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ back: [] }>()
const { t, locale } = useI18n()

const items = ref<BadgeItem[] | null>(null)
const problem = ref('')

onMounted(async () => {
  try {
    const data = await getMyBadges(props.token)
    if (data) items.value = shelfItems(data, t, locale.value as Locale)
    else problem.value = t('quests.off')
  } catch (e) {
    problem.value = apiErrorMessage(e, t('quests.loadFailed'))
  }
})
</script>

<template>
  <section class="flex flex-1 flex-col gap-4">
    <div>
      <p class="world-eyebrow">MY BADGES</p>
      <h1 class="world-title mt-1 text-2xl">{{ t('quests.mine') }}</h1>
    </div>
    <BadgeShelf v-if="items" :items="items" />
    <p v-else-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
    <p v-else class="text-sm text-white/60">{{ t('common.loading') }}</p>
    <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('back')">{{ t('quests.back') }}</button>
  </section>
</template>
