<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { Player } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloBadge from '@/components/players/EloBadge.vue'

const players = ref<Player[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const creating = ref(false)
const savingCreate = ref(false)
const newPlayer = reactive({ name: '', nickname: '', phone: '', line_id: '', elo_score: '' })
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

async function createPlayer(): Promise<void> {
  if (!newPlayer.name.trim()) return
  savingCreate.value = true
  try {
    let created = await adminApi.createPlayer({
      name: newPlayer.name.trim(),
      nickname: newPlayer.nickname.trim() || null,
      phone: newPlayer.phone.trim() || null,
      line_id: newPlayer.line_id.trim() || null,
      elo_score: newPlayer.elo_score.trim() ? Number(newPlayer.elo_score) : null,
    })
    if (newAvatarFile.value) {
      created = await adminApi.uploadAvatar(created.id, newAvatarFile.value)
    }
    players.value.unshift(created)
    newPlayer.name = ''
    newPlayer.nickname = ''
    newPlayer.phone = ''
    newPlayer.line_id = ''
    newPlayer.elo_score = ''
    newAvatarFile.value = null
    creating.value = false
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
      class="mt-4 grid gap-2 rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4 sm:grid-cols-2"
      @submit.prevent="createPlayer"
    >
      <input v-model="newPlayer.name" placeholder="ชื่อจริง *" required class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.nickname" placeholder="ชื่อเล่น" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.phone" placeholder="เบอร์โทร" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
      <input
        v-model="newPlayer.elo_score"
        type="number"
        placeholder="ELO เริ่มต้น (ค่าเริ่มต้น 1000)"
        title="ปล่อยว่างไว้ถ้าให้เริ่มที่ 1000 ตามปกติ"
        class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm"
      />
      <label class="flex items-center gap-2 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm text-white/60">
        รูปโปรไฟล์
        <input type="file" accept="image/*" class="flex-1 text-xs" @change="onNewAvatarSelected" />
      </label>
      <div class="flex gap-2 sm:col-span-2">
        <button type="submit" :disabled="savingCreate" class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50">
          {{ savingCreate ? 'กำลังบันทึก...' : 'บันทึกสมาชิกใหม่' }}
        </button>
        <button type="button" class="text-sm text-white/50" @click="creating = false">ยกเลิก</button>
      </div>
    </form>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="players.length === 0" class="mt-6 text-white/60">ยังไม่มีสมาชิก</p>

    <ul v-else class="mt-6 space-y-3">
      <li
        v-for="p in players"
        :key="p.id"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4"
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
            :class="p.is_active ? 'bg-white/10 text-white/60' : 'bg-green-500/20 text-green-400'"
            @click="toggleActive(p)"
          >
            {{ p.is_active ? 'ปิดใช้งาน' : 'เปิดใช้งาน' }}
          </button>
        </div>

        <form v-else class="grid gap-2 sm:grid-cols-2" @submit.prevent="saveEdit(p)">
          <input v-model="editForm.name" placeholder="ชื่อจริง *" required class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.nickname" placeholder="ชื่อเล่น" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.phone" placeholder="เบอร์โทร" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2 text-sm" />
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
