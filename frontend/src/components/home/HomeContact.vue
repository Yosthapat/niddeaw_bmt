<script setup lang="ts">
// How to reach whoever runs the club, and the quiet door to the admin
// pages — last on the phone, and beside the vibes on a desktop.
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
// Moved off the header: see the comment in AppHeader.vue.
const authStore = useAuthStore()

// Own-drawn line-icon glyphs (not the real brand marks) so the contact
// badges match the site's hand-drawn icon language instead of pasting in
// LINE's green speech-bubble or TikTok's note logo.
const socialLinks = [
  {
    label: 'LINE OA',
    href: 'https://line.me/R/ti/p/@369iojcn',
    path: 'M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-4 4v-4H6a2 2 0 0 1-2-2Z',
    // LINE's own green, darkened until white text on it is readable.
    cls: 'bg-[#037f36] border-[#06c755]/60 shadow-[0_8px_20px_-8px_rgb(6_199_85/0.6)]',
  },
  {
    label: 'TikTok',
    href: 'https://www.tiktok.com/@nidde4w',
    path: 'M14 4v10.5a3.5 3.5 0 1 1-3.5-3.5 M14 4c.5 2.5 2.5 4 5 4',
    cls: 'bg-white/8 border-white/25',
  },
]
</script>

<template>
  <section v-reveal class="world-card overflow-hidden p-5 sm:p-6" aria-labelledby="home-contact">
    <!-- the cat peeking in from the corner, so the last card is still
         the hero's world and not a form -->
    <img src="/hero/cat-color.webp" alt="" width="140" height="140" loading="lazy" class="pointer-events-none absolute -right-6 -bottom-8 h-36 w-36 opacity-25 sm:h-44 sm:w-44" />
    <p class="world-eyebrow">CONTACT</p>
    <h2 id="home-contact" class="world-title text-xl sm:text-2xl">{{ t('home.contactTitle') }}</h2>
    <p class="mt-2 max-w-[36ch] text-sm text-white/75">{{ t('home.contactBody') }}</p>
    <div class="relative mt-4 flex flex-wrap gap-2.5">
      <a
        v-for="social in socialLinks"
        :key="social.label"
        :href="social.href"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex min-h-12 items-center gap-2 rounded-full border px-5 font-display text-sm font-bold text-white transition-transform hover:-translate-y-0.5"
        :class="social.cls"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
          <path :d="social.path" />
        </svg>
        {{ social.label }}
      </a>
    </div>

    <!-- Kept inside the contact card but set apart by the rule: it is
         the same "who runs this" corner of the page, while staying
         visually unlike the LINE/TikTok buttons above so nobody taps
         it expecting to reach a human. -->
    <div class="relative mt-5 border-t border-white/10 pt-3">
      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="inline-flex min-h-11 items-center gap-2 text-xs font-semibold tracking-wide text-white/55 uppercase transition-colors hover:text-brand-pink-light"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5" aria-hidden="true">
          <rect x="5" y="11" width="14" height="9" rx="1.5" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
        {{ authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin') }}
      </RouterLink>
    </div>
  </section>
</template>
