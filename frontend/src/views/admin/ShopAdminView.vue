<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import type { OrderStatus, PreorderTally, Product, SaleType, ShopOrderAdmin, ShopOrderItem } from '@/types'
import { formatPhone, orderNo, priceOf, priceRange } from '@/types'
import { ApiError } from '@/api/client'
import { formatDayMonth, formatDateTime, money } from '@/utils/format'
import { bahtProblem, localToday, MAX_NAME } from '@/utils/limits'
import { compressImage } from '@/utils/imageCompression'
import AdminNav from '@/components/layout/AdminNav.vue'

const PRESET_SIZES = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL']
const MAX_SIZES = 16
const MAX_SIZE_LEN = 12
const MAX_PHOTOS = 4

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const lang = computed(() => locale.value as 'th' | 'en')

const tab = ref<'orders' | 'products'>('orders')
const orders = ref<ShopOrderAdmin[]>([])
const tally = ref<PreorderTally[]>([])
const products = ref<Product[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)
const actionError = ref<string | null>(null)
const busy = ref<string | null>(null)

onMounted(async () => {
  try {
    const [o, tl, p] = await Promise.all([adminApi.getShopOrders(), adminApi.getPreorderTally(), adminApi.getAdminProducts()])
    orders.value = o
    tally.value = tl
    products.value = p
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('shopAdmin.loadFailed'))
  } finally {
    loading.value = false
  }
})

// ------------------------------------------------------------------ orders
type Group = 'pending' | 'confirmed' | 'delivered' | 'rejected'
const group = ref<Group>('pending')
const count = (s: OrderStatus): number => orders.value.filter((o) => o.status === s).length
const groups = computed(() => [
  { id: 'pending' as Group, label: t('shopAdmin.tabPending', { n: count('pending') }) },
  { id: 'confirmed' as Group, label: t('shopAdmin.tabConfirmed', { n: count('confirmed') }) },
  { id: 'delivered' as Group, label: t('shopAdmin.tabDone') },
  { id: 'rejected' as Group, label: t('shopAdmin.tabRejected') },
])
const shownOrders = computed(() => orders.value.filter((o) => o.status === group.value))
const openTally = computed(() => tally.value.filter((x) => x.total > 0 || products.value.some((p) => p.id === x.product_id && p.open)))
const rejecting = ref<string | null>(null)
const reason = ref('')
const copiedId = ref<string | null>(null)

async function move(order: ShopOrderAdmin, status: OrderStatus, note?: string): Promise<void> {
  busy.value = order.id
  actionError.value = null
  try {
    const updated = await adminApi.updateShopOrder(order.id, status, note)
    orders.value = orders.value.map((o) => (o.id === updated.id ? updated : o))
    rejecting.value = null
    reason.value = ''
    // a refused or restored order changes what is left and what is ordered
    const [tl, p] = await Promise.all([adminApi.getPreorderTally(), adminApi.getAdminProducts()])
    tally.value = tl
    products.value = p
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('shopAdmin.actionFailed'))
  } finally {
    busy.value = null
  }
}

// ------------------------------------------------------- fixing a line
// A member who picked M meaning XL: the admin changes the size (or how
// many) here. The server prices the line again at the new size and moves
// the stock; the screen shows the difference first, so the admin knows
// what to collect or give back.
interface Draft {
  size: string
  qty: number
}
const fixing = ref<string | null>(null)
const drafts = ref<Record<string, Draft>>({})
const fixError = ref<string | null>(null)
const lastFix = ref<{ id: string; before: number; after: number } | null>(null)
const productOf = (item: ShopOrderItem): Product | null => products.value.find((p) => p.id === item.product_id) ?? null
const canFix = (item: ShopOrderItem): boolean => !!item.id && !!productOf(item)

function startFix(o: ShopOrderAdmin): void {
  fixing.value = o.id
  fixError.value = null
  drafts.value = Object.fromEntries(o.items.filter((i) => i.id).map((i) => [i.id as string, { size: i.size, qty: i.qty }]))
}
function draftLine(item: ShopOrderItem): number {
  const d = item.id ? drafts.value[item.id] : undefined
  const p = productOf(item)
  return d && p ? priceOf(p, d.size) * d.qty : item.line_total
}
const draftTotal = (o: ShopOrderAdmin): number => o.items.reduce((sum, i) => sum + draftLine(i), 0)
const changed = (item: ShopOrderItem): boolean => {
  const d = item.id ? drafts.value[item.id] : undefined
  return !!d && (d.size !== item.size || d.qty !== item.qty)
}
/** Units of `size` that could go on this line: what's on the shelf, plus
 *  what this line already holds of that size. A pre-order has no limit. */
function roomFor(item: ShopOrderItem, size: string): number {
  const p = productOf(item)
  if (!p || item.sale_type === 'preorder') return 10
  return (p.stock[size] ?? 0) + (size === item.size ? item.qty : 0)
}
function diffText(before: number, after: number): string {
  if (after > before) return t('shopAdmin.fixCollect', { amount: money(after - before) })
  if (after < before) return t('shopAdmin.fixRefund', { amount: money(before - after) })
  return t('shopAdmin.fixSame')
}

async function saveFix(o: ShopOrderAdmin): Promise<void> {
  busy.value = o.id
  fixError.value = null
  const before = o.total
  let updated: ShopOrderAdmin | null = null
  try {
    for (const item of o.items) {
      if (!item.id || !changed(item)) continue
      const d = drafts.value[item.id]
      updated = await adminApi.updateShopOrderItem(o.id, item.id, {
        ...(d.size !== item.size ? { size: d.size } : {}),
        ...(d.qty !== item.qty ? { qty: d.qty } : {}),
      })
    }
    if (updated) {
      const done = updated
      orders.value = orders.value.map((x) => (x.id === done.id ? done : x))
      lastFix.value = { id: done.id, before, after: done.total }
      const [tl, p] = await Promise.all([adminApi.getPreorderTally(), adminApi.getAdminProducts()])
      tally.value = tl
      products.value = p
    }
    fixing.value = null
  } catch (e) {
    fixError.value = apiErrorMessage(e, t('shopAdmin.fixFailed'))
    // what did go through is on the server; show it
    orders.value = await adminApi.getShopOrders().catch(() => orders.value)
  } finally {
    busy.value = null
  }
}

// ------------------------------------------------------- deleting an order
// For a test, a duplicate, a mistake. Gone for good, so the sheet says what
// happens and asks for the admin's own password again.
const deleting = ref<ShopOrderAdmin | null>(null)
const deletePassword = ref('')
const deleteError = ref<string | null>(null)
const deletedNote = ref<string | null>(null)
const passwordBox = ref<HTMLInputElement | null>(null)

function askDelete(o: ShopOrderAdmin): void {
  deleting.value = o
  deletePassword.value = ''
  deleteError.value = null
  setTimeout(() => passwordBox.value?.focus(), 50)
}
function stockBack(o: ShopOrderAdmin): string[] {
  if (o.status === 'rejected') return []
  return o.items.filter((i) => i.sale_type === 'stock').map((i) => [i.product_name, i.size, `× ${i.qty}`].filter(Boolean).join(' '))
}

async function confirmDelete(): Promise<void> {
  const o = deleting.value
  if (!o || !deletePassword.value) return
  busy.value = o.id
  deleteError.value = null
  try {
    await adminApi.deleteShopOrder(o.id, deletePassword.value)
    orders.value = orders.value.filter((x) => x.id !== o.id)
    deletedNote.value = t('shopAdmin.deletedNote', { no: orderNo(o.order_no) })
    deleting.value = null
    const [tl, p] = await Promise.all([adminApi.getPreorderTally(), adminApi.getAdminProducts()])
    tally.value = tl
    products.value = p
  } catch (e) {
    deleteError.value =
      e instanceof ApiError && e.status === 403
        ? t('shopAdmin.deleteWrongPassword')
        : apiErrorMessage(e, t('shopAdmin.deleteFailed'))
    deletePassword.value = ''
    passwordBox.value?.focus()
  } finally {
    busy.value = null
  }
}

async function copyTally(x: PreorderTally): Promise<void> {
  const lines = Object.entries(x.by_size).map(([s, n]) => `${s || '-'}: ${n}`)
  const text = `${x.name}\n${lines.join('\n')}\n${t('shopAdmin.tallyTotal')}: ${x.total}`
  try {
    await navigator.clipboard.writeText(text)
    copiedId.value = x.product_id
    setTimeout(() => (copiedId.value = null), 2000)
  } catch {
    // clipboard refused: nothing to undo
  }
}

// ---------------------------------------------------------------- products
const formOpen = ref(false)
const editing = ref<Product | null>(null)
const form = reactive({
  name: '',
  description: '',
  price: '' as number | '',
  sale_type: 'stock' as SaleType,
  hasSizes: true,
  sizes: [] as string[],
  stock: {} as Record<string, number | ''>,
  // Blank = the product's own price.
  sizePrices: {} as Record<string, number | ''>,
  closes: '',
  delivers: '',
  active: true,
})
const newPhotos = ref<{ file: File; url: string }[]>([])
const formError = ref<string | null>(null)
const tried = ref(false)
const saving = ref(false)

function openForm(p: Product | null): void {
  editing.value = p
  form.name = p?.name ?? ''
  form.description = p?.description ?? ''
  form.price = p?.price ?? ''
  form.sale_type = p?.sale_type ?? 'stock'
  form.hasSizes = p ? p.sizes.length > 0 : true
  form.sizes = p ? [...p.sizes] : ['S', 'M', 'L', 'XL']
  form.stock = p ? { ...p.stock } : {}
  form.sizePrices = p ? { ...p.size_prices } : {}
  customSize.value = ''
  sizeError.value = null
  form.closes = p?.preorder_closes_on ?? ''
  form.delivers = p?.preorder_delivers_on ?? ''
  form.active = p?.is_active ?? true
  newPhotos.value.forEach((x) => URL.revokeObjectURL(x.url))
  newPhotos.value = []
  formError.value = null
  tried.value = false
  formOpen.value = true
  window.scrollTo({ top: 0 })
}

// The usual sizes keep their usual order; the club's own (4XL, เด็ก M,
// สีฟ้า) follow in the order they were added.
function ordered(sizes: string[]): string[] {
  const presets = PRESET_SIZES.filter((x) => sizes.includes(x))
  return [...presets, ...sizes.filter((x) => !PRESET_SIZES.includes(x))]
}
function toggleSize(s: string): void {
  form.sizes = form.sizes.includes(s) ? form.sizes.filter((x) => x !== s) : ordered([...form.sizes, s])
}
const customSize = ref('')
const sizeError = ref<string | null>(null)
const customSizes = computed(() => form.sizes.filter((x) => !PRESET_SIZES.includes(x)))
function addCustomSize(): void {
  const s = customSize.value.trim()
  sizeError.value = null
  if (!s) return
  if (form.sizes.some((x) => x.toUpperCase() === s.toUpperCase())) {
    sizeError.value = t('shopAdmin.sizeTaken', { size: s })
    return
  }
  if (form.sizes.length >= MAX_SIZES) {
    sizeError.value = t('shopAdmin.sizeTooMany', { n: MAX_SIZES })
    return
  }
  form.sizes = ordered([...form.sizes, s])
  customSize.value = ''
}

const stockKeys = computed(() => (form.hasSizes ? form.sizes : ['']))
const problems = computed(() => {
  const p: Record<string, string> = {}
  if (!form.name.trim()) p.name = t('shopAdmin.nameRequired')
  const price = bahtProblem(form.price, { allowZero: false })
  if (price) p.price = t(`validation.${price}`)
  if (form.hasSizes && form.sizes.length === 0) p.sizes = t('shopAdmin.sizeRequired')
  if (form.sale_type === 'preorder' && !form.closes) p.closes = t('shopAdmin.closesRequired')
  if (form.hasSizes) {
    for (const k of form.sizes) {
      const v = form.sizePrices[k] ?? ''
      if (v !== '' && bahtProblem(v, { allowZero: false })) p.sizePrices = t('shopAdmin.sizePriceBad', { size: k })
    }
  }
  if (form.sale_type === 'stock') {
    for (const k of stockKeys.value) {
      // A blank box is "none yet": typing 0 into every size not in hand
      // is busywork, and the shop shows that size as sold out either way.
      const v = form.stock[k] ?? ''
      if (v !== '' && (!Number.isInteger(Number(v)) || Number(v) < 0)) {
        p.stock = t('validation.notNumber')
      }
    }
  }
  return p
})
const photoCount = computed(() => (editing.value?.image_urls.length ?? 0) + newPhotos.value.length)

async function onPhoto(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  for (const f of files.slice(0, MAX_PHOTOS - photoCount.value)) {
    const file = await compressImage(f)
    newPhotos.value.push({ file, url: URL.createObjectURL(file) })
  }
}

async function removeSaved(url: string): Promise<void> {
  if (!editing.value) return
  try {
    editing.value = await adminApi.removeProductImage(editing.value.id, url)
    products.value = products.value.map((p) => (p.id === editing.value!.id ? editing.value! : p))
  } catch (e) {
    formError.value = apiErrorMessage(e, t('shopAdmin.saveFailed'))
  }
}

async function save(): Promise<void> {
  tried.value = true
  if (Object.keys(problems.value).length) return
  saving.value = true
  formError.value = null
  const sizes = form.hasSizes ? form.sizes : []
  const fields = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    price: Number(form.price),
    sale_type: form.sale_type,
    sizes,
    // Only sizes that cost something other than the product's price.
    size_prices: Object.fromEntries(
      sizes
        .filter((k) => (form.sizePrices[k] ?? '') !== '' && Number(form.sizePrices[k]) !== Number(form.price))
        .map((k) => [k, Number(form.sizePrices[k])]),
    ),
    is_active: form.active,
    preorder_closes_on: form.sale_type === 'preorder' ? form.closes : null,
    preorder_delivers_on: form.sale_type === 'preorder' ? form.delivers || null : null,
    ...(form.sale_type === 'stock'
      ? { stock: Object.fromEntries(stockKeys.value.map((k) => [k, Number(form.stock[k] ?? 0)])) }
      : {}),
  }
  try {
    let saved = editing.value
      ? await adminApi.updateProduct(editing.value.id, fields)
      : await adminApi.createProduct(fields)
    for (const photo of newPhotos.value) saved = await adminApi.addProductImage(saved.id, photo.file)
    const exists = products.value.some((p) => p.id === saved.id)
    products.value = exists ? products.value.map((p) => (p.id === saved.id ? saved : p)) : [saved, ...products.value]
    formOpen.value = false
  } catch (e) {
    formError.value = apiErrorMessage(e, t('shopAdmin.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function remove(): Promise<void> {
  const p = editing.value
  if (!p) return
  const ok = await confirm({ title: t('shopAdmin.deleteTitle'), message: t('shopAdmin.deleteConfirm', { name: p.name }), danger: true })
  if (!ok) return
  try {
    await adminApi.deleteProduct(p.id)
    products.value = products.value.filter((x) => x.id !== p.id)
    formOpen.value = false
  } catch (e) {
    formError.value = apiErrorMessage(e, t('shopAdmin.saveFailed'))
  }
}

const stockTotal = (p: Product): number => Object.values(p.stock).reduce((a, b) => a + b, 0)
function priceText(p: Product): string {
  const [lo, hi] = priceRange(p)
  return lo === hi ? money(lo) : `${money(lo)} – ${money(hi)}`
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-2xl px-4 py-6">
    <div class="flex items-center justify-between gap-3">
      <h1 class="font-display text-2xl font-bold">{{ t('shopAdmin.title') }}</h1>
      <div v-if="!formOpen" role="tablist" class="flex gap-1.5">
        <button
          v-for="x in (['orders', 'products'] as const)"
          :key="x"
          type="button"
          role="tab"
          :aria-selected="tab === x"
          class="tap rounded-full px-4 text-sm"
          :class="tab === x ? 'bg-brand-pink font-medium text-brand-black' : 'border border-white/20 text-white/80'"
          @click="tab = x"
        >
          {{ x === 'orders' ? t('shopAdmin.tabOrders') : t('shopAdmin.tabProducts') }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <!-- ================================================================ orders -->
    <template v-else-if="tab === 'orders' && !formOpen">
      <section
        v-for="x in openTally"
        :key="x.product_id"
        class="mt-4 rounded-2xl border border-[#ffe14d]/35 bg-[#ffe14d]/7 p-3"
      >
        <div class="flex items-baseline justify-between gap-2">
          <h2 class="text-sm font-medium">{{ t('shopAdmin.tally', { name: x.name }) }}</h2>
          <span v-if="x.preorder_closes_on" class="text-xs text-white/65">{{ t('shopAdmin.tallyCloses', { date: formatDayMonth(x.preorder_closes_on, lang) }) }}</span>
        </div>
        <dl class="mt-2 grid gap-1 text-center font-display" :style="{ gridTemplateColumns: `repeat(${Object.keys(x.by_size).length + 1}, minmax(0, 1fr))` }">
          <div v-for="(n, s) in x.by_size" :key="s">
            <dt class="text-[11px] text-white/60">{{ s || '—' }}</dt>
            <dd class="text-lg font-bold">{{ n }}</dd>
          </div>
          <div>
            <dt class="text-[11px] text-white/60">{{ t('shopAdmin.tallyTotal') }}</dt>
            <dd class="text-lg font-bold text-[#ffe14d]">{{ x.total }}</dd>
          </div>
        </dl>
        <button type="button" class="tap mt-2 w-full rounded-full border border-[#ffe14d]/50 text-sm text-[#ffe14d]" @click="copyTally(x)">
          {{ copiedId === x.product_id ? t('shopAdmin.copied') : t('shopAdmin.copyTally') }}
        </button>
      </section>

      <div role="tablist" :aria-label="t('shopAdmin.statusTabs')" class="mt-4 grid grid-cols-2 gap-1 rounded-2xl bg-white/6 p-1 sm:grid-cols-4">
        <button
          v-for="g in groups"
          :key="g.id"
          type="button"
          role="tab"
          :aria-selected="group === g.id"
          class="min-h-11 rounded-xl text-[13px]"
          :class="group === g.id ? 'bg-white font-medium text-brand-black' : 'text-white/70'"
          @click="group = g.id"
        >
          {{ g.label }}
        </button>
      </div>

      <p v-if="actionError" class="mt-3 text-sm text-status-error" role="alert">{{ actionError }}</p>
      <p v-if="deletedNote" class="mt-3 rounded-xl border border-[#7ff0b4]/45 bg-[#7ff0b4]/10 px-3 py-2 text-sm text-[#7ff0b4]" role="status">✓ {{ deletedNote }}</p>
      <p v-if="shownOrders.length === 0" class="mt-6 text-center text-sm text-white/55">{{ t('shopAdmin.noOrders') }}</p>
      <ul class="mt-3 space-y-2">
        <li v-for="o in shownOrders" :key="o.id" class="hud-panel flex flex-col gap-2.5 border border-brand-pink/20 bg-brand-surface p-3">
          <div class="flex items-start gap-2.5">
            <a :href="o.slip_url" target="_blank" rel="noopener noreferrer" :aria-label="t('shopAdmin.viewSlip', { name: o.player_nickname })" class="shrink-0">
              <img :src="o.slip_url" alt="" loading="lazy" class="h-16 w-12 rounded-md border border-white/15 object-cover" />
            </a>
            <div class="min-w-0 flex-1">
              <div class="flex justify-between gap-2">
                <span class="font-medium">
                  {{ o.player_nickname }}
                  <span v-if="o.guest" class="ml-1 rounded-full bg-[#ffe14d]/16 px-2 py-0.5 text-[11px] font-normal text-[#ffe14d]">{{ t('shopAdmin.guestBadge') }}</span>
                  <span v-else class="text-xs font-normal text-white/55">{{ o.player_code }}</span>
                </span>
                <span class="font-display font-bold text-brand-pink-light">{{ money(o.total) }}</span>
              </div>
              <ul class="text-sm text-white/80">
                <li v-for="(item, i) in o.items" :key="i" class="flex justify-between gap-2">
                  <span class="min-w-0">{{ item.product_name }}<template v-if="item.size"> · <b class="font-display">{{ item.size }}</b></template> × {{ item.qty }}</span>
                  <span class="shrink-0 text-white/55">{{ money(item.line_total) }}</span>
                </li>
              </ul>
              <a v-if="o.guest && o.guest_phone" :href="`tel:${o.guest_phone}`" class="inline-flex min-h-8 items-center gap-1 text-sm text-[#7fb6ff]" :aria-label="t('shopAdmin.callGuest', { name: o.player_nickname })">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" /></svg>
                {{ formatPhone(o.guest_phone) }}
              </a>
              <p class="text-xs text-white/50">{{ orderNo(o.order_no) }} · {{ formatDateTime(o.created_at, lang) }}</p>
              <p v-if="o.note" class="mt-1 text-xs text-status-error">{{ o.note }}</p>
            </div>
          </div>

          <p v-if="lastFix && lastFix.id === o.id" role="status" class="rounded-xl border border-[#ffe14d]/40 bg-[#ffe14d]/8 px-3 py-2 text-sm text-[#ffe14d]">
            {{ t('shopAdmin.fixDone', { before: money(lastFix.before), after: money(lastFix.after) }) }} · {{ diffText(lastFix.before, lastFix.after) }}
          </p>

          <!-- fixing the lines: size buttons and how many, per line -->
          <div v-if="fixing === o.id" class="flex flex-col gap-3 rounded-xl border border-white/15 bg-white/4 p-3">
            <div v-for="item in o.items" :key="item.id ?? item.product_name + item.size" class="flex flex-col gap-2">
              <p class="text-sm font-medium">{{ item.product_name }}</p>
              <p v-if="!canFix(item)" class="text-xs text-white/55">{{ t('shopAdmin.fixGone') }}</p>
              <template v-else-if="item.id && drafts[item.id]">
                <div v-if="productOf(item)!.sizes.length" class="flex flex-wrap gap-1.5" role="radiogroup" :aria-label="t('shop.size')">
                  <button
                    v-for="s in productOf(item)!.sizes"
                    :key="s"
                    type="button"
                    role="radio"
                    :aria-checked="drafts[item.id].size === s"
                    :disabled="roomFor(item, s) < drafts[item.id].qty"
                    class="min-h-11 min-w-12 rounded-xl border px-2.5 font-display text-sm font-bold disabled:opacity-35"
                    :class="drafts[item.id].size === s ? 'border-white bg-white text-brand-black' : 'border-white/20 text-white/80'"
                    @click="drafts[item.id].size = s"
                  >
                    {{ s }}
                  </button>
                </div>
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center gap-1.5">
                    <button type="button" class="tap w-11 rounded-lg border border-white/20" :aria-label="t('shop.less')" :disabled="drafts[item.id].qty <= 1" @click="drafts[item.id].qty--">−</button>
                    <span class="min-w-6 text-center font-display font-bold" aria-live="polite">{{ drafts[item.id].qty }}</span>
                    <button type="button" class="tap w-11 rounded-lg border border-white/20" :aria-label="t('shop.more')" :disabled="drafts[item.id].qty >= Math.min(10, roomFor(item, drafts[item.id].size))" @click="drafts[item.id].qty++">+</button>
                  </div>
                  <span class="text-sm" :class="changed(item) ? 'font-medium text-[#ffe14d]' : 'text-white/60'">{{ money(draftLine(item)) }}</span>
                </div>
              </template>
            </div>
            <p class="text-sm">
              {{ t('shopAdmin.fixTotal', { before: money(o.total), after: money(draftTotal(o)) }) }}
              <b class="text-[#ffe14d]">· {{ diffText(o.total, draftTotal(o)) }}</b>
            </p>
            <p v-if="fixError" class="text-sm text-status-error" role="alert">{{ fixError }}</p>
            <div class="flex gap-2">
              <button type="button" class="tap flex-1 rounded-full bg-brand-pink text-sm font-semibold text-brand-black disabled:opacity-50" :disabled="busy === o.id || !o.items.some(changed)" @click="saveFix(o)">
                {{ busy === o.id ? t('common.saving') : t('shopAdmin.fixSave') }}
              </button>
              <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="fixing = null">{{ t('common.cancel') }}</button>
            </div>
          </div>

          <template v-else-if="o.status === 'pending'">
            <form v-if="rejecting === o.id" class="flex flex-col gap-2" @submit.prevent="move(o, 'rejected', reason)">
              <input v-model="reason" maxlength="300" :aria-label="t('shopAdmin.rejectReason')" :placeholder="t('shopAdmin.rejectReason')" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-sm" />
              <div class="flex gap-2">
                <button type="submit" :disabled="busy === o.id" class="tap flex-1 rounded-full bg-status-error/20 text-sm font-semibold text-status-error">{{ t('shopAdmin.rejectSend') }}</button>
                <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="rejecting = null">{{ t('common.cancel') }}</button>
              </div>
            </form>
            <div v-else class="flex gap-2">
              <button type="button" :disabled="busy === o.id" class="tap flex-1 rounded-full bg-brand-pink text-sm font-semibold text-brand-black" @click="move(o, 'confirmed')">{{ t('shopAdmin.confirm') }}</button>
              <button type="button" class="tap rounded-full border border-white/25 px-4 text-sm" @click="startFix(o)">{{ t('shopAdmin.fix') }}</button>
              <button type="button" class="tap rounded-full border border-status-error/50 px-4 text-sm text-status-error" @click="rejecting = o.id; reason = ''">{{ t('shopAdmin.reject') }}</button>
            </div>
          </template>
          <div v-else-if="o.status === 'confirmed'" class="flex gap-2">
            <button type="button" :disabled="busy === o.id" class="tap flex-1 rounded-full border border-[#7ff0b4]/50 bg-[#7ff0b4]/8 text-sm text-[#7ff0b4]" @click="move(o, 'delivered')">{{ t('shopAdmin.handed') }}</button>
            <button type="button" class="tap rounded-full border border-white/25 px-4 text-sm" @click="startFix(o)">{{ t('shopAdmin.fix') }}</button>
            <button type="button" :disabled="busy === o.id" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'pending')">{{ t('shopAdmin.undo') }}</button>
          </div>
          <button v-else-if="o.status === 'delivered'" type="button" :disabled="busy === o.id" class="tap self-start rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'confirmed')">{{ t('shopAdmin.undo') }}</button>
          <button v-else type="button" :disabled="busy === o.id" class="tap self-start rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'pending')">{{ t('shopAdmin.reopen') }}</button>
          <button
            v-if="fixing !== o.id"
            type="button"
            class="tap -mt-1 inline-flex items-center gap-1.5 self-end rounded-full px-3 text-xs text-white/45 hover:text-status-error"
            :aria-label="t('shopAdmin.deleteOrder', { no: orderNo(o.order_no) })"
            @click="askDelete(o)"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" /></svg>
            {{ t('shopAdmin.deleteShort') }}
          </button>
        </li>
      </ul>
    </template>

    <!-- ============================================================== products -->
    <template v-else-if="tab === 'products' && !formOpen">
      <p v-if="products.length === 0" class="mt-6 text-sm text-white/55">{{ t('shopAdmin.noProducts') }}</p>
      <ul class="mt-4 space-y-2">
        <li v-for="p in products" :key="p.id">
          <button type="button" class="hud-panel flex w-full items-center gap-3 border border-brand-pink/20 bg-brand-surface p-2 text-left" :class="{ 'opacity-60': !p.is_active }" @click="openForm(p)">
            <img v-if="p.image_urls[0]" :src="p.image_urls[0]" alt="" class="h-14 w-14 shrink-0 rounded-xl bg-[#f3eaf1] object-contain" />
            <span v-else class="h-14 w-14 shrink-0 rounded-xl bg-white/8" />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-medium">{{ p.name }}</span>
              <span class="block text-xs text-white/60">
                {{ priceText(p) }} ·
                {{ !p.is_active ? t('shopAdmin.hidden') : p.sale_type === 'preorder' ? t('shopAdmin.preorderBadge', { n: p.ordered }) : t('shopAdmin.stockBadge', { n: stockTotal(p) }) }}
              </span>
            </span>
            <span aria-hidden="true" class="pr-2 text-white/50">›</span>
          </button>
        </li>
      </ul>
      <button type="button" class="tap mt-6 w-full rounded-full bg-brand-pink px-4 font-semibold text-brand-black" @click="openForm(null)">+ {{ t('shopAdmin.addProduct') }}</button>
    </template>

    <!-- ================================================================== form -->
    <form v-else-if="formOpen" class="mt-5 flex flex-col gap-5" novalidate @submit.prevent="save">
      <h2 class="text-lg font-semibold">{{ editing ? t('shopAdmin.editProduct', { name: editing.name }) : t('shopAdmin.addProduct') }}</h2>

      <div>
        <p class="text-sm text-white/75">{{ t('shopAdmin.photos') }}</p>
        <div class="mt-2 flex flex-wrap gap-2">
          <div v-for="(url, i) in editing?.image_urls ?? []" :key="url" class="relative h-20 w-20">
            <img :src="url" alt="" class="h-full w-full rounded-xl bg-[#f3eaf1] object-contain" :class="{ 'ring-2 ring-brand-pink': i === 0 }" />
            <span v-if="i === 0" class="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-[10px]">{{ t('shopAdmin.cover') }}</span>
            <button type="button" class="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/80 text-white" :aria-label="t('shopAdmin.removePhoto')" @click="removeSaved(url)">×</button>
          </div>
          <div v-for="(x, i) in newPhotos" :key="x.url" class="relative h-20 w-20">
            <img :src="x.url" alt="" class="h-full w-full rounded-xl bg-[#f3eaf1] object-contain opacity-80" />
            <button type="button" class="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/80 text-white" :aria-label="t('shopAdmin.removePhoto')" @click="newPhotos.splice(i, 1)">×</button>
          </div>
          <label v-if="photoCount < MAX_PHOTOS" class="flex h-20 w-20 cursor-pointer items-center justify-center rounded-xl border border-dashed border-white/35 text-2xl text-white/70" :aria-label="t('shopAdmin.addPhoto')">
            +
            <input type="file" accept="image/*" multiple class="sr-only" @change="onPhoto" />
          </label>
        </div>
        <p v-if="newPhotos.length" class="mt-1 text-xs text-white/50">{{ t('shopAdmin.photosAfterSave') }}</p>
      </div>

      <label class="flex flex-col gap-1 text-sm text-white/75">
        {{ t('shopAdmin.name') }}
        <input v-model="form.name" :maxlength="MAX_NAME" :aria-invalid="tried && !!problems.name" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white" />
        <span v-if="tried && problems.name" class="text-xs text-status-error">{{ problems.name }}</span>
      </label>
      <label class="flex flex-col gap-1 text-sm text-white/75">
        {{ form.hasSizes ? t('shopAdmin.priceBase') : t('shopAdmin.price') }}
        <input v-model.number="form.price" type="number" inputmode="decimal" min="1" :aria-invalid="tried && !!problems.price" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white" />
        <span v-if="tried && problems.price" class="text-xs text-status-error">{{ problems.price }}</span>
      </label>
      <label class="flex flex-col gap-1 text-sm text-white/75">
        {{ t('shopAdmin.description') }}
        <textarea v-model="form.description" maxlength="1000" rows="3" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-white" />
      </label>

      <div>
        <p class="text-sm text-white/75">{{ t('shopAdmin.saleType') }}</p>
        <div role="radiogroup" :aria-label="t('shopAdmin.saleType')" class="mt-1.5 flex gap-1 rounded-xl bg-white/6 p-1">
          <button v-for="x in (['stock', 'preorder'] as const)" :key="x" type="button" role="radio" :aria-checked="form.sale_type === x" class="min-h-11 flex-1 rounded-lg text-sm" :class="form.sale_type === x ? 'bg-white font-medium text-brand-black' : 'text-white/70'" @click="form.sale_type = x">
            {{ x === 'stock' ? t('shopAdmin.saleStock') : t('shopAdmin.salePreorder') }}
          </button>
        </div>
        <p class="mt-1.5 text-xs text-white/55">{{ form.sale_type === 'stock' ? t('shopAdmin.stockHint') : t('shopAdmin.preorderHint') }}</p>
      </div>

      <div v-if="form.sale_type === 'preorder'" class="grid grid-cols-2 gap-3">
        <label class="flex flex-col gap-1 text-sm text-white/75">
          {{ t('shopAdmin.closesOn') }}
          <input v-model="form.closes" type="date" :min="editing ? undefined : localToday()" :aria-invalid="tried && !!problems.closes" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white" />
          <span v-if="tried && problems.closes" class="text-xs text-status-error">{{ problems.closes }}</span>
        </label>
        <label class="flex flex-col gap-1 text-sm text-white/75">
          {{ t('shopAdmin.deliversOn') }}
          <input v-model="form.delivers" type="date" :min="form.closes || undefined" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white" />
        </label>
      </div>

      <label class="flex items-center justify-between text-sm">
        {{ t('shopAdmin.hasSizes') }}
        <input v-model="form.hasSizes" type="checkbox" role="switch" class="h-6 w-11 accent-brand-pink" />
      </label>
      <div v-if="form.hasSizes">
        <p class="text-sm text-white/75">{{ t('shopAdmin.sizesOpen') }}</p>
        <div class="mt-1.5 flex flex-wrap gap-2">
          <button v-for="s in PRESET_SIZES" :key="s" type="button" class="min-h-11 min-w-12 rounded-xl border px-3 font-display font-bold" :class="form.sizes.includes(s) ? 'border-white bg-white text-brand-black' : 'border-white/20 text-white/75'" :aria-pressed="form.sizes.includes(s)" @click="toggleSize(s)">{{ s }}</button>
          <span v-for="s in customSizes" :key="s" class="flex min-h-11 items-center gap-1 rounded-xl border border-white bg-white pl-3 font-display font-bold text-brand-black">
            {{ s }}
            <button type="button" class="flex h-11 w-9 items-center justify-center text-lg" :aria-label="t('shopAdmin.removeSize', { size: s })" @click="toggleSize(s)">×</button>
          </span>
        </div>
        <div class="mt-2 flex gap-2">
          <input
            v-model="customSize"
            :maxlength="MAX_SIZE_LEN"
            :aria-label="t('shopAdmin.customSize')"
            :placeholder="t('shopAdmin.customSizeHint')"
            class="min-h-11 min-w-0 flex-1 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white"
            @keydown.enter.prevent="addCustomSize"
          />
          <button type="button" class="tap rounded-full border border-white/30 px-4 text-sm" @click="addCustomSize">+ {{ t('shopAdmin.addSize') }}</button>
        </div>
        <span v-if="sizeError" class="text-xs text-status-error">{{ sizeError }}</span>
        <span v-if="tried && problems.sizes" class="text-xs text-status-error">{{ problems.sizes }}</span>
      </div>

      <!-- one row per size: what it costs (blank = the price above) and,
           for stock, how many are on the shelf -->
      <div v-if="form.hasSizes && form.sizes.length">
        <p class="text-sm text-white/75">{{ form.sale_type === 'stock' ? t('shopAdmin.perSize') : t('shopAdmin.perSizePrice') }}</p>
        <p class="text-xs text-white/50">{{ form.sale_type === 'stock' ? t('shopAdmin.perSizeHint') : t('shopAdmin.perSizeHintPrice') }}</p>
        <div class="mt-1.5 flex flex-col gap-1.5">
          <div v-for="k in form.sizes" :key="k" class="flex min-h-12 items-center gap-2 rounded-xl border border-white/15 bg-white/4 px-3">
            <span class="w-16 shrink-0 font-display font-bold">{{ k }}</span>
            <label class="flex flex-1 items-center gap-1.5 text-xs text-white/60">
              ฿
              <input
                v-model.number="form.sizePrices[k]"
                type="number"
                inputmode="decimal"
                min="1"
                :placeholder="form.price === '' ? '—' : String(form.price)"
                :aria-label="t('shopAdmin.sizePrice', { size: k })"
                class="h-9 w-full min-w-0 rounded-lg border border-brand-pink/30 bg-brand-black px-2 text-center font-display text-base font-bold text-white"
              />
            </label>
            <label v-if="form.sale_type === 'stock'" class="flex items-center gap-1.5 text-xs text-white/60">
              {{ t('shopAdmin.stockShort') }}
              <input v-model.number="form.stock[k]" type="number" inputmode="numeric" min="0" :aria-label="`${t('shopAdmin.stockOne')} ${k}`" placeholder="0" class="h-9 w-16 rounded-lg border border-brand-pink/30 bg-brand-black text-center font-display text-base font-bold text-white" />
            </label>
          </div>
        </div>
        <span v-if="tried && problems.sizePrices" class="text-xs text-status-error">{{ problems.sizePrices }}</span>
        <span v-if="tried && problems.stock" class="text-xs text-status-error">{{ problems.stock }}</span>
      </div>

      <div v-if="!form.hasSizes && form.sale_type === 'stock'">
        <label class="flex min-h-12 items-center justify-between gap-2 rounded-xl border border-white/15 bg-white/4 pr-1.5 pl-3 text-sm">
          {{ t('shopAdmin.stockOne') }}
          <input v-model.number="form.stock['']" type="number" inputmode="numeric" min="0" :aria-label="t('shopAdmin.stockOne')" placeholder="0" class="h-9 w-20 rounded-lg border border-brand-pink/30 bg-brand-black text-center font-display font-bold" />
        </label>
        <span v-if="tried && problems.stock" class="text-xs text-status-error">{{ problems.stock }}</span>
      </div>

      <label class="flex items-center justify-between text-sm">
        {{ t('shopAdmin.active') }}
        <input v-model="form.active" type="checkbox" role="switch" class="h-6 w-11 accent-brand-pink" />
      </label>

      <p v-if="formError" class="text-sm text-status-error" role="alert">{{ formError }}</p>
      <div class="flex gap-2">
        <button type="submit" :disabled="saving" class="tap flex-1 rounded-full bg-brand-pink px-5 font-semibold text-brand-black disabled:opacity-50">
          {{ saving ? t('common.saving') : editing ? t('shopAdmin.save') : t('shopAdmin.saveNew') }}
        </button>
        <button type="button" class="tap rounded-full border border-white/20 px-5 text-sm text-white/60" @click="formOpen = false">{{ t('common.cancel') }}</button>
      </div>
      <button v-if="editing" type="button" class="tap w-full rounded-full bg-status-error/15 text-sm font-semibold text-status-error" @click="remove">{{ t('shopAdmin.delete') }}</button>
    </form>

    <!-- deleting: what goes, what comes back, and the admin's own password -->
    <Teleport to="body">
      <div v-if="deleting" class="fixed inset-0 z-50 flex items-end justify-center bg-black/60 sm:items-center" @click.self="deleting = null">
        <form
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-title"
          class="flex w-full max-w-md flex-col gap-3 rounded-t-3xl border-t border-status-error/50 bg-[#1a0d14] p-4 pb-[calc(1.25rem+env(safe-area-inset-bottom,0px))] sm:rounded-3xl sm:border"
          @submit.prevent="confirmDelete"
          @keydown.esc="deleting = null"
        >
          <h2 id="delete-title" class="font-display text-xl font-bold">{{ t('shopAdmin.deleteTitleOrder', { no: orderNo(deleting.order_no) }) }}</h2>
          <div class="rounded-xl border border-white/12 bg-white/5 px-3 py-2.5 text-sm">
            <div class="flex justify-between gap-3">
              <span>{{ deleting.player_nickname }}<template v-if="deleting.guest"> ({{ t('shopAdmin.guestBadge') }})</template></span>
              <b>{{ money(deleting.total) }}</b>
            </div>
            <p v-for="(item, i) in deleting.items" :key="i" class="text-white/70">{{ item.product_name }}<template v-if="item.size"> · {{ item.size }}</template> × {{ item.qty }}</p>
            <p class="text-xs text-white/50">{{ t(`shop.status.${deleting.status}`) }} · {{ formatDateTime(deleting.created_at, lang) }}</p>
          </div>
          <ul class="flex flex-col gap-1.5 text-sm text-white/85">
            <li v-if="stockBack(deleting).length">↩︎ {{ t('shopAdmin.deleteStockBack', { items: stockBack(deleting).join(', ') }) }}</li>
            <li>🗑 {{ t('shopAdmin.deleteSlip') }}</li>
            <li>📝 {{ t('shopAdmin.deleteLogged') }}</li>
            <li class="text-[#ff9b9b]">⚠︎ {{ t('shopAdmin.deleteNoUndo') }}</li>
          </ul>
          <label class="flex flex-col gap-1.5 text-sm">
            {{ t('shopAdmin.deletePassword') }}
            <input
              ref="passwordBox"
              v-model="deletePassword"
              type="password"
              autocomplete="current-password"
              :aria-invalid="!!deleteError"
              class="min-h-12 rounded-2xl border bg-white/7 px-4 text-base text-white"
              :class="deleteError ? 'border-status-error' : 'border-white/22'"
            />
            <span v-if="deleteError" role="alert" class="text-xs text-status-error">{{ deleteError }}</span>
          </label>
          <div class="flex gap-2">
            <button type="submit" :disabled="!deletePassword || busy === deleting.id" class="tap flex-1 rounded-full bg-[#d94848] font-semibold text-white disabled:bg-white/12 disabled:text-white/60">
              {{ busy === deleting.id ? t('shopAdmin.deleting') : t('shopAdmin.deleteForGood') }}
            </button>
            <button type="button" class="tap rounded-full border border-white/25 px-5 text-sm text-white/80" @click="deleting = null">{{ t('common.cancel') }}</button>
          </div>
        </form>
      </div>
    </Teleport>
  </main>
</template>
