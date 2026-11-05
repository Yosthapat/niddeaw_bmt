/** Mirrors backend app/models/shop.py. */
export type SaleType = 'stock' | 'preorder'
export type OrderStatus = 'pending' | 'confirmed' | 'delivered' | 'rejected'

export interface ProductDetail {
  url: string
  /** a short tag, "FRONT" */
  label: string
  /** the line under it */
  note: string
}

/** The words on a product's cinematic page; every part optional. */
export interface Cinema {
  title?: string
  subtitle?: string
  captions?: { label: string; text: string }[]
  facts?: string[]
  /** photo urls for the lookbook, in order; empty = all photos */
  lookbook?: string[]
  /** size chart in inches */
  chart?: { size: string; width: number | null; length: number | null }[]
}

export interface Product {
  id: string
  name: string
  description: string | null
  price: number
  sale_type: SaleType
  /** empty = one size */
  sizes: string[]
  preorder_closes_on: string | null
  preorder_delivers_on: string | null
  image_urls: string[]
  /** a short clip of it turning round; the product page opens on it */
  video_url?: string | null
  /** close-ups for the cinematic page, in order */
  detail_images?: ProductDetail[]
  cinema?: Cinema
  is_active: boolean
  sort_order: number
  created_at: string
  /** price per size where it isn't `price` (XL +20) — see priceOf() */
  size_prices: Record<string, number>
  /** per size ('' for one size); empty for a pre-order */
  stock: Record<string, number>
  ordered: number
  open: boolean
}

export interface ProductFields {
  name?: string
  description?: string | null
  price?: number
  sale_type?: SaleType
  sizes?: string[]
  preorder_closes_on?: string | null
  preorder_delivers_on?: string | null
  stock?: Record<string, number>
  size_prices?: Record<string, number>
  is_active?: boolean
  cinema?: Cinema
}

export interface ShopOrderItem {
  id?: string | null
  product_id: string | null
  product_name: string
  sale_type: SaleType
  size: string
  qty: number
  unit_price: number
  line_total: number
}

export interface ShopOrder {
  id: string
  order_no: number
  items: ShopOrderItem[]
  total: number
  status: OrderStatus
  note: string | null
  created_at: string
}

export interface ShopOrderAdmin extends ShopOrder {
  /** null for a guest's order */
  player_id: string | null
  /** the member's nickname, or the name a guest typed */
  player_nickname: string
  player_code: string
  guest: boolean
  guest_phone: string | null
  slip_url: string
  updated_at: string
}

/** One line of the cart, as kept on this phone and sent to the server. */
export interface CartLine {
  product_id: string
  size: string
  qty: number
}

/** The server's pricing of a cart, line by line: the cart shows exactly
 *  this, never its own sums. */
export interface QuoteLine extends CartLine {
  product_name: string
  image_url: string | null
  sale_type: SaleType
  unit_price: number
  line_total: number
  problem: string | null
  available: number | null
}

export interface Quote {
  lines: QuoteLine[]
  total: number
  ok: boolean
}

export interface PreorderTally {
  product_id: string
  name: string
  preorder_closes_on: string | null
  by_size: Record<string, number>
  total: number
}

/** What the shop has taken in. Money in is confirmed + delivered orders;
 *  pending ones are apart and in no total. cost is the shop-cost and shirt
 *  expenses. Mirrors backend app/models/shop.py ShopRevenue. */
export interface ShopRevenue {
  total: number
  orders: number
  pending_amount: number
  pending_orders: number
  to_ship: number
  cost: number
  profit: number
  /** newest first; dates are Bangkok days */
  daily: { date: string; amount: number; orders: number }[]
  top: { name: string; qty: number; amount: number }[]
}

/** A Thai phone number as its digits, or null when it isn't one: a leading
 *  0 and 9 or 10 digits. Mirrors backend app/models/shop.py phone_digits(). */
export function phoneDigits(raw: string): string | null {
  const digits = raw.replace(/\D/g, '')
  return /^0\d{8,9}$/.test(digits) ? digits : null
}

/** 0812345678 → 081-234-5678, for reading back and dialling. */
export function formatPhone(digits: string): string {
  return digits.length === 10 ? `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}` : `${digits.slice(0, 2)}-${digits.slice(2, 5)}-${digits.slice(5)}`
}

/** "S-0012" — how an order is said out loud and searched for. */
export function orderNo(n: number): string {
  return `S-${String(n).padStart(4, '0')}`
}

/** What one of `size` costs: its own price if it has one, else the
 *  product's. Mirrors backend app/models/shop.py unit_price(). */
export function priceOf(p: Pick<Product, 'price' | 'size_prices'>, size: string): number {
  return p.size_prices?.[size] ?? p.price
}

/** Cheapest and dearest size, for "฿250 – ฿310" before a size is picked. */
export function priceRange(p: Pick<Product, 'price' | 'size_prices' | 'sizes'>): [number, number] {
  const all = p.sizes.length ? p.sizes.map((s) => priceOf(p, s)) : [p.price]
  return [Math.min(...all), Math.max(...all)]
}
