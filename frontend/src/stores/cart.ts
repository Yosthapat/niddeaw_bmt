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

function read(): CartLine[] {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as unknown
    if (!Array.isArray(raw)) return []
    return raw
      .filter(
        (l): l is CartLine =>
          !!l && typeof l.product_id === 'string' && typeof l.size === 'string' && Number.isInteger(l.qty) && l.qty > 0,
      )
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

  function find(productId: string, size: string): CartLine | undefined {
    return lines.value.find((l) => l.product_id === productId && l.size === size)
  }

  /** Add `qty` of one size; the same size again tops up its line. Returns
   *  how many were actually added (a line holds ten at most). */
  function add(productId: string, size: string, qty: number): number {
    const line = find(productId, size)
    if (line) {
      const room = MAX_LINE_QTY - line.qty
      const added = Math.max(0, Math.min(room, qty))
      line.qty += added
      return added
    }
    if (lines.value.length >= MAX_LINES) return 0
    const added = Math.min(MAX_LINE_QTY, qty)
    lines.value.push({ product_id: productId, size, qty: added })
    return added
  }

  function setQty(productId: string, size: string, qty: number): void {
    const line = find(productId, size)
    if (line) line.qty = Math.max(1, Math.min(MAX_LINE_QTY, qty))
  }

  function remove(productId: string, size: string): void {
    lines.value = lines.value.filter((l) => !(l.product_id === productId && l.size === size))
  }

  function clear(): void {
    lines.value = []
  }

  return { lines, count, find, add, setQty, remove, clear }
})
