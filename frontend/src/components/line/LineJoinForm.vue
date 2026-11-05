<script setup lang="ts">
/**
 * Signing up from inside LINE, for someone not in the club yet. What they
 * send is an application: an admin takes them in (and sets their starting
 * tier) from Manage members, and only then are they a member.
 *
 * The nickname follows the club's rules as they type (utils/nickname.ts),
 * checked against everyone already in the club, so the API's answer is
 * rarely a surprise. Their LINE picture is the photo unless they pick one.
 */
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { JoinApplication, LineStatus, LinkOption } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { nicknameProblem, tidyNicknameCase } from '@/utils/nickname'
import { AVATAR_DIMENSION, compressImage } from '@/utils/imageCompression'
import { MAX_HANDLE, MAX_NOTE } from '@/utils/limits'

const props = defineProps<{
  token: string
  lineName: string
  linePicture: string | null
  application: JoinApplication | null
  members: LinkOption[]
}>()
const emit = defineEmits<{ sent: [status: LineStatus, warning: string]; back: [] }>()
const { t } = useI18n()

const app = props.application
const form = reactive({
  nickname: app?.nickname ?? '',
  hand: (app?.dominant_hand ?? 'right') as 'left' | 'right',
  instagram: app?.instagram ?? '',
  tiktok: app?.tiktok ?? '',
  quote: app?.quote ?? '',
})

// Which photo goes with the application: their LINE picture, the one
// already on the application they are editing, or a new one they picked.
type PhotoChoice = 'line' | 'keep' | 'new'
const choice = ref<PhotoChoice>(app?.photo_url ? 'keep' : 'line')
const file = ref<File | null>(null)
const preview = ref<string | null>(null)

function revoke(): void {
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = null
}
onBeforeUnmount(revoke)

async function pickPhoto(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const picked = input.files?.[0]
  input.value = ''
  if (!picked) return
  file.value = await compressImage(picked, AVATAR_DIMENSION)
  revoke()
  preview.value = URL.createObjectURL(file.value)
  choice.value = 'new'
}

function useLinePhoto(): void {
  revoke()
  file.value = null
  choice.value = 'line'
}

const photo = computed(() => {
  if (choice.value === 'new') return preview.value
  if (choice.value === 'keep') return app?.photo_url ?? null
  return props.linePicture
})

const initials = computed(() =>
  (form.nickname || props.lineName)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join(''),
)

const touched = ref(false)
// However they type it, the name is kept as a capital then small letters
// ("VAAN" → "Vaan"); the rules and the clash check look at that.
const tidied = computed(() => tidyNicknameCase(form.nickname))
const nameProblem = computed((): string | null => {
  if (!form.nickname.trim()) return touched.value ? t('members.nicknameEmpty') : null
  const problem = nicknameProblem(tidied.value)
  if (problem) return t(`members.nickname${problem[0].toUpperCase()}${problem.slice(1)}`)
  const name = tidied.value.toLowerCase()
  return props.members.some((m) => m.nickname.toLowerCase() === name) ? t('members.nicknameTaken') : null
})
function tidyName(): void {
  touched.value = true
  if (form.nickname.trim()) form.nickname = tidied.value
}
const nameOk = computed(() => form.nickname.trim() !== '' && nameProblem.value === null)

const sending = ref(false)
const problem = ref('')

async function submit(): Promise<void> {
  touched.value = true
  if (!nameOk.value || sending.value) return
  sending.value = true
  problem.value = ''
  try {
    let status = await lineApi.sendJoin(props.token, {
      nickname: tidied.value,
      dominant_hand: form.hand,
      instagram: form.instagram.trim() || null,
      tiktok: form.tiktok.trim() || null,
      quote: form.quote.trim() || null,
      use_line_photo: choice.value === 'line',
    })
    let warning = ''
    if (choice.value === 'new' && file.value) {
      try {
        status = await lineApi.uploadJoinPhoto(props.token, file.value)
      } catch (e) {
        // The application went through; only the photo didn't.
        warning = apiErrorMessage(e, t('lineJoin.photoFailed'))
      }
    }
    emit('sent', status, warning)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineJoin.sendFailed'))
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <form class="flex flex-1 flex-col gap-4" novalidate @submit.prevent="submit">
    <div>
      <p class="world-eyebrow">JOIN</p>
      <h1 class="world-title mt-1 text-2xl">{{ t('lineJoin.title') }}</h1>
      <p class="mt-1 text-sm text-white/70">{{ t('lineJoin.body') }}</p>
    </div>

    <div class="flex items-center gap-4">
      <span class="relative mb-2 shrink-0">
        <span class="photo-ring flex h-[88px] w-[88px] items-center justify-center overflow-hidden rounded-full bg-white/10">
          <img v-if="photo" :src="photo" alt="" class="h-full w-full object-cover" />
          <span v-else class="font-display text-2xl font-bold">{{ initials }}</span>
        </span>
        <span
          class="absolute -bottom-2.5 left-1/2 -translate-x-1/2 rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap shadow"
          :class="choice === 'line' ? 'bg-[#06c755] text-white' : 'bg-brand-pink text-brand-black'"
        >
          {{ choice === 'line' ? t('lineJoin.photoLine') : t('lineJoin.photoOwn') }}
        </span>
      </span>
      <span class="flex flex-wrap gap-2">
        <label class="glass-pill cursor-pointer">
          {{ t('lineJoin.changePhoto') }}
          <input type="file" accept="image/*" class="sr-only" @change="pickPhoto" />
        </label>
        <button v-if="choice !== 'line' && linePicture" type="button" class="glass-pill" @click="useLinePhoto">
          {{ t('lineJoin.useLinePhoto') }}
        </button>
      </span>
    </div>

    <label class="field">
      <span>{{ t('lineJoin.nickname') }}</span>
      <input
        v-model="form.nickname"
        type="text"
        maxlength="40"
        autocapitalize="words"
        autocomplete="nickname"
        :placeholder="t('lineJoin.nicknamePlaceholder')"
        :aria-invalid="!!nameProblem"
        class="inp"
        :class="nameProblem ? 'bad' : nameOk ? 'good' : ''"
        @blur="tidyName"
      />
      <span v-if="nameProblem" class="text-xs text-status-error" role="alert">{{ nameProblem }}</span>
      <span v-else-if="nameOk" class="text-xs text-[#7dffb0]">
        {{ t('lineJoin.nicknameFree') }}<template v-if="tidied !== form.nickname"> · {{ t('lineJoin.nicknameSavedAs', { name: tidied }) }}</template>
      </span>
      <span v-else class="text-xs text-white/55">{{ t('lineJoin.nicknameRule') }}</span>
    </label>

    <div class="field">
      <span>{{ t('lineJoin.hand') }}</span>
      <div class="seg self-start" role="radiogroup" :aria-label="t('lineJoin.hand')">
        <button type="button" role="radio" class="seg-btn" :class="{ on: form.hand === 'right' }" :aria-checked="form.hand === 'right'" @click="form.hand = 'right'">
          {{ t('lineJoin.right') }}
        </button>
        <button type="button" role="radio" class="seg-btn" :class="{ on: form.hand === 'left' }" :aria-checked="form.hand === 'left'" @click="form.hand = 'left'">
          {{ t('lineJoin.left') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <label class="field">
        <span>Instagram</span>
        <input v-model="form.instagram" type="text" :maxlength="MAX_HANDLE" placeholder="@" autocapitalize="off" class="inp" />
      </label>
      <label class="field">
        <span>TikTok</span>
        <input v-model="form.tiktok" type="text" :maxlength="MAX_HANDLE" placeholder="@" autocapitalize="off" class="inp" />
      </label>
    </div>

    <label class="field">
      <span>{{ t('lineJoin.quote') }}</span>
      <input v-model="form.quote" type="text" :maxlength="MAX_NOTE" :placeholder="t('lineJoin.quotePlaceholder')" class="inp" />
    </label>

    <p class="text-xs text-white/55">{{ t('lineJoin.tierNote') }}</p>

    <div class="sticky bottom-0 mt-auto flex flex-col gap-2 bg-gradient-to-t from-[#0b0518] via-[#0b0518]/95 to-transparent pt-4 pb-1">
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <button type="submit" class="cta min-h-14 rounded-2xl font-display text-base font-bold" :disabled="sending || (touched && !nameOk)">
        {{ sending ? t('lineJoin.sending') : application ? t('lineJoin.resend') : t('lineJoin.send') }}
      </button>
      <button type="button" class="min-h-11 text-sm text-white/65 underline-offset-4 hover:underline" @click="emit('back')">
        {{ t('lineJoin.back') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.photo-ring {
  box-shadow:
    0 0 0 3px #ff8fd0,
    0 0 24px rgb(234 76 164 / 0.45);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  color: rgb(255 255 255 / 0.8);
}
.inp {
  min-height: 48px;
  border-radius: 14px;
  border: 1px solid rgb(255 255 255 / 0.2);
  background: rgb(255 255 255 / 0.08);
  padding: 0 14px;
  font-size: 16px;
  color: #fff;
  outline: none;
}
.inp::placeholder {
  color: rgb(255 255 255 / 0.4);
}
.inp:focus {
  border-color: #ff8fd0;
}
.inp.bad {
  border-color: #ff6b8a;
}
.inp.good {
  border-color: rgb(127 240 180 / 0.6);
}
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
.cta:disabled {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
