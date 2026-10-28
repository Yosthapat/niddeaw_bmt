<script setup lang="ts">
// The partners band: every logo a white silhouette trimmed to the mark
// (made by the backend from whatever the sponsor sent), with its real size
// so the browser reserves the right shape before the bytes arrive. Under
// the big hero from 900px wide, under the home cards on a phone.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSponsors } from '@/api/public'
import { BUNDLED_SPONSORS, logoHeight, type BandLogo } from '@/utils/sponsorBand'

const { t } = useI18n()
const sponsors = ref<BandLogo[]>(BUNDLED_SPONSORS)
onMounted(async () => {
  try {
    sponsors.value = await getSponsors()
  } catch {
    // keep the bundled five — see BUNDLED_SPONSORS
  }
})
</script>

<template>
  <!-- The partners band. Two identical halves on one track that slides
       left by exactly one half, so the loop never shows a seam. The
       second half is hidden from screen readers and the tab order: it is
       the same links again. -->
  <div v-if="sponsors.length > 0" class="bb-marquee border-y border-white/10 bg-white/[0.04] py-3 backdrop-blur-md">
    <div class="bb-track flex w-max items-center">
      <template v-for="copy in 2" :key="copy">
        <div
          class="bb-half flex shrink-0 items-center gap-10 pr-10"
          :aria-hidden="copy === 2 ? 'true' : undefined"
          :data-copy="copy"
        >
          <span class="font-display text-[11px] font-semibold tracking-[0.25em] whitespace-nowrap text-white/60 uppercase">
            {{ t('home.sponsorsTitle') }}
          </span>
          <a
            v-for="sponsor in sponsors"
            :key="sponsor.logo_url"
            :href="sponsor.href ?? undefined"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="sponsor.name"
            :tabindex="copy === 2 ? -1 : undefined"
            class="sponsor-logo shrink-0"
          >
            <img
              :src="sponsor.logo_url"
              :alt="copy === 2 ? '' : sponsor.name"
              :width="sponsor.logo_width"
              :height="sponsor.logo_height"
              loading="lazy"
              decoding="async"
              class="bb-logo w-auto object-contain"
              :style="{ '--h': logoHeight(sponsor) }"
            />
          </a>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.bb-marquee {
  --band-scale: 1;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
}
.bb-track {
  animation: bb-marquee 32s linear infinite;
}
.bb-logo {
  height: calc(var(--h) * var(--band-scale) * 1px);
}
@media (min-width: 640px) {
  .bb-marquee {
    --band-scale: 1.25;
  }
}
/* Holds still while someone is aiming at a logo, by mouse or keyboard. */
.bb-marquee:hover .bb-track,
.bb-marquee:focus-within .bb-track {
  animation-play-state: paused;
}
@keyframes bb-marquee {
  to {
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  /* No drift: one copy, wrapped and centred, so every sponsor is still on
     screen and none of them has to move to be seen. */
  .bb-track {
    animation: none;
    width: 100%;
  }
  /* shrink-0 keeps the moving copy on one line; here it has to give that
     up, or the row runs off both edges instead of wrapping. */
  .bb-half {
    flex-shrink: 1;
    width: 100%;
    padding-inline: 1rem;
    flex-wrap: wrap;
    justify-content: center;
    row-gap: 1rem;
  }
  .bb-half[data-copy='2'] {
    display: none;
  }
  .bb-marquee {
    -webkit-mask-image: none;
    mask-image: none;
  }
}
</style>
