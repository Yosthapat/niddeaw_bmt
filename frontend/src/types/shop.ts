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
  is_active?: boolean
}

export interface ShopOrder {
  id: string
  order_no: number
  product_name: string
  sale_type: SaleType
  size: string
  qty: number
  total: number
  status: OrderStatus
  note: string | null
  created_at: string
}

export interface ShopOrderAdmin extends ShopOrder {
  player_id: string
  player_nickname: string
  player_code: string
  product_id: string | null
  unit_price: number
  slip_url: string
  updated_at: string
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
