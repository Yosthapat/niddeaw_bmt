<script setup lang="ts">
/**
 * "My badges" in LINE: first the quests the member is closest to finishing
 * ("almost there", with a bar each), then their own shelf, the same one
 * their profile shows.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMyBadges } from '@/api/quests'
import { apiErrorMessage } from '@/api/errors'
import { almostThere, shelfItems, type AlmostItem, type BadgeItem } from '@/utils/quests'
import type { Locale } from '@/i18n'
import BadgeShelf from '@/components/quests/BadgeShelf.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ back: [] }>()
const { t, locale } = useI18n()

const items = ref<BadgeItem[] | null>(null)
const almost = ref<AlmostItem[]>([])
const problem = ref('')

onMounted(async () => {
  try {
    const data = await getMyBadges(props.token)
    if (data) {
      items.value = shelfItems(data, t, locale.value as Locale)
      almost.value = almostThere(data, t, locale.value as Locale)
    } else problem.value = t('quests.off')
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
    <section v-if="almost.length" aria-labelledby="almost-title" class="flex flex-col gap-2">
      <h2 id="almost-title" class="font-display text-sm font-bold text-white/85">{{ t('quests.almost') }}</h2>
      <ul class="flex flex-col gap-2">
        <li v-for="a in almost" :key="a.id" class="almost">
          <img :src="a.img" alt="" width="256" height="256" class="medal" />
          <div class="min-w-0 flex-1">
            <p class="truncate font-display text-[15px] font-bold">{{ a.title }}</p>
            <p class="truncate text-xs text-white/65">{{ a.label }}</p>
            <div class="bar" role="progressbar" :aria-label="a.title" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(a.ratio * 100)">
              <span :style="{ width: `${Math.max(4, Math.round(a.ratio * 100))}%` }" />
            </div>
          </div>
        </li>
      </ul>
    </section>
    <BadgeShelf v-if="items" :items="items" />
    <p v-else-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
    <p v-else class="text-sm text-white/60">{{ t('common.loading') }}</p>
    <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('back')">{{ t('quests.back') }}</button>
  </section>
</template>

<style scoped>
.almost {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 16px;
  border: 1px solid rgb(255 255 255 / 0.08);
  background: rgb(255 255 255 / 0.05);
  padding: 10px 14px 10px 10px;
}
.medal {
  width: 48px;
  height: 48px;
  flex: none;
  object-fit: contain;
  filter: grayscale(1) brightness(0.55) contrast(0.95) drop-shadow(0 3px 4px rgb(0 0 0 / 0.5));
}
.bar {
  margin-top: 7px;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.1);
}
.bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f2c14e, #ff5fae);
}
</style>
