<script setup lang="ts">
// Two doors under the tournament and the shop: topping up credit and the
// Niddeaw Pass. Both lead to the /line page, where the member is known and
// the buying happens; here they only show what is on sale.
//
// Through the LIFF link (liff.line.me/<id>/credit), not /line/credit: on a
// phone that opens the LINE app, already signed in. /line straight from
// Safari sends them to LINE's web login, which refuses anyone who has only
// ever used LINE on their phone. /line is the fallback only while the LINE
// config hasn't loaded, or when LINE login isn't switched on. From 640px the
// credit card lists its packages (each opens the LINE page with that pack
// picked) and the pass card its perks.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLineConfig } from '@/api/line'
import { getWalletOffer, type WalletOffer } from '@/api/public'

const { t } = useI18n()
const offer = ref<WalletOffer | null>(null)

const liffId = ref<string | null>(null)
// LIFF adds the path and query to its endpoint (niddeaw.fyi/line), so this
// lands on /line/credit?pack=… inside LINE.
const lineHref = (section: string, query = ''): string =>
  liffId.value ? `https://liff.line.me/${liffId.value}/${section}${query}` : `/line/${section}${query}`

onMounted(async () => {
  getLineConfig()
    .then((c) => {
      if (c.enabled && c.liff_id) liffId.value = c.liff_id
    })
    .catch(() => {
      // the /line fallback stays
    })
  try {
    offer.value = await getWalletOffer()
  } catch {
    // The doors still open; only the prices are missing.
  }
})

const num = (n: number): string => n.toLocaleString('en-US')
const baht = (n: number): string => `฿${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
// what a package earns: 1,000 credit or more a pink card, 5,000 a black one
const tier = (credits: number): 'pink' | 'black' | null => (credits >= 5000 ? 'black' : credits >= 1000 ? 'pink' : null)
const bonus = computed(() => Math.max(0, ...(offer.value?.packages ?? []).map((p) => Math.round(p.credits - p.price))))
</script>

<template>
  <div class="wallet grid grid-cols-2 gap-2.5 sm:gap-4 min-[900px]:gap-5">
    <!-- credit: the "top up" link stretches over the card; the package
         chips sit above it as links of their own -->
    <div class="w-card credit">
      <span v-if="bonus > 0" class="w-tag bg-[#ffe14d] text-[#2a1a00]">{{ t('homeWallet.creditTag', { n: num(bonus) }) }}</span>
      <span class="w-title font-display">{{ t('homeWallet.creditTitle') }}</span>
      <span class="w-sub">{{ t('homeWallet.creditSub1') }}<br />{{ t('homeWallet.creditSub2') }}</span>
      <span v-if="offer?.packages.length" class="chips">
        <a
          v-for="p in offer.packages"
          :key="p.id"
          :href="lineHref('credit', `?pack=${encodeURIComponent(p.id)}`)"
          class="chip"
          :aria-label="t('homeWallet.packAria', { credits: num(p.credits), price: baht(p.price) })"
        >
          <span v-if="tier(p.credits)" class="dot" :class="tier(p.credits)!" aria-hidden="true"></span>
          {{ num(p.credits) }} <small>{{ baht(p.price) }}</small>
        </a>
      </span>
      <a :href="lineHref('credit')" class="w-go stretch bg-brand-pink text-white">
        {{ t('homeWallet.creditGo') }}<span aria-hidden="true">→</span>
      </a>
      <span class="art" aria-hidden="true">
        <span class="mc black"><i></i><img src="/credit/cat.webp" alt="" width="34" height="34" /></span>
        <span class="mc pink"><i></i><img src="/credit/cat.webp" alt="" width="34" height="34" /></span>
      </span>
    </div>

    <a :href="lineHref('pass')" class="w-card pass [--glow:rgb(255_207_63/0.45)]">
      <span class="w-tag border border-[#ffe14d] text-[#ffe14d]">✦ {{ t('homeWallet.passTag') }}</span>
      <span class="w-title font-display text-[#ffe58a]">Niddeaw Pass</span>
      <span class="w-sub">
        <template v-if="offer">{{ t('homeWallet.passSub', { price: num(offer.pass_price) }) }}<br /></template>{{ t('homeWallet.passWho') }}
      </span>
      <span class="chips">
        <span class="chip gold">⦸ {{ t('homeWallet.perkBlock') }}</span>
        <span class="chip gold">% {{ t('homeWallet.perkShop') }}</span>
        <span class="chip gold">◎ {{ t('homeWallet.perkLook') }}</span>
        <span class="chip gold">↗ {{ t('homeWallet.perkMine') }}</span>
      </span>
      <span class="w-go gold">{{ t('homeWallet.passGo') }}<span aria-hidden="true">→</span></span>
      <span class="tk" aria-hidden="true"><b>NIDDEAW</b><span>PASS</span></span>
      <span class="spark" aria-hidden="true">✦</span>
    </a>
  </div>
</template>

<style scoped>
/* The same glass as the tournament and shop doors (HomeCards): the credit
   card pink, the pass gold. */
.w-card {
  position: relative;
  display: flex;
  min-height: 164px;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  padding: 12px;
  border: 1px solid;
  border-radius: 22px;
  color: #fff;
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.3),
    0 22px 44px -22px var(--glow, rgb(234 76 164 / 0.55)),
    0 10px 28px rgb(6 0 20 / 0.45);
  transition: transform 0.15s;
}
.w-card:hover {
  transform: translateY(-2px);
}
.credit {
  border-color: rgb(234 76 164 / 0.55);
  background: linear-gradient(140deg, #4a0f3a, #1a0838 70%);
}
.pass {
  border-color: rgb(255 225 77 / 0.55);
  background:
    radial-gradient(90% 80% at 100% 100%, rgb(242 193 78 / 0.28), transparent 60%),
    linear-gradient(140deg, #3d2a06, #1a0838 72%);
}
.w-tag {
  align-self: flex-start;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 10px;
  line-height: 1;
  font-weight: 600;
}
.w-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}
.w-sub {
  font-size: 11px;
  font-weight: 300;
  color: rgb(255 255 255 / 0.75);
}
.w-go {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  margin-top: auto;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
}
.w-go.gold {
  background: linear-gradient(90deg, #ffe58a, #f2c14e);
  color: #2a1a00;
}
/* the credit card's one big link: it covers the whole card, under the
   chips. z-index auto, or this flex item stacks above them anyway. */
.stretch {
  position: static;
  z-index: auto;
}
.stretch::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 22px;
}
.stretch:focus-visible {
  outline: none;
}
.stretch:focus-visible::after {
  outline: 2px solid #ff8fd0;
  outline-offset: -3px;
}

/* the art: a pink card over a black one, and a gold pass ticket */
.art {
  position: absolute;
  right: 6px;
  bottom: 12px;
  width: 66px;
  height: 50px;
  pointer-events: none;
}
.mc {
  position: absolute;
  width: 54px;
  height: 34px;
  overflow: hidden;
  border-radius: 6px;
  box-shadow:
    0 6px 14px rgb(0 0 0 / 0.5),
    inset 0 1px 0 rgb(255 255 255 / 0.4);
}
.mc img {
  position: absolute;
  right: -6px;
  bottom: -8px;
  width: 30px;
  height: auto;
  opacity: 0.9;
}
.mc i {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 9px;
  height: 7px;
  border-radius: 2px;
  background: linear-gradient(135deg, #f7dc8a, #c9952f 55%, #f2d27a);
}
.mc.pink {
  top: 12px;
  right: 10px;
  rotate: -8deg;
  background:
    radial-gradient(120% 90% at 0% 0%, #ffd0e8 0%, transparent 45%),
    linear-gradient(135deg, #ff8fd0 0%, #ff4fa6 45%, #b81f74 100%);
}
.mc.black {
  top: 0;
  right: 0;
  rotate: 14deg;
  border: 1px solid rgb(242 193 78 / 0.5);
  background:
    radial-gradient(90% 70% at 100% 0%, rgb(155 107 255 / 0.35), transparent 60%),
    linear-gradient(140deg, #26222c 0%, #0b0a0e 55%, #000 100%);
}
.mc::after,
.pass::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.4) 50%, transparent 60%);
  background-size: 250% 100%;
  animation: shine 3.2s ease-in-out infinite;
  pointer-events: none;
}
.pass::after {
  background-image: linear-gradient(105deg, transparent 42%, rgb(255 240 190 / 0.12) 50%, transparent 58%);
  animation-duration: 4.5s;
}
@keyframes shine {
  0% {
    background-position: 120% 0;
  }
  60%,
  100% {
    background-position: -60% 0;
  }
}
.tk {
  position: absolute;
  right: 10px;
  bottom: 18px;
  display: flex;
  width: 62px;
  height: 38px;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  padding: 0 9px;
  border-radius: 9px;
  rotate: 10deg;
  background: linear-gradient(135deg, #ffe58a, #f2c14e 45%, #b9831f);
  color: #3a2500;
  box-shadow:
    0 8px 18px rgb(0 0 0 / 0.45),
    inset 0 1px 0 rgb(255 255 255 / 0.6);
}
.tk b {
  font-size: 6.5px;
  letter-spacing: 1.6px;
}
.tk span {
  font-size: 13px;
  font-weight: 800;
  line-height: 1.1;
}
/* the ticket's punched notches */
.tk::before,
.tk::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #241008;
  translate: 0 -50%;
}
.tk::before {
  left: -5px;
}
.tk::after {
  right: -5px;
}
.spark {
  position: absolute;
  right: 68px;
  bottom: 50px;
  font-size: 12px;
  color: #ffe58a;
  animation: twinkle 2s ease-in-out infinite;
}
@keyframes twinkle {
  50% {
    opacity: 0.25;
    scale: 0.7;
  }
}

/* the packages and the perks: from 640px, where there is room */
.chips {
  position: relative;
  z-index: 2;
  display: none;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 12px;
  padding: 7px 11px;
  background: rgb(255 255 255 / 0.07);
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s, border-color 0.15s;
}
a.chip:hover {
  border-color: rgb(255 143 208 / 0.6);
  background: rgb(255 79 166 / 0.16);
}
.chip small {
  font-size: 11px;
  font-weight: 400;
  color: rgb(255 255 255 / 0.6);
}
.chip.gold {
  border-color: rgb(242 193 78 / 0.35);
  background: rgb(242 193 78 / 0.12);
  color: #ffe8a3;
  font-weight: 500;
}
.dot {
  width: 14px;
  height: 9px;
  flex: none;
  border-radius: 2px;
}
.dot.pink {
  background: linear-gradient(135deg, #ff8fd0, #b81f74);
}
.dot.black {
  border: 1px solid #f2c14e;
  background: #111;
}

@media (min-width: 640px) {
  .w-card {
    min-height: 200px;
    gap: 6px;
    padding: 18px;
  }
  .w-title {
    font-size: 24px;
  }
  .w-sub {
    max-width: 62%;
    font-size: 13px;
  }
  .chips {
    display: flex;
  }
  .chip.gold {
    font-size: 12px;
  }
  .w-go {
    font-size: 14px;
    padding: 9px 15px;
  }
  .art,
  .tk {
    top: 18px;
    bottom: auto;
    scale: 1.4;
    transform-origin: 100% 0;
  }
  .art {
    right: 18px;
  }
  .tk {
    right: 24px;
  }
  .spark {
    top: 96px;
    right: 30px;
    bottom: auto;
  }
}
/* In the desktop grid the row runs the full width, so the cards stand
   taller and their art grows with them. */
@media (min-width: 900px) {
  .w-card {
    min-height: 230px;
    gap: 8px;
    padding: 26px;
  }
  .w-title {
    font-size: 30px;
  }
  .w-sub {
    font-size: 15px;
  }
  .w-go {
    font-size: 15px;
    padding: 11px 18px;
  }
  .art,
  .tk {
    top: 30px;
    scale: 1.9;
  }
  .art {
    right: 30px;
  }
  .tk {
    right: 38px;
  }
  .spark {
    top: 150px;
    right: 44px;
    font-size: 16px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .w-card {
    transition: none;
  }
  .mc::after,
  .pass::after,
  .spark {
    animation: none;
  }
}
</style>
