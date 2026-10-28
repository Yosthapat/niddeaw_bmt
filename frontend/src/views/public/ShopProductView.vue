<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getShopProduct } from '@/api/public'
import { apiErrorMessage } from '@/api/errors'
import type { Product } from '@/types'
import { formatDayMonth, money } from '@/utils/format'
import { BADGE_CLASS, productBadge } from '@/components/shop/productBadge'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const product = ref<Product | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const size = ref('')
const qty = ref(1)

watch(
  () => route.params.id,
  async (id) => {
    loading.value = true
    error.value = null
    try {
      product.value = await getShopProduct(String(id))
      size.value = ''
      qty.value = 1
    } catch (e) {
      error.value = apiErrorMessage(e, t('shop.loadFailed'))
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

const day = (iso: string | null): string => (iso ? formatDayMonth(iso, locale.value as 'th' | 'en') : '—')
const isPre = computed(() => product.value?.sale_type === 'preorder')
const hasSizes = computed(() => (product.value?.sizes.length ?? 0) > 0)
const left = (s: string): number => (isPre.value ? Infinity : (product.value?.stock[s] ?? 0))
const chosenSize = computed(() => (hasSizes.value ? size.value : ''))
// How many can be ordered of what is chosen: ten at most, and no more than
// the shelf holds.
const maxQty = computed(() => Math.min(10, hasSizes.value && !size.value ? 10 : left(chosenSize.value)))
watch(maxQty, (m) => {
  if (qty.value > m) qty.value = Math.max(1, m)
})

const badge = computed(() => {
  if (!product.value) return null
  const b = productBadge(product.value)
  const params = { ...b.params }
  if (typeof params.date === 'string' && params.date) params.date = day(params.date)
  return { text: t(b.key, params), cls: BADGE_CLASS[b.tone] }
})

// The button says why it can't be pressed instead of just greying out.
const blocker = computed(() => {
  const p = product.value
  if (!p) return null
  if (!p.open) return isPre.value ? t('shop.closed') : t('shop.soldOut')
  if (hasSizes.value && !size.value) return t('shop.needSize')
  if (left(chosenSize.value) < 1) return t('shop.soldOut')
  return null
})

const photo = ref(0)
function next(): void {
  router.push({ path: `/shop/${product.value!.id}/order`, query: { size: chosenSize.value || undefined, qty: String(qty.value) } })
}
</script>

<template>
  <main class="mx-auto max-w-5xl px-4 pt-4 pb-40 sm:pb-12">
    <RouterLink to="/shop" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70 hover:text-white">
      <span aria-hidden="true">←</span> {{ t('shop.back') }}
    </RouterLink>

    <div v-if="loading" class="mt-3 space-y-3">
      <HudSkeletonBlock class="aspect-square max-h-80 w-full" />
      <HudSkeletonBlock :delay="80" class="h-16" />
    </div>
    <p v-else-if="error || !product" class="mt-6 text-status-error">{{ error }}</p>

    <div v-else class="mt-2 grid gap-6 md:grid-cols-2 md:gap-10">
      <!-- photos: swipe on a phone, dots to say there are more -->
      <div>
        <div class="relative overflow-hidden rounded-[20px] border border-white/14 bg-[radial-gradient(circle_at_50%_40%,rgb(234_76_164/0.5),#1a0d33_75%)]">
          <div
            class="photo-strip flex aspect-square snap-x snap-mandatory overflow-x-auto"
            @scroll="photo = Math.round(($event.target as HTMLElement).scrollLeft / ($event.target as HTMLElement).clientWidth)"
          >
            <template v-if="product.image_urls.length">
              <img
                v-for="(url, i) in product.image_urls"
                :key="url"
                :src="url"
                :alt="`${product.name} ${i + 1}/${product.image_urls.length}`"
                class="h-full w-full flex-none snap-center object-cover"
              />
            </template>
            <div v-else class="flex h-full w-full flex-none items-center justify-center">
              <img src="/pwa-icons/pwa-192x192.png" alt="" class="h-1/3 w-1/3 rounded-full opacity-70" />
            </div>
          </div>
          <span v-if="badge" class="absolute top-3 left-3 rounded-full px-3 py-1.5 text-xs leading-none font-medium" :class="badge.cls">
            {{ badge.text }}
          </span>
          <div v-if="product.image_urls.length > 1" class="absolute right-0 bottom-3 left-0 flex justify-center gap-1.5" aria-hidden="true">
            <span
              v-for="(_, i) in product.image_urls"
              :key="i"
              class="h-1.5 rounded-full transition-all"
              :class="i === photo ? 'w-5 bg-white' : 'w-1.5 bg-white/40'"
            />
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-5">
        <div class="flex items-end justify-between gap-3">
          <h1 class="font-display text-2xl leading-tight font-bold sm:text-3xl">{{ product.name }}</h1>
          <span class="shrink-0 font-display text-2xl font-bold text-brand-pink-light">{{ money(product.price) }}</span>
        </div>
        <p v-if="product.description" class="text-sm whitespace-pre-line text-white/75">{{ product.description }}</p>

        <dl v-if="isPre" class="grid grid-cols-3 gap-2 rounded-2xl border border-[#ffe14d]/35 bg-[#ffe14d]/8 p-3 text-center">
          <div><dt class="text-[11px] text-white/65">{{ t('shop.closesOn') }}</dt><dd class="text-sm font-medium">{{ day(product.preorder_closes_on) }}</dd></div>
          <div><dt class="text-[11px] text-white/65">{{ t('shop.deliversOn') }}</dt><dd class="text-sm font-medium">{{ day(product.preorder_delivers_on) }}</dd></div>
          <div><dt class="text-[11px] text-white/65">{{ t('shop.orderedSoFar') }}</dt><dd class="text-sm font-medium">{{ t('shop.units', { n: product.ordered }) }}</dd></div>
        </dl>

        <fieldset v-if="hasSizes" class="flex flex-col gap-2">
          <legend class="mb-2 text-sm font-medium">{{ t('shop.size') }}</legend>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="s in product.sizes"
              :key="s"
              type="button"
              class="size-btn"
              :aria-pressed="size === s"
              :disabled="left(s) < 1"
              :aria-label="left(s) < 1 ? t('shop.sizeSoldOut', { size: s }) : s"
              @click="size = s"
            >
              {{ s }}
            </button>
          </div>
        </fieldset>

        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">{{ t('shop.qty') }}</span>
          <div class="flex items-center gap-2.5">
            <button type="button" class="step-btn" :aria-label="t('shop.less')" :disabled="qty <= 1" @click="qty--">−</button>
            <span aria-live="polite" class="min-w-6 text-center font-display text-xl font-bold">{{ qty }}</span>
            <button type="button" class="step-btn" :aria-label="t('shop.more')" :disabled="qty >= maxQty" @click="qty++">+</button>
          </div>
        </div>
        <p v-if="!isPre && (!hasSizes || size) && maxQty > 0 && maxQty < 10" class="-mt-3 text-right text-xs text-white/60">
          {{ t('shop.maxLeft', { n: maxQty }) }}
        </p>

        <!-- desktop: the button sits under the choices -->
        <div class="hidden items-center gap-4 md:flex">
          <span class="font-display text-xl font-bold">{{ money(product.price * qty) }}</span>
          <button type="button" class="buy-btn flex-1" :disabled="!!blocker" @click="next">
            {{ blocker ?? (isPre ? t('shop.orderPreorder') : t('shop.order')) }}
          </button>
        </div>
      </div>
    </div>

    <!-- phone: a buy bar above the tab bar -->
    <div
      v-if="product && !loading"
      class="fixed inset-x-0 bottom-[calc(96px+env(safe-area-inset-bottom,0px))] z-20 flex items-center gap-3 border-t border-white/8 bg-[#0b0518]/95 px-4 py-3 backdrop-blur md:hidden"
    >
      <div class="flex flex-col">
        <span class="text-xs text-white/65">
          {{ hasSizes ? t('shop.summary', { size: size || '—', qty }) : t('shop.summaryOne', { qty }) }}
        </span>
        <span class="font-display text-lg font-bold">{{ money(product.price * qty) }}</span>
      </div>
      <button type="button" class="buy-btn flex-1" :disabled="!!blocker" @click="next">
        {{ blocker ?? (isPre ? t('shop.orderPreorder') : t('shop.order')) }}
      </button>
    </div>
  </main>
</template>

<style scoped>
.photo-strip {
  scrollbar-width: none;
}
.photo-strip::-webkit-scrollbar {
  display: none;
}
.size-btn {
  min-width: 54px;
  height: 46px;
  padding: 0 12px;
  border: 1px solid rgb(255 255 255 / 0.2);
  border-radius: 12px;
  background: rgb(255 255 255 / 0.06);
  font-family: var(--font-display);
  font-weight: 700;
}
.size-btn[aria-pressed='true'] {
  border-color: #fff;
  background: #fff;
  color: #1a0d33;
  box-shadow: 0 6px 16px rgb(255 108 192 / 0.35);
}
.size-btn:disabled {
  opacity: 0.35;
  text-decoration: line-through;
}
.step-btn {
  width: 44px;
  height: 44px;
  border: 1px solid rgb(255 255 255 / 0.2);
  border-radius: 12px;
  background: rgb(255 255 255 / 0.06);
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
}
.step-btn:disabled {
  opacity: 0.35;
}
.buy-btn {
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(#ff8fd0, var(--color-brand-pink) 55%, #c22f86);
  box-shadow:
    0 5px 0 #6d1247,
    0 12px 24px rgb(234 76 164 / 0.4),
    inset 0 1px 0 rgb(255 255 255 / 0.55);
  color: #fff;
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
}
.buy-btn:disabled {
  background: rgb(255 255 255 / 0.12);
  box-shadow: none;
  color: rgb(255 255 255 / 0.7);
}
</style>
