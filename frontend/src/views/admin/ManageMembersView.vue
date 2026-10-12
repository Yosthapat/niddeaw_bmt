<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { ApiError } from '@/api/client'
import { useEloTier, tierTextStyle } from '@/composables/useEloTier'
import { AVATAR_DIMENSION, compressImage } from '@/utils/imageCompression'
import { nicknameProblem } from '@/utils/nickname'
import type { EloTier, Player } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const { t } = useI18n()
const { confirm } = useConfirmDialog()

const players = ref<Player[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Sixteen members and growing, every one a row with three buttons: finding
// one by scrolling is the slowest thing on this screen. The count in the
// heading stays the club's, so a search narrows the list without ever
// changing what the screen claims the club has.
const search = ref('')

// The API is what actually enforces the nickname rules — both this screen
// and the check-in screen call it. This says the same thing while the
// admin is still typing, so they are not told after a round trip that the
// name they just entered will not do.
function nicknameMessage(raw: string, excludeId?: string): string | null {
  if (!raw.trim()) return null // an empty box is not yet a mistake
  const problem = nicknameProblem(raw)
  if (problem) return t(`members.nickname${problem[0].toUpperCase()}${problem.slice(1)}`)
  // Only members still in the club hold a name: someone deleted has left,
  // and reserving their nickname forever would retire it from the club.
  const clash = players.value.find(
    (p) =>
      p.is_active &&
      p.id !== excludeId &&
      p.nickname.toLowerCase() === raw.trim().split(/\s+/).join(' ').toLowerCase(),
  )
  return clash ? t('members.nicknameTaken') : null
}

const newNameProblem = computed(() => nicknameMessage(newPlayer.nickname))
const editNameProblem = computed(() =>
  editingId.value ? nicknameMessage(editForm.nickname, editingId.value) : null,
)
// A deleted member is kept rather than removed when they have matches,
// check-ins or a bill behind them — the alternative is breaking every
// record they appear in. They are out of the list by default, which is
// what "deleted" should look like.
//
// This switch is the only way back from such a delete. "ลบ" cannot
// promise to be permanent — for anyone who has played a night it can do
// no more than hide them — so without somewhere they still appear, one
// mistaken tap would be unrecoverable from the screens entirely.
const showDeleted = ref(false)
const deletedCount = computed(() => players.value.filter((p) => !p.is_active).length)
const activeCount = computed(() => players.value.filter((p) => p.is_active).length)

const visiblePlayers = computed(() => {
  const query = search.value.trim().toLowerCase()
  return players.value.filter(
    (p) =>
      (p.is_active || showDeleted.value) &&
      (!query || p.nickname.toLowerCase().includes(query)),
  )
})

// Representative starting score per tier — matches the boundaries in
// backend/app/services/elo_service.py's get_tier() thresholds.
const tierOptions: { tier: EloTier; label: string; score: number; color: string; gradient?: string }[] = [
  { tier: 'milk', label: 'Milk', score: 800, color: 'var(--color-tier-milk)' },
  { tier: 'beer', label: 'Beer', score: 1000, color: 'var(--color-tier-beer)' },
  { tier: 'highball', label: 'Highball', score: 1200, color: 'var(--color-tier-highball)' },
  { tier: 'wine', label: 'Wine', score: 1400, color: 'var(--color-tier-wine)' },
  { tier: 'soju', label: 'Soju', score: 1600, color: 'var(--color-tier-soju)' },
  { tier: 'whisky', label: 'Whisky', score: 1800, color: 'var(--color-tier-whisky)' },
  { tier: 'vodka', label: 'Vodka', score: 2000, color: 'var(--color-tier-vodka)' },
  { tier: 'absinthe', label: 'Absinthe', score: 2200, color: 'var(--color-tier-absinthe)', gradient: 'var(--gradient-tier-absinthe)' },
]

type HandOption = '' | 'left' | 'right'

const creating = ref(false)
const savingCreate = ref(false)
const createError = ref<string | null>(null)
const newPlayer = reactive({
  nickname: '',
  line_id: '',
  dominant_hand: '' as HandOption,
  tiktok: '',
  instagram: '',
  quote: '',
})
const selectedTier = ref<EloTier | null>(null)
const newAvatarFile = ref<File | null>(null)

async function onNewAvatarSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  newAvatarFile.value = file ? await compressImage(file, AVATAR_DIMENSION) : null
}

const editingId = ref<string | null>(null)
const savingEdit = ref(false)
const editForm = reactive({
  nickname: '',
  line_id: '',
  dominant_hand: '' as HandOption,
  tiktok: '',
  instagram: '',
  quote: '',
  elo_score: 0,
})
const uploadingAvatarId = ref<string | null>(null)
const deletingId = ref<string | null>(null)
const rowError = ref<string | null>(null)
const rowNotice = ref<string | null>(null)

async function loadPlayers(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    players.value = await adminApi.getAllPlayers()
  } catch {
    error.value = t('members.loadListError')
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
  if (!newPlayer.nickname.trim()) return
  savingCreate.value = true
  createError.value = null
  try {
    const eloScore = selectedTier.value
      ? (tierOptions.find((t) => t.tier === selectedTier.value)?.score ?? null)
      : null

    let created = await adminApi.createPlayer({
      nickname: newPlayer.nickname.trim(),
      line_id: newPlayer.line_id.trim() || null,
      dominant_hand: newPlayer.dominant_hand || null,
      tiktok: newPlayer.tiktok.trim() || null,
      instagram: newPlayer.instagram.trim() || null,
      quote: newPlayer.quote.trim() || null,
      elo_score: eloScore,
    })

    if (newAvatarFile.value) {
      try {
        created = await adminApi.uploadAvatar(created.id, newAvatarFile.value)
      } catch (e) {
        createError.value = apiErrorMessage(e, t('members.createdButAvatarFailed'))
      }
    }

    players.value.unshift(created)
    newPlayer.nickname = ''
    newPlayer.line_id = ''
    newPlayer.dominant_hand = ''
    newPlayer.tiktok = ''
    newPlayer.instagram = ''
    newPlayer.quote = ''
    selectedTier.value = null
    newAvatarFile.value = null
    if (!createError.value) creating.value = false
  } catch (e) {
    createError.value = apiErrorMessage(e, t('members.createFailed'))
  } finally {
    savingCreate.value = false
  }
}

function startEdit(player: Player): void {
  editingId.value = player.id
  editForm.nickname = player.nickname
  editForm.line_id = player.line_id ?? ''
  editForm.dominant_hand = player.dominant_hand ?? ''
  editForm.tiktok = player.tiktok ?? ''
  editForm.instagram = player.instagram ?? ''
  editForm.quote = player.quote ?? ''
  editForm.elo_score = player.elo_score
}

function cancelEdit(): void {
  editingId.value = null
}

async function saveEdit(player: Player): Promise<void> {
  savingEdit.value = true
  try {
    const updated = await adminApi.updatePlayer(player.id, {
      nickname: editForm.nickname.trim(),
      line_id: editForm.line_id.trim() || null,
      dominant_hand: editForm.dominant_hand || null,
      tiktok: editForm.tiktok.trim() || null,
      instagram: editForm.instagram.trim() || null,
      quote: editForm.quote.trim() || null,
      elo_score: editForm.elo_score,
    })
    players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
    editingId.value = null
  } finally {
    savingEdit.value = false
  }
}

// No confirmation on the way back in: this undoes a delete rather than
// doing anything, and a tap in error is undone by the delete button that
// takes its place.
async function restorePlayer(player: Player): Promise<void> {
  const updated = await adminApi.updatePlayer(player.id, { is_active: true })
  players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
}

async function removePlayer(player: Player): Promise<void> {
  const confirmed = await confirm({
    title: t('members.delete'),
    message: t('members.deleteConfirm', { name: player.nickname }),
    danger: true,
  })
  if (!confirmed) return
  deletingId.value = player.id
  rowError.value = null
  rowNotice.value = null
  try {
    await adminApi.deletePlayer(player.id)
    players.value = players.value.filter((p) => p.id !== player.id)
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      try {
        const updated = await adminApi.updatePlayer(player.id, { is_active: false })
        players.value = players.value.map((p) => (p.id === updated.id ? updated : p))
        rowNotice.value = t('members.deleteFallbackDeactivated', { name: player.nickname })
      } catch (e2) {
        rowError.value = apiErrorMessage(e2, t('members.deleteFailed'))
      }
    } else {
      rowError.value = apiErrorMessage(e, t('members.deleteFailed'))
    }
  } finally {
    deletingId.value = null
  }
}

function eloTierFor(score: number): EloTier {
  return useEloTier(score).tier
}

async function onAvatarSelected(event: Event, player: Player): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadingAvatarId.value = player.id
  try {
    const updated = await adminApi.uploadAvatar(player.id, await compressImage(file, AVATAR_DIMENSION))
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
      <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.members') }}</h1>
      <button
        v-if="!creating"
        class="tap rounded-full bg-brand-pink px-3 text-sm font-semibold text-brand-black"
        @click="creating = true"
      >
        + {{ t('members.addNew') }}
      </button>
    </div>

    <form
      v-if="creating"
      class="mt-4 grid gap-2 hud-panel border border-brand-pink/20 bg-brand-surface p-4 sm:grid-cols-2"
      @submit.prevent="createPlayer"
    >
      <input v-model="newPlayer.nickname" :placeholder="t('members.nicknameRequired')" required class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <select v-model="newPlayer.dominant_hand" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/80">
        <option value="">{{ t('members.handUnset') }}</option>
        <option value="left">{{ t('profile.leftHanded') }}</option>
        <option value="right">{{ t('profile.rightHanded') }}</option>
      </select>
      <input v-model="newPlayer.tiktok" placeholder="TikTok" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.instagram" placeholder="Instagram" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
      <input v-model="newPlayer.quote" :placeholder="t('members.quote')" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm sm:col-span-2" />

      <div class="sm:col-span-2">
        <p class="mb-1.5 text-xs text-white/40">{{ t('members.startingTierHint') }}</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="opt in tierOptions"
            :key="opt.tier"
            type="button"
            class="hud-panel flex items-center gap-1.5 border px-3 py-1.5 text-xs font-semibold tracking-wide uppercase"
            :class="selectedTier === opt.tier ? 'border-brand-pink bg-brand-surface-raised' : 'border-brand-pink/20 bg-brand-black text-white/50'"
            @click="selectedTier = selectedTier === opt.tier ? null : opt.tier"
          >
            <TierMascot :tier="opt.tier" :size="20" :interactive="false" />
            <span :style="selectedTier === opt.tier ? tierTextStyle(opt.color, opt.gradient) : undefined">{{ opt.label }}</span>
          </button>
        </div>
      </div>

      <label class="flex items-center gap-2 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/60 sm:col-span-2">
        {{ t('members.profilePhoto') }}
        <input type="file" accept="image/*" class="flex-1 text-xs" @change="onNewAvatarSelected" />
      </label>

      <p v-if="newNameProblem" class="text-sm text-status-error sm:col-span-2">{{ newNameProblem }}</p>
      <p v-if="createError" class="text-sm text-status-error sm:col-span-2">{{ createError }}</p>

      <div class="flex gap-2 sm:col-span-2">
        <button
          type="submit"
          :disabled="savingCreate || newNameProblem !== null || !newPlayer.nickname.trim()"
          class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
        >
          {{ savingCreate ? t('common.saving') : t('members.saveNew') }}
        </button>
        <button type="button" class="text-sm text-white/50" @click="creating = false">{{ t('common.cancel') }}</button>
      </div>
    </form>

    <input
      v-model="search"
      type="search"
      :placeholder="t('members.searchPlaceholder')"
      class="hud-panel mt-4 w-full border border-brand-pink/25 bg-brand-surface px-3 py-2 text-sm outline-none focus:border-brand-pink"
    />

    <p v-if="rowError" class="mt-4 text-sm text-status-error">{{ rowError }}</p>
    <p v-if="rowNotice" class="mt-4 text-sm text-status-success">{{ rowNotice }}</p>
    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="players.length === 0" class="mt-6 text-white/60">{{ t('members.empty') }}</p>

    <template v-else>
    <div class="mt-6 flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-white/70">
        {{ t('members.listTitle') }} ({{ activeCount }})
      </h2>
      <button
        v-if="deletedCount > 0"
        type="button"
        class="tap rounded-full border border-white/15 px-3 text-xs text-white/50"
        :class="showDeleted ? 'border-brand-pink/40 text-brand-pink' : ''"
        @click="showDeleted = !showDeleted"
      >
        {{ t('members.showDeleted', { n: deletedCount }) }}
      </button>
    </div>
    <p v-if="visiblePlayers.length === 0" class="mt-2 text-sm text-white/40">
      {{ t('members.noSearchResults') }}
    </p>
    <ul class="mt-2 space-y-3">
      <li
        v-for="p in visiblePlayers"
        :key="p.id"
        class="hud-hover hud-panel border border-brand-pink/20 bg-brand-surface p-4"
        :class="{ 'opacity-50': !p.is_active }"
      >
        <div v-if="editingId !== p.id">
          <div class="flex items-center gap-3">
            <label class="relative cursor-pointer">
              <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="md" />
              <input type="file" accept="image/*" class="hidden" @change="onAvatarSelected($event, p)" />
              <span v-if="uploadingAvatarId === p.id" class="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 text-[10px]">...</span>
            </label>
            <p class="min-w-0 flex-1 truncate font-medium">
              {{ p.nickname }}
              <span
                v-if="!p.is_active"
                class="ml-1 rounded-full bg-status-error/20 px-2 py-0.5 align-middle text-[10px] font-semibold text-status-error"
              >
                {{ t('members.deletedBadge') }}
              </span>
            </p>
            <TierMascot :tier="p.elo_level" :size="28" :interactive="false" />
            <EloBadge :elo-score="p.elo_score" show-score />
          </div>
          <div class="mt-2 flex items-center gap-2">
            <button
              class="min-h-10 flex-1 rounded-full border border-brand-pink/40 px-3 text-xs font-semibold text-brand-pink"
              @click="startEdit(p)"
            >
              {{ t('common.edit') }}
            </button>
            <button
              v-if="p.is_active"
              :disabled="deletingId === p.id"
              class="min-h-10 flex-1 rounded-full bg-status-error/20 px-3 text-xs font-semibold text-status-error disabled:opacity-50"
              @click="removePlayer(p)"
            >
              {{ deletingId === p.id ? t('common.saving') : t('members.delete') }}
            </button>
            <button
              v-else
              class="min-h-10 flex-1 rounded-full bg-status-success/20 px-3 text-xs font-semibold text-status-success"
              @click="restorePlayer(p)"
            >
              {{ t('members.restore') }}
            </button>
          </div>
        </div>

        <form v-else class="grid gap-2 sm:grid-cols-2" @submit.prevent="saveEdit(p)">
          <label class="relative flex w-fit cursor-pointer items-center gap-2 text-xs text-white/50 sm:col-span-2">
            <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="md" />
            <input type="file" accept="image/*" class="hidden" @change="onAvatarSelected($event, p)" />
            <span v-if="uploadingAvatarId === p.id" class="absolute inset-0 flex items-center justify-center bg-black/60 text-[10px]">...</span>
            <span>{{ t('members.clickToChangePhoto') }}</span>
          </label>
          <input v-model="editForm.nickname" :placeholder="t('members.nicknameRequired')" required class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.line_id" placeholder="LINE ID" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <select v-model="editForm.dominant_hand" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/80">
            <option value="">{{ t('members.handUnset') }}</option>
            <option value="left">{{ t('profile.leftHanded') }}</option>
            <option value="right">{{ t('profile.rightHanded') }}</option>
          </select>
          <input v-model="editForm.tiktok" placeholder="TikTok" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.instagram" placeholder="Instagram" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm" />
          <input v-model="editForm.quote" :placeholder="t('members.quote')" class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm sm:col-span-2" />
          <label class="flex items-center gap-2 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm sm:col-span-2">
            <span class="shrink-0 text-white/50">{{ t('members.eloScore') }}</span>
            <input v-model.number="editForm.elo_score" type="number" class="w-24 bg-transparent text-center" />
            <TierMascot :tier="eloTierFor(editForm.elo_score)" :size="24" class="shrink-0" :interactive="false" />
          </label>
          <p v-if="editNameProblem" class="text-sm text-status-error sm:col-span-2">
            {{ editNameProblem }}
          </p>
          <div class="flex gap-2 sm:col-span-2">
            <button
              type="submit"
              :disabled="savingEdit || editNameProblem !== null || !editForm.nickname.trim()"
              class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
            >
              {{ savingEdit ? t('common.saving') : t('common.save') }}
            </button>
            <button type="button" class="text-sm text-white/50" @click="cancelEdit">{{ t('common.cancel') }}</button>
          </div>
        </form>
      </li>
    </ul>
    </template>
  </main>
</template>
