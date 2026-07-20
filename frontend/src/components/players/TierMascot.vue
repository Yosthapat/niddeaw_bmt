<script setup lang="ts">
import type { EloTier } from '@/types'

withDefaults(defineProps<{ tier: EloTier; size?: number }>(), {
  size: 64,
})
</script>

<template>
  <svg
    v-if="tier === 'milk'"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Milk tier mascot"
  >
    <path
      d="M30 40 L30 100 Q30 106 36 106 L84 106 Q90 106 90 100 L90 40 Z"
      fill="#e8e4da"
      stroke="#2a2420"
      stroke-width="4"
    />
    <path d="M30 40 L60 20 L90 40 Z" fill="#f5f2ea" stroke="#2a2420" stroke-width="4" stroke-linejoin="round" />
    <line x1="60" y1="20" x2="60" y2="40" stroke="#2a2420" stroke-width="3" />
    <!-- sleepy cowlick — a beginner still learning to stand steady -->
    <path d="M57 18 Q60 8 63 18 Q60 14 57 18" fill="#f5f2ea" stroke="#2a2420" stroke-width="3" stroke-linejoin="round" />
    <!-- content closed eyes, not alert dots — innocent and unbothered -->
    <path d="M44 65 Q48 59 52 65" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M68 65 Q72 59 76 65" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <circle cx="42" cy="76" r="6" fill="#f2b6c6" opacity="0.8" />
    <circle cx="78" cy="76" r="6" fill="#f2b6c6" opacity="0.8" />
    <path d="M52 78 Q60 82 68 78" stroke="#2a2420" stroke-width="4" fill="none" stroke-linecap="round" />
  </svg>

  <svg
    v-else-if="tier === 'soju'"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Soju tier mascot"
  >
    <rect x="52" y="14" width="16" height="22" rx="4" fill="#8ec899" stroke="#2a2420" stroke-width="4" />
    <rect x="48" y="6" width="24" height="12" rx="3" fill="#4f7a58" stroke="#2a2420" stroke-width="4" />
    <path
      d="M36 36 Q30 40 30 50 L30 100 Q30 108 38 108 L82 108 Q90 108 90 100 L90 50 Q90 40 84 36 Z"
      fill="#8ec899"
      stroke="#2a2420"
      stroke-width="4"
    />
    <rect x="38" y="62" width="44" height="26" rx="4" fill="#ffffff" stroke="#2a2420" stroke-width="3" />
    <!-- one-eyed wink + a bead of sweat — the easygoing, already-a-bit-tipsy regular -->
    <path d="M47 75 Q52 70 57 75" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <circle cx="68" cy="75" r="4" fill="#2a2420" />
    <path d="M83 58 Q87 64 83 68 Q79 64 83 58" fill="#cdeed4" stroke="#2a2420" stroke-width="2" />
    <path d="M52 82 Q59 89 68 80" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
  </svg>

  <svg
    v-else-if="tier === 'beer'"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Beer tier mascot"
  >
    <path
      d="M88 48 Q108 48 108 68 Q108 88 88 88"
      fill="none"
      stroke="#2a2420"
      stroke-width="8"
      stroke-linecap="round"
    />
    <path
      d="M26 46 L94 46 L90 104 Q89 110 83 110 L37 110 Q31 110 30 104 Z"
      fill="#dfa11a"
      stroke="#2a2420"
      stroke-width="4"
      stroke-linejoin="round"
    />
    <path
      d="M24 46 Q24 30 36 30 Q38 20 50 24 Q56 14 66 22 Q78 16 82 28 Q96 26 96 42 Q96 48 88 48 L32 48 Q24 48 24 46 Z"
      fill="#fff8e6"
      stroke="#2a2420"
      stroke-width="4"
      stroke-linejoin="round"
    />
    <!-- big joyful closed-eye cheer, wide open laugh — the hearty, having-a-great-time core of the club -->
    <path d="M45 74 Q52 66 59 74" stroke="#2a2420" stroke-width="4" fill="none" stroke-linecap="round" />
    <path d="M65 74 Q72 66 79 74" stroke="#2a2420" stroke-width="4" fill="none" stroke-linecap="round" />
    <path
      d="M47 84 Q61 102 77 84"
      stroke="#2a2420"
      stroke-width="4"
      fill="#7a4a0a"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <ellipse cx="30" cy="52" rx="3" ry="4.5" fill="#fff8e6" stroke="#2a2420" stroke-width="2" />
    <ellipse cx="92" cy="54" rx="3" ry="4.5" fill="#fff8e6" stroke="#2a2420" stroke-width="2" />
  </svg>

  <svg
    v-else-if="tier === 'whisky'"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Whisky tier mascot"
  >
    <path
      d="M32 34 L88 34 L84 104 Q83 110 77 110 L43 110 Q37 110 36 104 Z"
      fill="none"
      stroke="#2a2420"
      stroke-width="4"
      stroke-linejoin="round"
    />
    <path
      d="M34 60 L86 60 L84 104 Q83 110 77 110 L43 110 Q37 110 36 104 Z"
      fill="#a8503f"
      opacity="0.9"
    />
    <!-- a single big ice sphere, not cubes — steadier and more deliberate than highball's fizz -->
    <circle cx="60" cy="64" r="16" fill="#f4e9da" opacity="0.95" stroke="#2a2420" stroke-width="3" />
    <path d="M52 57 Q56 53 62 54" stroke="#ffffff" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.7" />
    <!-- calm, composed eyes and an even, unhurried smile — matured confidence, no smirk or swagger yet -->
    <path d="M48 90 Q52 87 56 90" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M64 90 Q68 87 72 90" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M52 98 Q60 102 68 98" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
  </svg>

  <svg
    v-else-if="tier === 'highball'"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Highball tier mascot"
  >
    <path
      d="M38 20 L82 20 L74 106 Q73 112 67 112 L53 112 Q47 112 46 106 Z"
      fill="none"
      stroke="#2a2420"
      stroke-width="4"
      stroke-linejoin="round"
    />
    <path
      d="M42 55 L78 55 L74 106 Q73 112 67 112 L53 112 Q47 112 46 106 Z"
      fill="#ea6f2f"
      opacity="0.85"
    />
    <circle cx="55" cy="80" r="2.5" fill="#ffd9b3" />
    <circle cx="65" cy="90" r="2" fill="#ffd9b3" />
    <circle cx="60" cy="70" r="2" fill="#ffd9b3" />
    <rect
      x="50"
      y="58"
      width="14"
      height="14"
      rx="3"
      fill="#ffffff"
      opacity="0.9"
      stroke="#2a2420"
      stroke-width="2.5"
      transform="rotate(-12 57 65)"
    />
    <!-- angled brows converging toward center + a lopsided smirk — sporty, game-ready determination -->
    <path d="M49 87 L57 91" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M63 91 L71 87" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <circle cx="55" cy="94" r="4" fill="#2a2420" />
    <circle cx="68" cy="94" r="4" fill="#2a2420" />
    <path d="M52 101 Q62 107 72 98" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
  </svg>

  <svg
    v-else
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    role="img"
    aria-label="Vodka tier mascot"
  >
    <path
      d="M46 18 L50 8 L58 16 L60 6 L62 16 L70 8 L74 18 Z"
      fill="#f5c518"
      stroke="#2a2420"
      stroke-width="3"
      stroke-linejoin="round"
    />
    <rect x="52" y="20" width="16" height="18" fill="#c9a8f7" stroke="#2a2420" stroke-width="4" />
    <path
      d="M40 38 Q34 42 34 52 L34 100 Q34 108 42 108 L78 108 Q86 108 86 100 L86 52 Q86 42 80 38 Z"
      fill="#9d5bf4"
      stroke="#2a2420"
      stroke-width="4"
    />
    <rect x="42" y="64" width="36" height="24" rx="4" fill="#f4ecff" stroke="#2a2420" stroke-width="3" />
    <!-- one arched brow of smug confidence over half-lidded, unbothered eyes -->
    <path d="M62 67 Q68 63 74 67" stroke="#2a2420" stroke-width="3" fill="none" stroke-linecap="round" />
    <path d="M48 76 Q52 73 56 76" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M64 76 Q68 73 72 76" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M50 84 Q59 89 70 82" stroke="#2a2420" stroke-width="3.5" fill="none" stroke-linecap="round" />
    <path d="M90 50 L92 56 L98 58 L92 60 L90 66 L88 60 L82 58 L88 56 Z" fill="#f5c518" />
  </svg>
</template>
