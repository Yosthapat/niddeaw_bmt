<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getShopProducts } from '@/api/public'
import type { Product, SaleType } from '@/types'
import ProductCard from '@/components/shop/ProductCard.vue'
import CartLink from '@/components/shop/CartLink.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import PageBanner from '@/components/common/PageBanner.vue'

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
  <main class="pb-12 sm:pb-20">
    <PageBanner eyebrow="Club Shop" :title="t('shop.title')" :sub="t('shop.lead')" mascot="/tiers/highball.webp">
      <!-- the cart stays beside the filter: off to the right it would sit
           on the mascot on a desktop -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="seg" role="group" :aria-label="t('shop.filterLabel')">
          <button
            v-for="chip in chips"
            :key="chip.id"
            type="button"
            class="seg-btn"
            :class="{ on: kind === chip.id }"
            :aria-pressed="kind === chip.id"
            @click="kind = chip.id"
          >
            {{ chip.label }}
          </button>
        </div>
        <CartLink compact class="backdrop-blur" />
      </div>
    </PageBanner>

    <div class="home-world">
      <div class="mx-auto max-w-[1200px] px-3 pt-4 sm:px-6 sm:pt-7">
        <!-- how buying works, on a screen wide enough to say it in one line -->
        <ol class="mb-5 hidden gap-3 lg:flex">
          <li
            v-for="(step, i) in [t('shop.step1'), t('shop.step2'), t('shop.step3')]"
            :key="i"
            class="world-card flex min-h-[56px] flex-1 items-center gap-3 px-5 text-sm"
          >
            <span class="step-no">{{ i + 1 }}</span>{{ step }}
          </li>
        </ol>

        <div v-if="loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
          <HudSkeletonBlock v-for="i in 4" :key="i" :delay="i * 60" class="aspect-[3/4] rounded-[18px]" />
        </div>
        <p v-else-if="error" class="world-card p-5 text-status-error">{{ error }}</p>
        <p v-else-if="products.length === 0" class="world-card p-8 text-center text-white/65">{{ t('shop.empty') }}</p>
        <p v-else-if="shown.length === 0" class="world-card p-8 text-center text-white/65">{{ t('shop.emptyFilter') }}</p>
        <ul v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
          <li v-for="(p, i) in shown" :key="p.id" v-reveal="i">
            <ProductCard :product="p" />
          </li>
        </ul>
      </div>
    </div>
  </main>
</template>

<style scoped>
.step-no {
  display: flex;
  width: 30px;
  height: 30px;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  font-family: var(--font-display);
  font-weight: 700;
  box-shadow: 0 4px 14px rgb(234 76 164 / 0.45);
}
</style>
