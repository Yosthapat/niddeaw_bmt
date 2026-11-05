<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getShopProduct } from '@/api/public'
import { apiErrorMessage } from '@/api/errors'
import type { Product } from '@/types'
import { priceOf, priceRange } from '@/types'
import { formatDayMonth, money } from '@/utils/format'
import { useCartStore, MAX_LINE_QTY } from '@/stores/cart'
import { BADGE_CLASS, productBadge } from '@/components/shop/productBadge'
import ProductGallery from '@/components/shop/ProductGallery.vue'
import CartLink from '@/components/shop/CartLink.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const cart = useCartStore()
const product = ref<Product | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const size = ref('')
const qty = ref(1)
const sizesBox = ref<HTMLElement | null>(null)
const nudge = ref(false)
const added = ref<string | null>(null)
let addedTimer: ReturnType<typeof setTimeout> | undefined

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
onBeforeUnmount(() => clearTimeout(addedTimer))

const day = (iso: string | null): string => (iso ? formatDayMonth(iso, locale.value as 'th' | 'en') : '—')
const isPre = computed(() => product.value?.sale_type === 'preorder')
const hasSizes = computed(() => (product.value?.sizes.length ?? 0) > 0)
const chosenSize = computed(() => (hasSizes.value ? size.value : ''))
const sizePicked = computed(() => !hasSizes.value || !!size.value)
const left = (s: string): number => (isPre.value ? Infinity : (product.value?.stock[s] ?? 0))
const inCart = (s: string): number => (product.value ? (cart.find(product.value.id, s)?.qty ?? 0) : 0)
// Sizes that cost differently show their price on their button.
const pricesDiffer = computed(() => {
  const p = product.value
  if (!p) return false
  const [lo, hi] = priceRange(p)
  return lo !== hi
})
const price = computed(() => (product.value ? priceOf(product.value, chosenSize.value) : 0))
const priceLabel = computed(() => {
  const p = product.value
  if (!p) return ''
  if (sizePicked.value || !pricesDiffer.value) return money(price.value)
  const [lo, hi] = priceRange(p)
  return `${money(lo)} – ${money(hi)}`
})

// How many more of the chosen size can go in: ten a line at most, no more
// than the shelf holds, minus what the cart already has of it.
const maxQty = computed(() => {
  if (!sizePicked.value) return MAX_LINE_QTY
  const s = chosenSize.value
  return Math.max(0, Math.min(MAX_LINE_QTY, left(s)) - inCart(s))
})
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

// Why nothing can be added, said on the button instead of just greying it.
// "Pick a size" is not one of these: that button stays live and takes you
// to the sizes.
const blocker = computed(() => {
  const p = product.value
  if (!p) return null
  if (!p.open) return isPre.value ? t('shop.closed') : t('shop.soldOut')
  if (!sizePicked.value) return null
  if (left(chosenSize.value) < 1) return t('shop.soldOut')
  if (maxQty.value < 1) return t('shop.maxInCart')
  return null
})

/** On a phone the sizes can be a long description away from the buy bar:
 *  bring them into view and make them stand out for a moment. */
async function toSizes(): Promise<void> {
  if (!sizesBox.value) {
    // one size: nothing to pick, so go to the price and the buttons
    document.querySelector('main h1')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  sizesBox.value.scrollIntoView({ behavior: 'smooth', block: 'center' })
  nudge.value = false
  await nextTick()
  nudge.value = true
  sizesBox.value?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus({ preventScroll: true })
}

function addToCart(): boolean {
  const p = product.value
  if (!p) return false
  if (!sizePicked.value) {
    void toSizes()
    return false
  }
  if (blocker.value) return false
  const n = cart.add(p.id, chosenSize.value, qty.value)
  if (n < 1) return false
  added.value = chosenSize.value ? t('shop.addedSize', { size: chosenSize.value, n }) : t('shop.addedOne', { n })
  clearTimeout(addedTimer)
  addedTimer = setTimeout(() => (added.value = null), 4000)
  qty.value = 1
  return true
}

function buyNow(): void {
  if (addToCart()) router.push('/shop/cart')
}

// A product with a turnaround clip opens on it: the clip loops under a
// spotlight, plays only while it is on screen, and waits for a tap when the
// phone asks for less motion.
const still = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const clip = ref<HTMLVideoElement | null>(null)
const playing = ref(false)
let seen: IntersectionObserver | null = null
function play(): void {
  void clip.value?.play().catch(() => {})
}
function toggleClip(): void {
  const v = clip.value
  if (!v) return
  if (v.paused) play()
  else v.pause()
}
watch(clip, (v) => {
  seen?.disconnect()
  seen = null
  if (!v || still || !('IntersectionObserver' in window)) return
  seen = new IntersectionObserver(([e]) => (e?.isIntersecting ? play() : v.pause()), { threshold: 0.25 })
  seen.observe(v)
})
onBeforeUnmount(() => seen?.disconnect())
</script>

<template>
  <!-- the world the rest of the site stands in, behind this page too -->
  <div class="home-world">
    <main class="mx-auto max-w-5xl px-4 pt-4 pb-44 sm:pb-12">
      <div class="flex items-center justify-between gap-3">
        <RouterLink to="/shop" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70 hover:text-white">
          <span aria-hidden="true">←</span> {{ t('shop.back') }}
        </RouterLink>
        <CartLink />
      </div>

      <!-- the turnaround, when the product has one -->
      <section v-if="!loading && product?.video_url" class="cine bars -mx-4 mt-3 md:mx-0" :aria-label="product.name">
        <div class="beam" aria-hidden="true" />
        <div class="cine-titles" aria-hidden="true">
          <span class="cine-eyebrow">NIDDEAW BADMINTON CLUB</span>
          <span class="cine-name">{{ product.name }}</span>
          <span class="cine-price">{{ priceLabel }}<template v-if="isPre"> · {{ t('shop.preorderTag') }}</template></span>
        </div>
        <div class="screen">
          <video
            ref="clip"
            :src="product.video_url"
            :poster="product.image_urls[0]"
            muted
            loop
            playsinline
            preload="auto"
            :autoplay="!still"
            :aria-label="t('shop.clipLabel', { name: product.name })"
            @play="playing = true"
            @pause="playing = false"
          />
        </div>
        <button type="button" class="cine-cue" @click="toSizes">{{ hasSizes ? t('shop.clipToSizes') : t('shop.clipToBuy') }} <span aria-hidden="true">↓</span></button>
        <button type="button" class="cine-pp" :aria-label="playing ? t('shop.clipPause') : t('shop.clipPlay')" @click="toggleClip">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path :d="playing ? 'M7 5h3v14H7zM14 5h3v14h-3z' : 'M8 5v14l11-7z'" /></svg>
        </button>
      </section>

      <div v-if="loading" class="mt-3 space-y-3">
        <HudSkeletonBlock class="aspect-square max-h-80 w-full" />
        <HudSkeletonBlock :delay="80" class="h-16" />
      </div>
      <p v-else-if="error || !product" class="mt-6 text-status-error">{{ error }}</p>

      <div v-else class="mt-2 grid gap-6 md:grid-cols-2 md:items-start md:gap-10">
        <ProductGallery :images="product.image_urls" :name="product.name" class="md:sticky md:top-24">
          <span v-if="badge" class="pointer-events-none absolute top-3 left-3 rounded-full px-3 py-1.5 text-xs leading-none font-medium" :class="badge.cls">
            {{ badge.text }}
          </span>
        </ProductGallery>

        <div class="flex flex-col gap-5">
          <div class="flex items-end justify-between gap-3">
            <h1 class="font-display text-2xl leading-tight font-bold sm:text-3xl">{{ product.name }}</h1>
            <span class="shrink-0 font-display text-2xl font-bold text-brand-pink-light" aria-live="polite">{{ priceLabel }}</span>
          </div>

          <dl v-if="isPre" class="grid grid-cols-2 gap-2 rounded-2xl border border-[#ffe14d]/35 bg-[#ffe14d]/8 p-3 text-center">
            <div><dt class="text-[11px] text-white/65">{{ t('shop.closesOn') }}</dt><dd class="text-sm font-medium">{{ day(product.preorder_closes_on) }}</dd></div>
            <div><dt class="text-[11px] text-white/65">{{ t('shop.deliversOn') }}</dt><dd class="text-sm font-medium">{{ day(product.preorder_delivers_on) }}</dd></div>
          </dl>

          <fieldset v-if="hasSizes" ref="sizesBox" class="sizes flex scroll-mt-24 flex-col gap-2 rounded-2xl" :class="{ nudge }" @animationend="nudge = false">
            <legend class="mb-2 text-sm font-medium">{{ t('shop.size') }}</legend>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="s in product.sizes"
                :key="s"
                type="button"
                class="size-btn"
                :aria-pressed="size === s"
                :disabled="left(s) < 1"
                :aria-label="left(s) < 1 ? t('shop.sizeSoldOut', { size: s }) : pricesDiffer ? `${s} ${money(priceOf(product, s))}` : s"
                @click="size = s"
              >
                <span>{{ s }}</span>
                <span v-if="pricesDiffer" class="text-[11px] font-normal opacity-75">{{ money(priceOf(product, s)) }}</span>
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
          <p v-if="sizePicked && inCart(chosenSize) > 0" class="-mt-3 text-right text-xs text-white/60">
            {{ t('shop.inCartAlready', { n: inCart(chosenSize) }) }}
          </p>
          <p v-else-if="!isPre && sizePicked && maxQty > 0 && maxQty < MAX_LINE_QTY" class="-mt-3 text-right text-xs text-white/60">
            {{ t('shop.maxLeft', { n: maxQty }) }}
          </p>

          <!-- desktop: the buttons sit under the choices -->
          <div class="hidden items-center gap-3 md:flex">
            <span class="font-display text-xl font-bold">{{ sizePicked ? money(price * qty) : priceLabel }}</span>
            <button type="button" class="ghost-btn flex-1" :disabled="!!blocker" @click="addToCart">
              {{ blocker ?? (sizePicked ? t('shop.addToCart') : t('shop.needSize')) }}
            </button>
            <button v-if="!blocker" type="button" class="buy-btn flex-1" @click="buyNow">
              {{ isPre ? t('shop.orderPreorder') : t('shop.buyNow') }}
            </button>
          </div>

          <p v-if="product.description" class="text-sm whitespace-pre-line text-white/75">{{ product.description }}</p>
        </div>
      </div>

      <p
        v-if="added"
        role="status"
        class="added fixed inset-x-4 bottom-[calc(170px+env(safe-area-inset-bottom,0px))] z-30 mx-auto flex max-w-md items-center justify-between gap-3 rounded-2xl border border-[#7ff0b4]/40 bg-[#10241b] px-4 py-3 text-sm md:bottom-8"
      >
        <span>✓ {{ added }}</span>
        <RouterLink to="/shop/cart" class="font-medium text-[#7ff0b4] underline">{{ t('shop.viewCart', { n: cart.count }) }}</RouterLink>
      </p>

      <!-- phone: the buy bar above the tab bar -->
      <div
        v-if="product && !loading"
        class="fixed inset-x-0 bottom-[calc(96px+env(safe-area-inset-bottom,0px))] z-20 flex items-center gap-2.5 border-t border-white/8 bg-[#0b0518]/95 px-4 py-3 backdrop-blur md:hidden"
      >
        <div class="flex min-w-0 flex-col">
          <span class="truncate text-xs text-white/65">
            {{ hasSizes ? t('shop.summary', { size: size || '—', qty }) : t('shop.summaryOne', { qty }) }}
          </span>
          <span class="font-display text-lg font-bold whitespace-nowrap">{{ sizePicked ? money(price * qty) : priceLabel }}</span>
        </div>
        <template v-if="blocker">
          <button type="button" class="buy-btn flex-1" disabled>{{ blocker }}</button>
        </template>
        <template v-else-if="!sizePicked">
          <button type="button" class="buy-btn flex-1" @click="toSizes">{{ t('shop.needSize') }}</button>
        </template>
        <template v-else>
          <button type="button" class="ghost-btn" :aria-label="t('shop.addToCart')" @click="addToCart">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2M12 9v5M9.5 11.5h5" /><circle cx="10" cy="20" r="1.2" /><circle cx="17" cy="20" r="1.2" /></svg>
            <span class="max-[379px]:sr-only">{{ t('shop.addShort') }}</span>
          </button>
          <button type="button" class="buy-btn flex-1" @click="buyNow">{{ isPre ? t('shop.orderPreorder') : t('shop.buyNow') }}</button>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.size-btn {
  display: flex;
  min-width: 58px;
  min-height: 50px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border: 1px solid rgb(255 255 255 / 0.2);
  border-radius: 12px;
  background: rgb(255 255 255 / 0.06);
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1.15;
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
/* "pick a size first": the picker pulses once where it is */
.sizes.nudge {
  animation: nudge 0.9s ease-out;
}
@keyframes nudge {
  0% {
    box-shadow: 0 0 0 0 rgb(255 108 192 / 0.9);
  }
  60% {
    box-shadow: 0 0 0 10px rgb(255 108 192 / 0);
  }
  100% {
    box-shadow: none;
  }
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
  padding: 0 14px;
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
.ghost-btn {
  display: flex;
  height: 54px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  border: 1px solid rgb(255 255 255 / 0.3);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.08);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
}
.ghost-btn:disabled {
  opacity: 0.6;
}
.added {
  animation: pop 0.25s ease-out;
}

/* ---- the turnaround: a dark stage, the clip under a spotlight ---- */
.cine {
  position: relative;
  /* on a phone the stage fits between the header and the buy bar + tab bar */
  height: clamp(440px, calc(100svh - 300px), 760px);
  overflow: hidden;
  background:
    radial-gradient(60% 46% at 50% 54%, rgb(255 79 166 / 0.16), transparent 70%),
    radial-gradient(80% 60% at 50% 110%, rgb(120 40 140 / 0.3), transparent 70%),
    #07050a;
}
@media (min-width: 768px) {
  .cine {
    height: min(80svh, 760px);
    border-radius: 24px;
  }
}
.beam {
  position: absolute;
  top: -10%;
  left: 50%;
  width: 70vmax;
  height: 120%;
  translate: -50% 0;
  background: conic-gradient(from 180deg at 50% 0%, transparent 168deg, rgb(255 190 230 / 0.08) 176deg, rgb(255 190 230 / 0.13) 180deg, rgb(255 190 230 / 0.08) 184deg, transparent 192deg);
  filter: blur(6px);
  pointer-events: none;
}
.bars::before,
.bars::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  z-index: 4;
  height: 4%;
  background: #000;
}
.bars::before {
  top: 0;
}
.bars::after {
  bottom: 0;
}
.screen {
  position: absolute;
  left: 50%;
  bottom: 4%;
  height: 80%;
  aspect-ratio: 9 / 16;
  max-width: 100%;
  translate: -50% 0;
}
.screen video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* closest-side: fully gone at the clip's own edges, so no seam shows */
  -webkit-mask-image: radial-gradient(closest-side, #000 52%, transparent 100%);
  mask-image: radial-gradient(closest-side, #000 52%, transparent 100%);
}
.cine-titles {
  position: absolute;
  z-index: 5;
  top: 8%;
  left: 16px;
  right: 16px;
  display: grid;
  gap: 4px;
  text-align: center;
  pointer-events: none;
}
.cine-eyebrow {
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.4em;
  color: #ff9fd6;
}
.cine-name {
  font-family: var(--font-display);
  font-size: clamp(26px, 7.5vw, 48px);
  font-weight: 700;
  line-height: 1.02;
  letter-spacing: 0.03em;
  text-wrap: balance;
  text-shadow: 0 0 30px rgb(255 79 166 / 0.35);
}
.cine-price {
  font-size: 13px;
  color: rgb(255 255 255 / 0.7);
}
.cine-cue {
  position: absolute;
  z-index: 6;
  left: 50%;
  bottom: calc(4% + 10px);
  translate: -50% 0;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 999px;
  background: rgb(7 5 10 / 0.55);
  backdrop-filter: blur(6px);
  font-size: 13px;
  white-space: nowrap;
}
.cine-pp {
  position: absolute;
  z-index: 6;
  right: 16px;
  bottom: calc(4% + 10px);
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 50%;
  background: rgb(7 5 10 / 0.55);
}
.cine-cue:focus-visible,
.cine-pp:focus-visible {
  outline: 2px solid #ff9fd6;
  outline-offset: 2px;
}
@keyframes pop {
  from {
    opacity: 0;
    translate: 0 8px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .sizes.nudge,
  .added {
    animation: none;
  }
}
</style>
