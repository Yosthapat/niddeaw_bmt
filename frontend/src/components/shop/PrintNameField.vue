<script setup lang="ts">
/**
 * A name printed on the back of a shirt, for a product that offers it
 * (product.name_print_price). Left blank, nothing is printed. A Niddeaw
 * Pass holder ordering from LINE has it printed for nothing: the cart
 * shows that, priced by the server.
 */
import { useI18n } from 'vue-i18n'
import { money } from '@/utils/format'
import { MAX_PRINT_NAME } from '@/stores/cart'

defineProps<{ price: number }>()
const name = defineModel<string>({ required: true })
const { t } = useI18n()
</script>

<template>
  <label class="pn">
    <span class="flex items-baseline justify-between gap-2">
      <span class="text-sm font-medium">{{ t('shop.printName') }}</span>
      <span class="text-xs text-white/60">{{ price > 0 ? `+${money(price)} / ${t('shop.unit')}` : t('shop.printFree') }}</span>
    </span>
    <input
      v-model="name"
      type="text"
      :maxlength="MAX_PRINT_NAME"
      autocomplete="off"
      autocapitalize="characters"
      :placeholder="t('shop.printNamePlaceholder')"
      class="pn-input"
    />
    <span class="text-[11px] text-[#ffe58a]">✦ {{ t('shop.printPassHint') }}</span>
  </label>
</template>

<style scoped>
.pn {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pn-input {
  min-height: 46px;
  border: 1px solid rgb(255 255 255 / 0.22);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.07);
  padding: 0 14px;
  font-family: var(--font-display);
  font-size: 16px;
  letter-spacing: 0.06em;
  outline: none;
}
.pn-input:focus {
  border-color: var(--color-brand-pink);
}
</style>
