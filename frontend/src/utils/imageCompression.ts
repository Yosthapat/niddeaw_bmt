// Phone photos (especially iPhone HEIC shots) routinely land at 8-20MB —
// well over the backend's avatar/receipt size limits. Resizing and
// re-encoding to JPEG here, entirely in-browser via <canvas>, shrinks
// those down to a few hundred KB and normalizes the format at the same
// time, so a HEIC/PNG/whatever original still arrives as a small .jpg.

const MAX_DIMENSION = 1600
const JPEG_QUALITY = 0.8
const SKIP_BELOW_BYTES = 500 * 1024

function withJpegExtension(filename: string): string {
  const base = filename.replace(/\.[^./\\]+$/, '')
  return `${base || 'photo'}.jpg`
}

/**
 * Resizes + re-encodes an image file to JPEG for upload. Falls back to
 * returning the original file untouched if it's not an image, is already
 * small, or the browser can't decode it (e.g. an exotic format) — the
 * backend's own extension/size checks are still the final word.
 */
export async function compressImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.size <= SKIP_BELOW_BYTES) {
    return file
  }

  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    return file
  }

  try {
    const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height))
    const width = Math.round(bitmap.width * scale)
    const height = Math.round(bitmap.height * scale)

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.drawImage(bitmap, 0, 0, width, height)

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY),
    )
    if (!blob || blob.size >= file.size) return file

    return new File([blob], withJpegExtension(file.name), { type: 'image/jpeg' })
  } finally {
    bitmap.close()
  }
}
