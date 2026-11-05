<script setup lang="ts">
/** "Ball & Bank", each name followed by their credit card if they hold one. */
import CreditCardMark from '@/components/credit/CreditCardMark.vue'

defineProps<{ ids: string[]; nameOf: (id: string) => string }>()
</script>

<template>
  <template v-for="(id, i) in ids" :key="id"><template v-if="i > 0">{{ ' & ' }}</template>{{ nameOf(id) }}<CreditCardMark :player-id="id" class="ml-1" /></template>
</template>
