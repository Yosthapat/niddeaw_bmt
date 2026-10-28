<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getShopProducts } from '@/api/public'
import type { Product, SaleType } from '@/types'
import ProductCard from '@/components/shop/ProductCard.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

const { t } = useI18n()
const products = ref<Product[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const kind = ref<SaleType | 'all'>('all')

onMounted(async () => {
  try {
    products.value = await getShopProducts()
  } catch {
    error.value = t('shop.loadFailed')
  } finally {
    loading.value = false
  }
})

// What can be bought now first; sold-out and closed at the end.
const shown = computed(() =>
  products.value
    .filter((p) => kind.value === 'all' || p.sale_type === kind.value)
    .sort((a, b) => Number(b.open) - Number(a.open)),
)
const chips = computed<{ id: SaleType | 'all'; label: string }[]>(() => [
  { id: 'all', label: t('shop.filterAll') },
  { id: 'stock', label: t('shop.filterStock') },
  { id: 'preorder', label: t('shop.filterPreorder') },
])
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-6 sm:py-10">
    <RouterLink to="/" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70 hover:text-white">
      <span aria-hidden="true">←</span> {{ t('shop.backHome') }}
    </RouterLink>

    <div class="mt-1 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="font-display text-xs font-semibold tracking-[0.25em] text-brand-pink/80">CLUB SHOP</p>
        <h1 class="font-display text-3xl font-bold sm:text-5xl">{{ t('shop.title') }}</h1>
        <p class="mt-1 text-sm text-white/70 sm:hidden">{{ t('shop.lead') }}</p>
      </div>
      <ol class="hidden gap-2.5 lg:flex">
        <li v-for="(step, i) in [t('shop.step1'), t('shop.step2'), t('shop.step3')]" :key="i" class="flex min-h-[52px] items-center gap-2.5 rounded-2xl border border-white/14 bg-white/6 px-4 text-sm">
          <span class="font-display font-bold text-brand-pink-light">{{ i + 1 }}</span>{{ step }}
        </li>
      </ol>
    </div>

    <div role="group" :aria-label="t('shop.filterLabel')" class="mt-5 flex gap-2 overflow-x-auto">
      <button
        v-for="chip in chips"
        :key="chip.id"
        type="button"
        class="shop-chip"
        :aria-pressed="kind === chip.id"
        @click="kind = chip.id"
      >
        {{ chip.label }}
      </button>
    </div>

    <div v-if="loading" class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
      <HudSkeletonBlock v-for="i in 4" :key="i" :delay="i * 60" class="aspect-[3/4]" />
    </div>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="products.length === 0" class="mt-10 text-center text-white/65">{{ t('shop.empty') }}</p>
    <p v-else-if="shown.length === 0" class="mt-10 text-center text-white/65">{{ t('shop.emptyFilter') }}</p>
    <ul v-else class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
      <li v-for="p in shown" :key="p.id">
        <ProductCard :product="p" />
      </li>
    </ul>
  </main>
</template>

<style scoped>
.shop-chip {
  display: inline-flex;
  min-height: 44px;
  flex: none;
  align-items: center;
  padding: 0 16px;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.06);
  color: rgb(255 255 255 / 0.82);
  font-size: 14px;
}
.shop-chip[aria-pressed='true'] {
  border-color: rgb(255 255 255 / 0.4);
  background: radial-gradient(120% 140% at 30% 0%, rgb(255 255 255 / 0.4), rgb(255 255 255 / 0.1) 60%);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.7),
    inset 0 -3px 8px rgb(234 76 164 / 0.38),
    0 6px 14px rgb(234 76 164 / 0.35);
  color: #fff;
}
</style>
