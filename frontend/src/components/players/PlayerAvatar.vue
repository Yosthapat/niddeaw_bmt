<script setup lang="ts">
// `round`: a circle instead of the HUD notch, for the home page, which
// takes the hero's rounded glass rather than the scoreboard look.
//
// `playerId` on a round avatar: if that member wears a Niddeaw Pass frame
// (stores/passStyles.ts), it is drawn round the picture. `frame` sets one
// outright, for the LINE page's previews. The frame sits outside the
// picture's box, so nothing around it moves.
import { computed, onMounted } from 'vue'
import type { PassFrame } from '@/api/line'
import { usePassStylesStore } from '@/stores/passStyles'
import PlayerAvatarFace from '@/components/players/PlayerAvatarFace.vue'

defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<{
    name: string
    avatarUrl?: string | null
    size?: 'sm' | 'md' | 'lg' | 'xl'
    round?: boolean
    playerId?: string | null
    frame?: PassFrame | null
  }>(),
  { avatarUrl: null, size: 'md', round: false, playerId: null, frame: undefined },
)

const styles = usePassStylesStore()
onMounted(() => {
  if (props.playerId && props.frame === undefined) void styles.load()
})
const shownFrame = computed<PassFrame | null>(() => {
  if (props.frame !== undefined) return props.frame
  return props.round ? styles.frameOf(props.playerId) : null
})

</script>

<template>
  <!-- No frame: the bare picture, laid out exactly as before (a parent's
       -space-x and the like still reach it). -->
  <PlayerAvatarFace v-if="!shownFrame" v-bind="$attrs" :name="name" :avatar-url="avatarUrl" :size="size" :round="round" />
  <!-- With one, the caller's classes (an overlap's -ml, a ring) go on the
       frame, so the ring stays centred on the picture. -->
  <span v-else v-bind="$attrs" class="pf" :class="[`pf-${shownFrame}`, `pf-${size}`]">
    <PlayerAvatarFace :name="name" :avatar-url="avatarUrl" :size="size" :round="round" />
    <svg v-if="shownFrame === 'crown'" class="pf-x-crown" viewBox="0 0 40 26" aria-hidden="true">
      <path d="M3 24 1 6l10 8 9-13 9 13 10-8-2 18Z" fill="#ff4fa6" stroke="#ffe58a" stroke-width="2" stroke-linejoin="round" />
      <circle cx="20" cy="3" r="3" fill="#ffe58a" />
    </svg>
    <svg v-else-if="shownFrame === 'moon'" class="pf-x-moon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M14 2a8 8 0 1 0 4 14A7 7 0 0 1 14 2Z" fill="#e9edff" />
    </svg>
    <span v-else-if="shownFrame === 'king'" class="pf-x-gems" aria-hidden="true"><i /><i /><i /></span>
    <template v-else-if="shownFrame === 'legend'">
      <span class="pf-spark pf-spark--a" aria-hidden="true">✦</span>
      <span class="pf-spark pf-spark--b" aria-hidden="true">✦</span>
    </template>
  </span>
</template>

<style scoped>
/* The ring is drawn just outside the picture, behind it; the picture keeps
   its own size, so nothing around it moves. */
.pf {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
  isolation: isolate;
  border-radius: 9999px;
}
.pf > :deep(:first-child) {
  position: relative;
  z-index: 1;
}
.pf::before {
  content: '';
  position: absolute;
  z-index: 0;
  inset: -9%;
  border-radius: 9999px;
}
.pf-xl::before {
  inset: -5%;
}

@property --pf-a {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
@keyframes pf-turn {
  to {
    --pf-a: 360deg;
  }
}

.pf-gold::before {
  background: conic-gradient(from var(--pf-a), #fff3b0, #f2c14e, #9a6a12, #ffe58a, #c9952f, #fff3b0);
  box-shadow: 0 0 12px rgb(242 193 78 / 0.55);
  animation: pf-turn 4s linear infinite;
}
.pf-neon::before {
  background: #ff4fa6;
  -webkit-mask: radial-gradient(closest-side, transparent 80%, #000 84%);
  mask: radial-gradient(closest-side, transparent 80%, #000 84%);
  filter: drop-shadow(0 0 4px #ff4fa6) drop-shadow(0 0 8px rgb(155 107 255 / 0.8));
}
.pf-crown::before {
  background: conic-gradient(#ff8fd0, #f2c14e, #ff8fd0, #f2c14e, #ff8fd0);
}
.pf-moon::before {
  background: conic-gradient(from var(--pf-a), #f4f6ff, #aab3cf, #6c7391, #e3e8ff, #9aa3c4, #f4f6ff);
  box-shadow: 0 0 12px rgb(200 210 255 / 0.45);
  animation: pf-turn 6s linear infinite;
}
.pf-king::before {
  background: conic-gradient(
    from var(--pf-a),
    #7a2bd6,
    #f2c14e,
    #ff4fa6,
    #f2c14e,
    #7a2bd6,
    #f2c14e,
    #ff4fa6,
    #f2c14e,
    #7a2bd6
  );
  box-shadow: 0 0 14px rgb(160 90 255 / 0.6);
  animation: pf-turn 5s linear infinite;
}
.pf-legend::before {
  background: conic-gradient(from var(--pf-a), #8ff7ff, #b88cff, #ff8fd0, #ffe58a, #8fffc1, #8ff7ff);
  box-shadow:
    0 0 14px rgb(150 220 255 / 0.7),
    0 0 26px rgb(255 143 208 / 0.35);
  animation: pf-turn 3s linear infinite;
}

/* the extras, sized off the picture so they suit every size */
.pf-x-crown {
  position: absolute;
  z-index: 2;
  top: -40%;
  left: 50%;
  width: 62%;
  translate: -50% 0;
  filter: drop-shadow(0 3px 3px rgb(0 0 0 / 0.5));
}
.pf-x-moon {
  position: absolute;
  z-index: 2;
  top: -12%;
  right: -16%;
  width: 38%;
  filter: drop-shadow(0 0 4px rgb(220 230 255 / 0.8));
}
.pf-x-gems {
  position: absolute;
  z-index: 2;
  inset: -9%;
}
.pf-x-gems i {
  position: absolute;
  width: 14%;
  height: 14%;
  rotate: 45deg;
  background: linear-gradient(135deg, #fff, #ff8fd0 40%, #b81f74);
  box-shadow: 0 0 5px #ff8fd0;
}
.pf-x-gems i:nth-child(1) {
  top: -6%;
  left: 43%;
}
.pf-x-gems i:nth-child(2) {
  top: 43%;
  left: -6%;
}
.pf-x-gems i:nth-child(3) {
  top: 43%;
  right: -6%;
}
.pf-spark {
  position: absolute;
  z-index: 2;
  color: #fff;
  line-height: 1;
  text-shadow: 0 0 6px #8ff7ff;
  animation: pf-twinkle 1.8s ease-in-out infinite;
}
.pf-spark--a {
  top: -16%;
  right: -10%;
}
.pf-spark--b {
  bottom: -8%;
  left: -14%;
  animation-delay: 0.9s;
}
.pf-sm .pf-spark {
  font-size: 9px;
}
.pf-md .pf-spark {
  font-size: 11px;
}
.pf-lg .pf-spark {
  font-size: 13px;
}
.pf-xl .pf-spark {
  font-size: 28px;
}
@keyframes pf-twinkle {
  50% {
    opacity: 0.3;
    scale: 0.7;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pf::before,
  .pf-spark {
    animation: none;
  }
}
</style>
