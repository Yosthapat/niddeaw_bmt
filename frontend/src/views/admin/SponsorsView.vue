<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import type { LogoPreview, Sponsor } from '@/types'
import { logoHeight } from '@/utils/sponsorBand'
import { MAX_NAME } from '@/utils/limits'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t } = useI18n()
const { confirm } = useConfirmDialog()

const sponsors = ref<Sponsor[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)
const rowError = ref<string | null>(null)
const busyId = ref<string | null>(null)

const shown = computed(() => sponsors.value.filter((s) => s.is_visible))

onMounted(async () => {
  try {
    sponsors.value = await adminApi.getAllSponsors()
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('sponsors.loadFailed'))
  } finally {
    loading.value = false
  }
})

function replace(updated: Sponsor): void {
  sponsors.value = sponsors.value.map((s) => (s.id === updated.id ? updated : s))
}

/** "https://www.instagram.com/match.mellowww" -> "@match.mellowww". */
function linkLabel(href: string | null): string {
  if (!href) return t('sponsors.noLink')
  const ig = href.match(/instagram\.com\/([^/?#]+)/)
  return ig ? `@${ig[1]}` : href.replace(/^https?:\/\/(www\.)?/, '')
}

async function toggle(sponsor: Sponsor): Promise<void> {
  rowError.value = null
  busyId.value = sponsor.id
  try {
    replace(await adminApi.updateSponsor(sponsor.id, { is_visible: !sponsor.is_visible }))
  } catch (e) {
    rowError.value = apiErrorMessage(e, t('sponsors.saveFailed'))
  } finally {
    busyId.value = null
  }
}

// Arrows rather than drag-to-reorder: a drag handle on a phone fights the
// page's own scrolling, and there are only ever a handful of sponsors.
async function move(index: number, by: -1 | 1): Promise<void> {
  const target = index + by
  if (target < 0 || target >= sponsors.value.length) return
  const before = sponsors.value
  const next = [...before]
  ;[next[index], next[target]] = [next[target], next[index]]
  sponsors.value = next
  rowError.value = null
  try {
    sponsors.value = await adminApi.reorderSponsors(next.map((s) => s.id))
  } catch (e) {
    sponsors.value = before
    rowError.value = apiErrorMessage(e, t('sponsors.saveFailed'))
  }
}

// ----------------------------------------------------------- add / edit
// One form for both: `editing` null means a new sponsor.
const formOpen = ref(false)
const editing = ref<Sponsor | null>(null)
const form = reactive({ name: '', href: '' })
const file = ref<File | null>(null)
const original = ref<string | null>(null)
const preview = ref<LogoPreview | null>(null)
const previewing = ref(false)
const saving = ref(false)
const formError = ref<string | null>(null)
const tried = ref(false)

const nameProblem = computed(() => (form.name.trim() ? null : t('sponsors.nameRequired')))
const logoProblem = computed(() => (editing.value || file.value ? null : t('sponsors.logoRequired')))
const linkPreview = computed(() => {
  const raw = form.href.trim()
  if (!raw) return null
  if (raw.startsWith('@') || !raw.includes('.')) return `@${raw.replace(/^@/, '')}`
  return raw.replace(/^https?:\/\/(www\.)?/, '')
})
// The band as it will look after saving: the other visible logos, with
// this one in its place (or on the end, for a new sponsor).
const bandAfter = computed(() => {
  const mine = preview.value
    ? { name: form.name || '?', logo_url: preview.value.data_uri, logo_width: preview.value.width, logo_height: preview.value.height, isNew: true }
    : editing.value
      ? { ...editing.value, isNew: true }
      : null
  const others = shown.value.filter((s) => s.id !== editing.value?.id).map((s) => ({ ...s, isNew: false }))
  if (!mine) return others
  if (!editing.value) return [...others, mine]
  return shown.value.map((s) => (s.id === editing.value?.id ? mine : { ...s, isNew: false }))
})

function openForm(sponsor: Sponsor | null): void {
  editing.value = sponsor
  form.name = sponsor?.name ?? ''
  form.href = sponsor?.href ? linkLabel(sponsor.href) : ''
  file.value = null
  preview.value = null
  if (original.value) URL.revokeObjectURL(original.value)
  original.value = null
  formError.value = null
  tried.value = false
  formOpen.value = true
}

function closeForm(): void {
  formOpen.value = false
  if (original.value) URL.revokeObjectURL(original.value)
  original.value = null
}

async function onFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const picked = input.files?.[0]
  // cleared so choosing the same file again (after an error) still fires
  input.value = ''
  if (!picked) return
  file.value = picked
  if (original.value) URL.revokeObjectURL(original.value)
  original.value = URL.createObjectURL(picked)
  preview.value = null
  formError.value = null
  previewing.value = true
  try {
    preview.value = await adminApi.previewSponsorLogo(picked)
  } catch (e) {
    file.value = null
    formError.value = apiErrorMessage(e, t('sponsors.previewFailed'))
  } finally {
    previewing.value = false
  }
}

async function save(): Promise<void> {
  tried.value = true
  if (nameProblem.value || logoProblem.value) return
  saving.value = true
  formError.value = null
  try {
    if (editing.value) {
      let updated = await adminApi.updateSponsor(editing.value.id, {
        name: form.name.trim(),
        href: form.href.trim() || null,
      })
      if (file.value) updated = await adminApi.replaceSponsorLogo(editing.value.id, file.value)
      replace(updated)
    } else if (file.value) {
      sponsors.value = [...sponsors.value, await adminApi.createSponsor(form.name.trim(), form.href, file.value)]
    }
    closeForm()
  } catch (e) {
    formError.value = apiErrorMessage(e, t('sponsors.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function remove(): Promise<void> {
  const sponsor = editing.value
  if (!sponsor) return
  const ok = await confirm({
    title: t('sponsors.deleteConfirmTitle'),
    message: t('sponsors.deleteConfirm', { name: sponsor.name }),
    danger: true,
  })
  if (!ok) return
  saving.value = true
  try {
    await adminApi.deleteSponsor(sponsor.id)
    sponsors.value = sponsors.value.filter((s) => s.id !== sponsor.id)
    closeForm()
  } catch (e) {
    formError.value = apiErrorMessage(e, t('sponsors.saveFailed'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-2xl px-4 py-6">
    <div class="flex items-end justify-between gap-3">
      <h1 class="font-display text-2xl font-bold">{{ t('sponsors.title') }}</h1>
      <span v-if="!loading" class="text-sm text-white/60">
        {{ t('sponsors.shownCount', { shown: shown.length, total: sponsors.length }) }}
      </span>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <template v-else-if="!formOpen">
      <!-- What the home page shows right now -->
      <p class="mt-5 text-xs text-white/60">{{ t('sponsors.bandPreview') }}</p>
      <div class="sponsor-band mt-2">
        <img
          v-for="s in shown"
          :key="s.id"
          :src="s.logo_url"
          :alt="s.name"
          :width="s.logo_width"
          :height="s.logo_height"
          class="w-auto object-contain"
          :style="{ height: `${Math.round(logoHeight(s) * 0.72)}px` }"
        />
        <span v-if="shown.length === 0" class="text-xs text-white/50">{{ t('sponsors.bandEmpty') }}</span>
      </div>

      <p v-if="sponsors.length > 1" class="mt-4 text-xs text-white/60">{{ t('sponsors.orderHint') }}</p>
      <p v-if="rowError" class="mt-3 text-sm text-status-error" role="alert">{{ rowError }}</p>
      <p v-if="sponsors.length === 0" class="mt-6 text-sm text-white/50">{{ t('sponsors.empty') }}</p>

      <ul class="mt-3 space-y-2">
        <li
          v-for="(s, i) in sponsors"
          :key="s.id"
          class="hud-panel flex items-center gap-2 border border-brand-pink/20 bg-brand-surface p-2 pr-1"
          :class="{ 'opacity-60': !s.is_visible }"
        >
          <div class="flex flex-col">
            <button
              type="button"
              class="flex h-7 w-9 items-center justify-center text-white/50 hover:text-white disabled:opacity-20"
              :disabled="i === 0"
              :aria-label="t('sponsors.moveUp', { name: s.name })"
              @click="move(i, -1)"
            >
              ▲
            </button>
            <button
              type="button"
              class="flex h-7 w-9 items-center justify-center text-white/50 hover:text-white disabled:opacity-20"
              :disabled="i === sponsors.length - 1"
              :aria-label="t('sponsors.moveDown', { name: s.name })"
              @click="move(i, 1)"
            >
              ▼
            </button>
          </div>
          <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-[#140a2b]">
            <img :src="s.logo_url" alt="" class="max-h-10 max-w-11 object-contain" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate font-medium">{{ s.name }}</p>
            <p class="truncate text-xs text-white/60">
              {{ s.is_visible ? linkLabel(s.href) : t('sponsors.hidden') }}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            class="switch"
            :class="{ on: s.is_visible }"
            :aria-checked="s.is_visible"
            :aria-label="t('sponsors.show', { name: s.name })"
            :disabled="busyId === s.id"
            @click="toggle(s)"
          >
            <span />
          </button>
          <button
            type="button"
            class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-white/75 hover:bg-white/5"
            :aria-label="t('sponsors.edit', { name: s.name })"
            @click="openForm(s)"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4" />
            </svg>
          </button>
        </li>
      </ul>

      <button
        type="button"
        class="tap mt-6 w-full rounded-full bg-brand-pink px-4 font-semibold text-brand-black"
        @click="openForm(null)"
      >
        + {{ t('sponsors.add') }}
      </button>
    </template>

    <!-- Add / edit -->
    <form v-else class="mt-5 space-y-5" novalidate @submit.prevent="save">
      <h2 class="text-lg font-semibold">
        {{ editing ? t('sponsors.editTitle', { name: editing.name }) : t('sponsors.addTitle') }}
      </h2>

      <div>
        <p class="text-sm text-white/70">{{ t('sponsors.logo') }}</p>
        <div class="mt-2 grid grid-cols-2 gap-3">
          <div class="flex flex-col items-center gap-1">
            <div class="logo-well bg-white">
              <img v-if="original" :src="original" alt="" class="max-h-full max-w-full object-contain" />
              <img v-else-if="editing" :src="editing.logo_url" alt="" class="max-h-full max-w-full object-contain invert" />
            </div>
            <span class="text-xs text-white/50">{{ t('sponsors.uploaded') }}</span>
          </div>
          <div class="flex flex-col items-center gap-1">
            <div class="logo-well bg-[#140a2b]">
              <span v-if="previewing" class="text-xs text-white/60">{{ t('sponsors.processing') }}</span>
              <img v-else-if="preview" :src="preview.data_uri" alt="" class="max-h-full max-w-full object-contain" />
              <img v-else-if="editing" :src="editing.logo_url" alt="" class="max-h-full max-w-full object-contain" />
            </div>
            <span class="text-xs text-white/50">{{ t('sponsors.onSite') }}</span>
          </div>
        </div>
        <p class="mt-2 text-xs text-white/50">{{ t('sponsors.whitenHint') }}</p>
        <label class="tap mt-2 w-full cursor-pointer rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink">
          {{ file || editing ? t('sponsors.changeLogo') : t('sponsors.pickLogo') }}
          <input type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" @change="onFile" />
        </label>
        <p v-if="tried && logoProblem" class="mt-1 text-xs text-status-error">{{ logoProblem }}</p>
      </div>

      <label class="flex flex-col gap-1 text-sm text-white/70">
        {{ t('sponsors.name') }}
        <input
          v-model="form.name"
          :maxlength="MAX_NAME"
          :aria-invalid="tried && !!nameProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white"
        />
        <span v-if="tried && nameProblem" class="text-xs text-status-error">{{ nameProblem }}</span>
      </label>

      <label class="flex flex-col gap-1 text-sm text-white/70">
        {{ t('sponsors.link') }}
        <input
          v-model="form.href"
          :placeholder="t('sponsors.linkPlaceholder')"
          autocapitalize="off"
          autocomplete="off"
          inputmode="url"
          maxlength="300"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-white"
        />
        <span v-if="linkPreview" class="text-xs text-white/50">{{ t('sponsors.linkGoesTo', { where: linkPreview }) }}</span>
      </label>

      <div>
        <p class="text-xs text-white/60">{{ t('sponsors.bandPreview') }}</p>
        <div class="sponsor-band mt-2">
          <img
            v-for="s in bandAfter"
            :key="s.logo_url"
            :src="s.logo_url"
            alt=""
            class="w-auto object-contain"
            :class="{ 'is-new': s.isNew }"
            :style="{ height: `${Math.round(logoHeight(s) * 0.72)}px` }"
          />
        </div>
      </div>

      <p v-if="formError" class="text-sm text-status-error" role="alert">{{ formError }}</p>

      <div class="flex flex-wrap gap-2">
        <button
          type="submit"
          :disabled="saving || previewing"
          class="tap flex-1 rounded-full bg-brand-pink px-5 font-semibold text-brand-black disabled:opacity-50"
        >
          {{ saving ? t('common.saving') : editing ? t('sponsors.save') : t('sponsors.saveNew') }}
        </button>
        <button type="button" class="tap rounded-full border border-white/20 px-5 text-sm text-white/60" @click="closeForm">
          {{ t('common.cancel') }}
        </button>
      </div>
      <button
        v-if="editing"
        type="button"
        :disabled="saving"
        class="tap w-full rounded-full bg-status-error/15 px-4 text-sm font-semibold text-status-error disabled:opacity-50"
        @click="remove"
      >
        {{ t('sponsors.delete') }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.sponsor-band {
  display: flex;
  min-height: 4rem;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-around;
  gap: 0.75rem 1rem;
  padding: 0.75rem;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 0.875rem;
  background: linear-gradient(90deg, #2a0f45, #140a2b 50%, #2a0f45);
}
.sponsor-band .is-new {
  filter: drop-shadow(0 0 6px rgb(234 76 164 / 0.9));
}
.logo-well {
  display: flex;
  width: 100%;
  aspect-ratio: 4 / 3;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 0.75rem;
}
.switch {
  position: relative;
  width: 48px;
  height: 28px;
  flex: none;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.18);
  transition: background 0.2s;
}
/* a 44px target around the 28px track */
.switch::after {
  content: '';
  position: absolute;
  inset: -8px -2px;
}
.switch.on {
  background: var(--color-brand-pink);
}
.switch span {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgb(0 0 0 / 0.4);
  transition: left 0.2s;
}
.switch.on span {
  left: 23px;
}
</style>
