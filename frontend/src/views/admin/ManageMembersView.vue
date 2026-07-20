<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { EloTier, Player } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const players = ref<Player[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Representative starting score per tier — matches the boundaries in
// backend/app/services/elo_service.py's get_tier() thresholds.
const tierOptions: { tier: EloTier; label: string; score: number; color: string }[] = [
  { tier: 'milk', label: 'Milk', score: 800, color: 'var(--color-tier-milk)' },
  { tier: 'soju', label: 'Soju', score: 1000, color: 'var(--color-tier-soju)' },
  { tier: 'beer', label: 'Beer', score: 1200, color: 'var(--color-tier-beer)' },
  { tier: 'highball', label: 'Highball', score: 1400, color: 'var(--color-tier-highball)' },
  { tier: 'vodka', label: 'Vodka', score: 1600, color: 'var(--color-tier-vodka)' },
]

const creating = ref(false)
const savingCreate = ref(false)
const createError = ref<string | null>(null)
const newPlayer = reactive({ name: '', nickname: '', phone: '', line_id: '' })
const selectedTier = ref<EloTier | null>(null)
const newAvatarFile = ref<File | null>(null)

function onNewAvatarSelected(event: Event): void {
  const input = event.target as HTMLInputElement
  newAvatarFile.value = input.files?.[0] ?? null
}

const editingId = ref<string | null>(null)
const savingEdit = ref(false)
const editForm = reactive({ name: '', nickname: '', phone: '', line_id: '' })
const uploadingAvatarId = ref<string | null>(null)

async function loadPlayers(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    players.value = await adminApi.getAllPlayers()
  } catch {
    error.value = 'โหลดรายชื่อสมาชิกไม่สำเร็จ'
  } finally {
    loading.value = false
  }
}

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

async function createPlayer(): Promise<void> {
  if (!newPlayer.name.trim()) return
  savingCreate.value = true
  createError.value = null
  try {
    const eloScore = selectedTier.value
      ? (tierOptions.find((t) => t.tier === selectedTier.value)?.score ?? null)
      : null

    let created = await adminApi.createPlayer({
      name: newPlayer.name.trim(),
      nickname: newPlayer.nickname.trim() || null,
      phone: newPlayer.phone.trim() || null,
      line_id: newPlayer.line_id.trim() || null,
      elo_score: eloScore,
    })

    if (newAvatarFile.value) {
      try {
        created = await adminApi.uploadAvatar(created.id, newAvatarFile.value)
      } catch (e) {
        createError.value = apiErrorMessage(e, 'สร้างสมาชิกสำเร็จ แต่อัพโหลดรูปไม่สำเร็จ — ลองอัพโหลดใหม่ทีหลังได้')
      }
    }

    players.value.unshift(created)
    newPlayer.name = ''
    newPlayer.nickname = ''
    newPlayer.phone = ''
    newPlayer.line_id = ''
    selectedTier.value = null
    newAvatarFile.value = null
    if (!createError.value) creating.value = false
  } catch (e) {
    createError.value = apiErrorMessage(e, 'สร้างสมาชิกไม่สำเร็จ ลองใหม่อีกครั้ง')
  } finally {
    savingCreate.value = false
  }
}

function startEdit(player: Player): void {
  editingId.value = player.id
  editForm.name = player.name
  editForm.nickname = player.nickname ?? ''
  editForm.phone = player.phone ?? ''
  editForm.line_id = player.line_id ?? ''
}

function cancelEdit(): void {
  editingId.value = null
}

async function saveEdit(player: Player): Promise<void> {
  savingEdit.value = true
  try {
    const updated = await adminApi.updatePlayer(player.id, {
      name: editForm.name.trim(),
      nickname: editForm.nickname.trim() || null,
      phone: editForm.phone.trim() || null,
      line_id: editForm.line_id.trim() || null,
    })
    players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
    editingId.value = null
  } finally {
    savingEdit.value = false
  }
}

async function toggleActive(player: Player): Promise<void> {
  const updated = await adminApi.updatePlayer(player.id, { is_active: !player.is_active })
  players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
}

async function onAvatarSelected(event: Event, player: Player): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingAvatarId.value = player.id
  try {
    const updated = await adminApi.uploadAvatar(player.id, file)
    players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
  } finally {
    uploadingAvatarId.value = null
    input.value = ''
  }
}

onMounted(loadPlayers)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-brand-pink">จัดการสมาชิก</h1>
      <button
        v-if="!creating"
        class="rounded-full bg-brand-pink px-3 py-1.5 text-sm font-semibold text-brand-black"
        @click="creating = true"
      >
        + เพิ่มสมาชิกใหม่
      </button>
    </div>

    <form
      v-if="creating"
      class="mt-4 grid gap-2 hud-panel border border-brand-pink/20 bg-brand-surface p-4 sm:grid-cols-2"
      @submit.prevent="createPlayer"
    >
      <input v-model="newPlayer.name" placeholder="ชื่อจริง *" required class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.nickname" placeholder="ชื่อเล่น" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.phone" placeholder="เบอร์โทร" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />

      <div class="sm:col-span-2">
        <p class="mb-1.5 text-xs text-white/40">ระดับเริ่มต้น (ไม่เลือก = เริ่มที่ Soju ตามปกติ)</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="opt in tierOptions"
            :key="opt.tier"
            type="button"
            class="hud-panel flex items-center gap-1.5 border px-3 py-1.5 text-xs font-semibold tracking-wide uppercase"
            :class="selectedTier === opt.tier ? 'border-brand-pink bg-brand-surface-raised' : 'border-brand-pink/20 bg-brand-black text-white/50'"
            @click="selectedTier = selectedTier === opt.tier ? null : opt.tier"
          >
            <TierMascot :tier="opt.tier" :size="20" />
            <span :style="{ color: selectedTier === opt.tier ? opt.color : undefined }">{{ opt.label }}</span>
          </button>
        </div>
      </div>

      <label class="flex items-center gap-2 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/60 sm:col-span-2">
        รูปโปรไฟล์
        <input type="file" accept="image/*" class="flex-1 text-xs" @change="onNewAvatarSelected" />
      </label>

      <p v-if="createError" class="text-sm text-status-error sm:col-span-2">{{ createError }}</p>

      <div class="flex gap-2 sm:col-span-2">
        <button type="submit" :disabled="savingCreate" class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50">
          {{ savingCreate ? 'กำลังบันทึก...' : 'บันทึกสมาชิกใหม่' }}
        </button>
        <button type="button" class="text-sm text-white/50" @click="creating = false">ยกเลิก</button>
      </div>
    </form>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="players.length === 0" class="mt-6 text-white/60">ยังไม่มีสมาชิก</p>

    <ul v-else class="mt-6 space-y-3">
      <li
        v-for="p in players"
        :key="p.id"
        class="hud-panel border border-brand-pink/20 bg-brand-surface p-4"
        :class="{ 'opacity-50': !p.is_active }"
      >
        <div v-if="editingId !== p.id" class="flex items-center gap-3">
          <label class="relative cursor-pointer">
            <PlayerAvatar :name="p.name" :avatar-url="p.avatar_url" size="md" />
            <input type="file" accept="image/*" class="hidden" @change="onAvatarSelected($event, p)" />
            <span v-if="uploadingAvatarId === p.id" class="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 text-[10px]">...</span>
          </label>
          <div class="flex-1">
            <p class="font-medium">{{ p.nickname || p.name }} <span v-if="p.nickname" class="text-xs text-white/40">({{ p.name }})</span></p>
            <p class="text-xs text-white/50">{{ p.phone || '-' }} · {{ p.line_id || '-' }}</p>
          </div>
          <EloBadge :elo-score="p.elo_score" show-score />
          <button class="text-xs text-brand-pink underline" @click="startEdit(p)">แก้ไข</button>
          <button
            class="rounded-full px-3 py-1 text-xs font-semibold"
            :class="p.is_active ? 'bg-white/10 text-white/60' : 'bg-status-success/20 text-status-success'"
            @click="toggleActive(p)"
          >
            {{ p.is_active ? 'ปิดใช้งาน' : 'เปิดใช้งาน' }}
          </button>
        </div>

        <form v-else class="grid gap-2 sm:grid-cols-2" @submit.prevent="saveEdit(p)">
          <input v-model="editForm.name" placeholder="ชื่อจริง *" required class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.nickname" placeholder="ชื่อเล่น" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.phone" placeholder="เบอร์โทร" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <div class="flex gap-2 sm:col-span-2">
            <button type="submit" :disabled="savingEdit" class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50">
              {{ savingEdit ? 'กำลังบันทึก...' : 'บันทึก' }}
            </button>
            <button type="button" class="text-sm text-white/50" @click="cancelEdit">ยกเลิก</button>
          </div>
        </form>
      </li>
    </ul>
  </main>
</template>
