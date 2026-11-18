import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { CartLine } from '@/types'

// Members have no accounts, so the cart lives on the phone: a few shirts
// picked across a week of looking, kept until the order goes in. Only what
// was chosen is kept — never a price: the cart page asks the server what
// each line costs now (quoteCart), so an old price can't be paid.
const STORAGE_KEY = 'niddeaw_shop_cart'
export const MAX_LINE_QTY = 10
export const MAX_LINES = 20
export const MAX_PRINT_NAME = 20

/** A printed name as the cart keeps it: trimmed, and blank is none. */
export function printName(name: string | null | undefined): string | null {
  const trimmed = (name ?? '').trim().slice(0, MAX_PRINT_NAME)
  return trimmed || null
}

function read(): CartLine[] {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as unknown
    if (!Array.isArray(raw)) return []
    return raw
      .filter(
        (l): l is CartLine =>
          !!l && typeof l.product_id === 'string' && typeof l.size === 'string' && Number.isInteger(l.qty) && l.qty > 0,
      )
      .map((l) => ({ ...l, print_name: typeof l.print_name === 'string' ? printName(l.print_name) : null }))
      .slice(0, MAX_LINES)
  } catch {
    return []
  }
}

export const useCartStore = defineStore('cart', () => {
  const lines = ref<CartLine[]>(read())

  watch(
    lines,
    (now) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(now))
      } catch {
        // private mode: the cart lasts until the tab closes
      }
    },
    { deep: true },
  )

  const count = computed(() => lines.value.reduce((n, l) => n + l.qty, 0))

  // A line is a product, a size and the name printed on it (if any): the
  // same shirt with two names is two lines.
  function find(productId: string, size: string, name: string | null = null): CartLine | undefined {
    const n = printName(name)
    return lines.value.find((l) => l.product_id === productId && l.size === size && (l.print_name ?? null) === n)
  }

  /** Add `qty` of one size; the same size (and name) again tops up its
   *  line. Returns how many were actually added (a line holds ten at most). */
  function add(productId: string, size: string, qty: number, name: string | null = null): number {
    const line = find(productId, size, name)
    if (line) {
      const room = MAX_LINE_QTY - line.qty
      const added = Math.max(0, Math.min(room, qty))
      line.qty += added
      return added
    }
    if (lines.value.length >= MAX_LINES) return 0
    const added = Math.min(MAX_LINE_QTY, qty)
    lines.value.push({ product_id: productId, size, qty: added, print_name: printName(name) })
    return added
  }

  function setQty(productId: string, size: string, qty: number, name: string | null = null): void {
    const line = find(productId, size, name)
    if (line) line.qty = Math.max(1, Math.min(MAX_LINE_QTY, qty))
  }

  function remove(productId: string, size: string, name: string | null = null): void {
    const gone = find(productId, size, name)
    lines.value = lines.value.filter((l) => l !== gone)
  }

  function clear(): void {
    lines.value = []
  }

  return { lines, count, find, add, setQty, remove, clear }
})
