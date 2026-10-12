/** A receipt's thumbnail lives beside it: `abc-123.png` -> `abc-123-thumb.jpg`.
 *
 * Derived rather than stored in a column of its own — the rows already hold
 * the receipt's URL, and a convention costs no migration. Receipts uploaded
 * before thumbnails existed have none, so every <img> that uses this must
 * fall back to the full image on error (see ReceiptThumb.vue). */
export function thumbUrl(publicUrl: string): string {
  const [head, query] = publicUrl.split('?')
  const derived = `${head.replace(/\.[^./]+$/, '')}-thumb.jpg`
  return query ? `${derived}?${query}` : derived
}
