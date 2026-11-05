<script setup lang="ts">
/**
 * The club's LINE link as a QR card, for members who haven't linked yet:
 * show it at the court, or copy the link into the group chat. Scanning
 * opens LINE at /line, where they pick their own name; the admin then
 * confirms it under "คำขอผูก LINE" on the members page.
 *
 * Unlike tonight's check-in QR this one never changes and can be shared:
 * linking still needs the admin to say yes.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { LineInvite } from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import BrandQr from '@/components/common/BrandQr.vue'

defineProps<{ linked: number; total: number }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()

const invite = ref<LineInvite | null>(null)
const problem = ref('')
const copied = ref(false)

async function copy(): Promise<void> {
  if (!invite.value) return
  try {
    await navigator.clipboard.writeText(invite.value.url)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    problem.value = invite.value.url
  }
}

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    invite.value = await adminApi.getLineInvite()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineInvite.loadFailed'))
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div
    class="fixed inset-0 z-40 overflow-y-auto bg-[#12081f]/95 backdrop-blur-md"
    role="dialog"
    aria-modal="true"
    :aria-label="t('lineInvite.title')"
  >
    <div class="mx-auto flex min-h-full max-w-md flex-col items-center gap-4 px-5 pt-6 pb-10 text-center">
      <div class="flex w-full justify-end">
        <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/70" @click="emit('close')">
          {{ t('admin.close') }}
        </button>
      </div>
      <p class="world-eyebrow text-[#7ff0b4]">LINE</p>
      <h2 class="world-title text-3xl">{{ t('lineInvite.title') }}</h2>
      <p class="text-sm text-white/70">{{ t('lineInvite.sub', { n: linked, total }) }}</p>

      <BrandQr v-if="invite" :modules="invite.qr_modules" :caption="t('lineInvite.caption')" :alt="t('lineInvite.title')" saveable file-name="niddeaw-line.png" class="mt-1 w-[min(300px,74vw)]" />
      <div v-else class="flex h-[min(300px,72vw)] w-[min(300px,72vw)] items-center justify-center rounded-3xl bg-[#f4a6c8]/30 text-sm text-white/70">
        {{ problem || t('common.loading') }}
      </div>

      <ol class="w-full space-y-2 text-left text-sm">
        <li v-for="(step, i) in [t('lineInvite.step1'), t('lineInvite.step2'), t('lineInvite.step3')]" :key="i" class="flex items-start gap-3 rounded-2xl bg-white/[0.06] px-4 py-3">
          <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#06c755] text-xs font-bold text-white">{{ i + 1 }}</span>
          <span class="text-white/85">{{ step }}</span>
        </li>
      </ol>

      <button
        v-if="invite"
        type="button"
        class="tap w-full rounded-full border border-[#06c755]/60 px-5 text-sm font-semibold text-[#7ff0b4]"
        @click="copy"
      >
        {{ copied ? t('lineInvite.copied') : t('lineInvite.copy') }}
      </button>
      <p v-if="problem && invite" class="break-all text-xs text-white/60">{{ problem }}</p>
    </div>
  </div>
</template>
