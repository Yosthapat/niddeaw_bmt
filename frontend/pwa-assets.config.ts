import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// Generates the PWA icon set (192x192, 512x512, 512x512 maskable, favicon,
// apple-touch-icon) from the club logo. Assets are written next to the
// source image, so the source is a copy of the club logo placed at
// public/pwa-icons/source-logo.jpg — outputs land in public/pwa-icons/ too.
// Run with: npx pwa-assets-generator
export default defineConfig({
  headLinkOptions: {
    preset: '2023',
  },
  preset: minimal2023Preset,
  images: ['public/pwa-icons/source-logo.jpg'],
})
