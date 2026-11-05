<script setup lang='ts'>
/**
 * Where the medal shelf sits, for a member who hasn't linked LINE: badges
 * are for linked members. The shelf shows through, faded and blurred, so
 * there is clearly something to collect, under a green panel that says how
 * to unlock it and how many medals are already waiting (they are counted
 * all along, and appear the moment the link is approved).
 *
 * The profile is public, so it speaks to whoever owns it ('if this is
 * you'). On a phone the button opens the club's LINE; on a computer, where
 * it can't, the club's QR stands in for it.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getQuestLineInvite } from '@/api/quests'
import type { LineInvite } from '@/api/admin'
import type { BadgeItem } from '@/utils/quests'
import BrandQr from '@/components/common/BrandQr.vue'

const props = defineProps<{ items: BadgeItem[]; waiting: number; waitingImgs: string[] }>()
const { t } = useI18n()
const invite = ref<LineInvite | null>(null)

onMounted(async () => {
  try {
    invite.value = await getQuestLineInvite()
  } catch {
    invite.value = null // the panel still says what to do
  }
})
</script>

<template>
  <section class="gate" :aria-label="t('quests.gate.title')">
    <div class="ghost" aria-hidden="true">
      <img
        v-for="it in props.items.slice(0, 12)"
        :key="it.id"
        :src="it.img"
        alt=""
        width="256"
        height="256"
        decoding="async"
      />
    </div>
    <div class="panel">
      <span class="bubble" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path
            d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5s5.9-3.5 8-6C21.4 14.2 22 12.7 22 11c0-4.4-4.5-8-10-8Z"
          />
        </svg>
      </span>
      <h2 class="font-display text-lg font-bold">
        {{ t('quests.gate.title') }}
      </h2>
      <p class="max-w-[30ch] text-[13px] leading-relaxed text-white/65">
        {{ t('quests.gate.body') }}
      </p>
      <p v-if="waiting > 0" class="waiting">
        <span class="sil" aria-hidden="true"
          ><img
            v-for="(src, i) in waitingImgs"
            :key="i"
            :src="src"
            alt=""
            width="64"
            height="64"
        /></span>
        {{ t('quests.gate.waiting', { n: waiting }) }}
      </p>
      <template v-if="invite">
        <!-- display lives on wrappers: the scoped rules below would beat lg:hidden -->
        <div class="lg:hidden">
          <a :href="invite.url" target="_blank" rel="noopener" class="cta">
            <span class="bubble sm" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5s5.9-3.5 8-6C21.4 14.2 22 12.7 22 11c0-4.4-4.5-8-10-8Z"
                />
              </svg>
            </span>
            {{ t('quests.gate.cta') }}
          </a>
        </div>
        <div class="hidden items-center gap-3 lg:flex">
          <BrandQr
            :modules="invite.qr_modules"
            :alt="t('quests.gate.qrAlt')"
            class="w-[120px] shrink-0"
          />
          <p
            class="max-w-[16ch] text-left text-xs leading-relaxed text-white/60"
          >
            {{ t('quests.gate.scan') }}
          </p>
        </div>
      </template>
      <div :class="{ 'lg:hidden': invite }">
        <ol class="steps">
          <li><i>1</i>{{ t('quests.gate.step1') }}</li>
          <li><i>2</i>{{ t('quests.gate.step2') }}</li>
          <li><i>3</i>{{ t('quests.gate.step3') }}</li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* the faded shelf and the panel share one cell: the taller sets the height */
.gate {
  display: grid;
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgb(6 199 85 / 0.35);
  background: #120d18;
}
.gate > * {
  grid-area: 1 / 1;
}
.ghost {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px 6px;
  padding: 14px 12px;
  opacity: 0.32;
  filter: blur(3px) grayscale(1) brightness(0.55);
}
.ghost img {
  display: block;
  width: 100%;
  height: auto;
  aspect-ratio: 1;
}
.panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px 16px;
  text-align: center;
  background: radial-gradient(
    90% 70% at 50% 40%,
    rgb(18 13 24 / 0.5),
    rgb(18 13 24 / 0.94)
  );
}
.bubble {
  display: inline-grid;
  width: 46px;
  height: 46px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: #06c755;
  color: #fff;
  box-shadow:
    0 0 0 6px rgb(6 199 85 / 0.15),
    0 0 28px rgb(6 199 85 / 0.45);
}
.bubble svg {
  width: 58%;
  height: 58%;
  fill: currentColor;
}
.bubble.sm {
  width: 18px;
  height: 18px;
  box-shadow: none;
  background: rgb(255 255 255 / 0.25);
}
.waiting {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  border: 1px solid rgb(242 193 78 / 0.35);
  background: rgb(242 193 78 / 0.1);
  padding: 5px 12px 5px 6px;
  font-size: 13px;
  color: #f2c14e;
}
.sil {
  display: flex;
}
.sil img {
  width: 26px;
  height: 26px;
  margin-right: -8px;
  filter: brightness(0) drop-shadow(0 0 3px rgb(242 193 78 / 0.9));
}
.sil img:last-child {
  margin-right: 0;
}
.cta {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 999px;
  background: #06c755;
  padding: 0 22px;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.cta:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 3px;
}
.steps {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px 10px;
  font-size: 11px;
  color: rgb(255 255 255 / 0.6);
}
.steps li {
  display: flex;
  align-items: center;
  gap: 4px;
}
.steps i {
  display: grid;
  width: 16px;
  height: 16px;
  place-items: center;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.1);
  font-family: var(--font-display);
  font-size: 10px;
  font-style: normal;
  color: #fff;
}
</style>
