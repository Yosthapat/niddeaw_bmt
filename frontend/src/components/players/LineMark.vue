<script setup lang="ts">
/**
 * The green chat bubble that means "linked to LINE", the same on every
 * screen: on the corner of a face in the admin's lists, beside the member
 * code on the trading card.
 */
import { useI18n } from 'vue-i18n'

withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' })
const { t } = useI18n()
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center rounded-full bg-[#06c755] text-white"
    :class="size === 'md' ? 'h-5 w-5' : 'h-4 w-4'"
    :title="t('lineAdmin.badge')"
    role="img"
    :aria-label="t('lineAdmin.badge')"
  >
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" :class="size === 'md' ? 'h-3 w-3' : 'h-2.5 w-2.5'">
      <path d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5s5.9-3.5 8-6C21.4 14.2 22 12.7 22 11c0-4.4-4.5-8-10-8Z" />
    </svg>
  </span>
</template>
