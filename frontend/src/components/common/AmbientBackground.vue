<script setup lang="ts">
// Fixed, full-viewport backdrop of slowly drifting blurred blobs — keeps
// public pages feeling alive even when nothing on screen is scrolling or
// polling. Mounted once in App.vue for non-admin routes only. Pure CSS
// (see .ambient-bg/.ambient-blob* in tailwind.css); disabled entirely
// under prefers-reduced-motion by that same stylesheet.
</script>

<template>
  <div class="ambient-bg" aria-hidden="true">
    <div class="ambient-blob ambient-blob--a" />
    <div class="ambient-blob ambient-blob--b" />
    <div class="ambient-blob ambient-blob--c" />
  </div>
</template>
