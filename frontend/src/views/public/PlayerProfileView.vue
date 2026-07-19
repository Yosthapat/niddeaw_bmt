<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPlayerProfile } from '@/api/public'
import type { PlayerProfile } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const route = useRoute()
const profile = ref<PlayerProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    profile.value = await getPlayerProfile(String(route.params.id))
  } catch {
    error.value = 'ไม่พบข้อมูลสมาชิกนี้'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-8">
    <RouterLink to="/members" class="text-sm text-brand-pink hover:underline">&larr; กลับไปหน้าสมาชิก</RouterLink>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error || !profile" class="mt-6 text-red-400">{{ error }}</p>

    <template v-else>
      <div class="mt-6 flex flex-col items-center gap-3 text-center">
        <PlayerAvatar :name="profile.player.name" :avatar-url="profile.player.avatar_url" size="lg" />
        <h1 class="text-2xl font-bold">{{ profile.player.nickname || profile.player.name }}</h1>
        <p v-if="profile.player.nickname" class="-mt-2 text-sm text-white/50">{{ profile.player.name }}</p>
        <EloBadge :elo-score="profile.player.elo_score" show-score />
      </div>

      <div class="mt-8 grid grid-cols-3 gap-3 sm:grid-cols-6">
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Game</p>
          <p class="mt-1 text-xl font-bold">{{ profile.games }}</p>
        </div>
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Win</p>
          <p class="mt-1 text-xl font-bold text-green-400">{{ profile.wins }}</p>
        </div>
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Draw</p>
          <p class="mt-1 text-xl font-bold text-white/70">{{ profile.draws }}</p>
        </div>
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Loss</p>
          <p class="mt-1 text-xl font-bold text-red-400">{{ profile.losses }}</p>
        </div>
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Pts</p>
          <p class="mt-1 text-xl font-bold text-brand-pink">{{ profile.points }}</p>
        </div>
        <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3 text-center">
          <p class="text-xs text-white/50">Sc(%)</p>
          <p class="mt-1 text-xl font-bold">{{ profile.score_percent.toFixed(1) }}</p>
        </div>
      </div>

      <section v-if="profile.nemesis" class="mt-8 rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4">
        <h2 class="text-sm font-semibold text-white/70">เทกันจัง</h2>
        <div class="mt-3 flex items-center gap-3">
          <PlayerAvatar
            :name="profile.nemesis.player.name"
            :avatar-url="profile.nemesis.player.avatar_url"
            size="md"
          />
          <div class="flex-1">
            <RouterLink
              :to="`/members/${profile.nemesis.player.id}`"
              class="font-medium text-brand-pink hover:underline"
            >
              {{ profile.nemesis.player.nickname || profile.nemesis.player.name }}
            </RouterLink>
            <p class="text-xs text-white/50">
              เจอกัน {{ profile.nemesis.encounters }} ครั้ง · ชนะ {{ profile.nemesis.wins }} · แพ้
              {{ profile.nemesis.losses }} · เสมอ {{ profile.nemesis.draws }}
            </p>
          </div>
        </div>
      </section>
      <p v-else class="mt-8 text-center text-sm text-white/40">ยังไม่มีข้อมูลคู่ปรับ (ต้องเล่นแมตช์ก่อน)</p>
    </template>
  </main>
</template>
