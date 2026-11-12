<script setup lang="ts">
/**
 * What the QR on a slip said, for the admin deciding on it:
 * ✅ new (and which bank it came from), ⛔ the same slip was used before
 * (on what, by whom), ⚠️ no QR or not a slip's QR. A check, not a verdict:
 * the admin still approves or refuses.
 */
import { computed, watch, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { SlipKind, SlipCheck } from '@/api/admin'
import { useSlipCheck } from '@/composables/useSlipChecks'
import { formatDateTime, money } from '@/utils/format'
import type { Locale } from '@/i18n'

const props = withDefaults(defineProps<{ kind: SlipKind; targetId: string; slipUrl: string; detail?: boolean }>(), { detail: true })
const { t, locale } = useI18n()

const check = ref<SlipCheck | null>(null)
watch(
  () => [props.kind, props.targetId, props.slipUrl] as const,
  ([k, id, url], _, onCleanup) => {
    const r = useSlipCheck(k, id, url)
    check.value = r.value
    const stop = watch(r, (v) => (check.value = v))
    onCleanup(stop)
  },
  { immediate: true },
)

// The Bank of Thailand's bank codes, as they appear in a slip's QR.
const BANKS: Record<string, string> = {
  '002': 'กรุงเทพ', '004': 'กสิกร', '006': 'กรุงไทย', '011': 'ttb', '014': 'ไทยพาณิชย์', '017': 'Citi',
  '022': 'CIMB', '024': 'UOB', '025': 'กรุงศรี', '030': 'ออมสิน', '033': 'ธอส.', '034': 'ธ.ก.ส.',
  '066': 'อิสลาม', '067': 'ทิสโก้', '069': 'เกียรตินาคิน', '070': 'ICBC', '071': 'ไทยเครดิต', '073': 'LH Bank',
}
const bank = computed(() => (check.value?.bank ? (BANKS[check.value.bank] ?? check.value.bank) : null))
const before = computed(() => {
  const u = check.value?.used_before
  if (!u) return ''
  if (u.gone) return t('slipCheck.beforeGone', { what: t(`slipCheck.kind.${u.kind}`) })
  return t('slipCheck.before', {
    what: t(`slipCheck.kind.${u.kind}`),
    who: u.who ?? '?',
    when: u.when ? formatDateTime(u.when, locale.value as Locale) : '',
    amount: u.amount != null ? money(u.amount) : '',
  })
})
</script>

<template>
  <div v-if="check" class="slip-check" :class="check.status" role="status">
    <p class="pill">
      <template v-if="check.status === 'ok'">✅ {{ t('slipCheck.ok') }}<template v-if="bank"> · {{ bank }}</template></template>
      <template v-else-if="check.status === 'duplicate'">⛔ {{ t('slipCheck.duplicate') }}</template>
      <template v-else-if="check.status === 'no_qr'">⚠️ {{ t('slipCheck.noQr') }}</template>
      <template v-else-if="check.status === 'not_slip'">⚠️ {{ t('slipCheck.notSlip') }}</template>
      <template v-else>{{ t('slipCheck.unchecked') }}</template>
    </p>
    <p v-if="detail && check.status === 'duplicate'" class="why">
      {{ before }}<template v-if="check.used_count > 1"> · {{ t('slipCheck.more', { n: check.used_count - 1 }) }}</template>
    </p>
    <p v-else-if="detail && check.status === 'no_qr'" class="why">{{ t('slipCheck.noQrHint') }}</p>
  </div>
</template>

<style scoped>
.slip-check {
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
}
.pill {
  align-self: flex-start;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.why {
  font-size: 12px;
  line-height: 1.4;
}
.ok .pill {
  background: rgb(127 240 180 / 0.14);
  color: #7ff0b4;
}
.duplicate .pill {
  background: rgb(255 77 109 / 0.2);
  color: #ff9db0;
  box-shadow: inset 0 0 0 1px rgb(255 77 109 / 0.55);
}
.duplicate .why {
  color: #ffb3c1;
}
.no_qr .pill,
.not_slip .pill {
  background: rgb(255 211 77 / 0.16);
  color: #ffd34d;
}
.no_qr .why {
  color: rgb(255 255 255 / 0.55);
}
.unchecked .pill {
  background: rgb(255 255 255 / 0.08);
  color: rgb(255 255 255 / 0.55);
}
</style>
