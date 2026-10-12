<script setup lang="ts">
import { ref, watch } from 'vue'
import { thumbUrl } from '@/utils/thumbUrl'

const props = defineProps<{ url: string; alt?: string }>()

// Receipts uploaded before thumbnails existed have none, and a receipt
// whose thumbnail failed to encode has none either, so a 404 here is an
// ordinary case rather than a fault: fall back to the full image, which is
// what the screen used to show anyway.
const src = ref(thumbUrl(props.url))
watch(
  () => props.url,
  (next) => {
    src.value = thumbUrl(next)
  },
)
</script>

<template>
  <a :href="url" target="_blank" rel="noopener noreferrer" class="shrink-0">
    <img
      :src="src"
      :alt="alt ?? ''"
      loading="lazy"
      decoding="async"
      class="h-14 w-14 rounded border border-brand-pink/20 object-cover"
      @error="src = url"
    />
  </a>
</template>
