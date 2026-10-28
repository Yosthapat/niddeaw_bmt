<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import type { OrderStatus, PreorderTally, Product, SaleType, ShopOrderAdmin } from '@/types'
import { orderNo } from '@/types'
import { formatDayMonth, formatDateTime, money } from '@/utils/format'
import { bahtProblem, localToday, MAX_NAME } from '@/utils/limits'
import { compressImage } from '@/utils/imageCompression'
import AdminNav from '@/components/layout/AdminNav.vue'

const PRESET_SIZES = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL']
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

function toggleSize(s: string): void {
  form.sizes = form.sizes.includes(s) ? form.sizes.filter((x) => x !== s) : PRESET_SIZES.filter((x) => x === s || form.sizes.includes(x))
}

const stockKeys = computed(() => (form.hasSizes ? form.sizes : ['']))
const problems = computed(() => {
  const p: Record<string, string> = {}
  if (!form.name.trim()) p.name = t('shopAdmin.nameRequired')
  const price = bahtProblem(form.price, { allowZero: false })
  if (price) p.price = t(`validation.${price}`)
  if (form.hasSizes && form.sizes.length === 0) p.sizes = t('shopAdmin.sizeRequired')
  if (form.sale_type === 'preorder' && !form.closes) p.closes = t('shopAdmin.closesRequired')
  if (form.sale_type === 'stock') {
    for (const k of stockKeys.value) {
      const v = form.stock[k]
      if (v === '' || v === undefined || !Number.isInteger(Number(v)) || Number(v) < 0) {
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
    is_active: form.active,
    preorder_closes_on: form.sale_type === 'preorder' ? form.closes : null,
    preorder_delivers_on: form.sale_type === 'preorder' ? form.delivers || null : null,
    ...(form.sale_type === 'stock'
      ? { stock: Object.fromEntries(stockKeys.value.map((k) => [k, Number(form.stock[k])])) }
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
      <p v-if="shownOrders.length === 0" class="mt-6 text-center text-sm text-white/55">{{ t('shopAdmin.noOrders') }}</p>
      <ul class="mt-3 space-y-2">
        <li v-for="o in shownOrders" :key="o.id" class="hud-panel flex flex-col gap-2.5 border border-brand-pink/20 bg-brand-surface p-3">
          <div class="flex items-start gap-2.5">
            <a :href="o.slip_url" target="_blank" rel="noopener noreferrer" :aria-label="t('shopAdmin.viewSlip', { name: o.player_nickname })" class="shrink-0">
              <img :src="o.slip_url" alt="" loading="lazy" class="h-16 w-12 rounded-md border border-white/15 object-cover" />
            </a>
            <div class="min-w-0 flex-1">
              <div class="flex justify-between gap-2">
                <span class="font-medium">{{ o.player_nickname }} <span class="text-xs font-normal text-white/55">{{ o.player_code }}</span></span>
                <span class="font-display font-bold text-brand-pink-light">{{ money(o.total) }}</span>
              </div>
              <p class="text-sm text-white/75">{{ o.product_name }}<template v-if="o.size"> · {{ o.size }}</template> × {{ o.qty }}</p>
              <p class="text-xs text-white/50">{{ orderNo(o.order_no) }} · {{ formatDateTime(o.created_at, lang) }}</p>
              <p v-if="o.note" class="mt-1 text-xs text-status-error">{{ o.note }}</p>
            </div>
          </div>

          <template v-if="o.status === 'pending'">
            <form v-if="rejecting === o.id" class="flex flex-col gap-2" @submit.prevent="move(o, 'rejected', reason)">
              <input v-model="reason" maxlength="300" :aria-label="t('shopAdmin.rejectReason')" :placeholder="t('shopAdmin.rejectReason')" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-sm" />
              <div class="flex gap-2">
                <button type="submit" :disabled="busy === o.id" class="tap flex-1 rounded-full bg-status-error/20 text-sm font-semibold text-status-error">{{ t('shopAdmin.rejectSend') }}</button>
                <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="rejecting = null">{{ t('common.cancel') }}</button>
              </div>
            </form>
            <div v-else class="flex gap-2">
              <button type="button" :disabled="busy === o.id" class="tap flex-1 rounded-full bg-brand-pink text-sm font-semibold text-brand-black" @click="move(o, 'confirmed')">{{ t('shopAdmin.confirm') }}</button>
              <button type="button" class="tap rounded-full border border-status-error/50 px-4 text-sm text-status-error" @click="rejecting = o.id; reason = ''">{{ t('shopAdmin.reject') }}</button>
            </div>
          </template>
          <div v-else-if="o.status === 'confirmed'" class="flex gap-2">
            <button type="button" :disabled="busy === o.id" class="tap flex-1 rounded-full border border-[#7ff0b4]/50 bg-[#7ff0b4]/8 text-sm text-[#7ff0b4]" @click="move(o, 'delivered')">{{ t('shopAdmin.handed') }}</button>
            <button type="button" :disabled="busy === o.id" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'pending')">{{ t('shopAdmin.undo') }}</button>
          </div>
          <button v-else-if="o.status === 'delivered'" type="button" :disabled="busy === o.id" class="tap self-start rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'confirmed')">{{ t('shopAdmin.undo') }}</button>
          <button v-else type="button" :disabled="busy === o.id" class="tap self-start rounded-full border border-white/20 px-4 text-sm text-white/60" @click="move(o, 'pending')">{{ t('shopAdmin.reopen') }}</button>
        </li>
      </ul>
    </template>

    <!-- ============================================================== products -->
    <template v-else-if="tab === 'products' && !formOpen">
      <p v-if="products.length === 0" class="mt-6 text-sm text-white/55">{{ t('shopAdmin.noProducts') }}</p>
      <ul class="mt-4 space-y-2">
        <li v-for="p in products" :key="p.id">
          <button type="button" class="hud-panel flex w-full items-center gap-3 border border-brand-pink/20 bg-brand-surface p-2 text-left" :class="{ 'opacity-60': !p.is_active }" @click="openForm(p)">
            <img v-if="p.image_urls[0]" :src="p.image_urls[0]" alt="" class="h-14 w-14 shrink-0 rounded-xl object-cover" />
            <span v-else class="h-14 w-14 shrink-0 rounded-xl bg-white/8" />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-medium">{{ p.name }}</span>
              <span class="block text-xs text-white/60">
                {{ money(p.price) }} ·
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
            <img :src="url" alt="" class="h-full w-full rounded-xl object-cover" :class="{ 'ring-2 ring-brand-pink': i === 0 }" />
            <span v-if="i === 0" class="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-[10px]">{{ t('shopAdmin.cover') }}</span>
            <button type="button" class="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/80 text-white" :aria-label="t('shopAdmin.removePhoto')" @click="removeSaved(url)">×</button>
          </div>
          <div v-for="(x, i) in newPhotos" :key="x.url" class="relative h-20 w-20">
            <img :src="x.url" alt="" class="h-full w-full rounded-xl object-cover opacity-80" />
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
        {{ t('shopAdmin.price') }}
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
        </div>
        <span v-if="tried && problems.sizes" class="text-xs text-status-error">{{ problems.sizes }}</span>
      </div>

      <div v-if="form.sale_type === 'stock' && stockKeys.length">
        <p class="text-sm text-white/75">{{ form.hasSizes ? t('shopAdmin.stockPerSize') : t('shopAdmin.stockOne') }}</p>
        <div class="mt-1.5 grid grid-cols-3 gap-2">
          <label v-for="k in stockKeys" :key="k" class="flex min-h-12 items-center justify-between gap-2 rounded-xl border border-white/15 bg-white/4 pr-1.5 pl-3">
            <span class="font-display font-bold">{{ k || '#' }}</span>
            <input v-model.number="form.stock[k]" type="number" inputmode="numeric" min="0" :aria-label="`${t('shopAdmin.stockOne')} ${k}`" class="h-9 w-16 rounded-lg border border-brand-pink/30 bg-brand-black text-center font-display font-bold" />
          </label>
        </div>
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
  </main>
</template>
