/** Mirrors backend app/models/shop.py. */
export type SaleType = 'stock' | 'preorder'
export type OrderStatus = 'pending' | 'confirmed' | 'delivered' | 'rejected'

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
  player_id: string
  player_nickname: string
  player_code: string
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
