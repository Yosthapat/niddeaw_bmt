/** Mirrors backend app/models/sponsor.py Sponsor. */
export interface Sponsor {
  id: string
  name: string
  href: string | null
  /** A bucket URL for an uploaded logo, or a path under /sponsors/ for the
   *  five that shipped with the site. Always a white silhouette. */
  logo_url: string
  logo_width: number
  logo_height: number
  sort_order: number
  is_visible: boolean
  created_at: string
}

export interface LogoPreview {
  data_uri: string
  width: number
  height: number
}
