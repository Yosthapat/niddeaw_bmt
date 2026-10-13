<script setup lang="ts">
/**
 * A native date or month input that reads in the language the rest of the
 * screen is in.
 *
 * The browser draws `<input type="date">` in its *own* locale, not the
 * page's, so on a Thai admin's laptop the activity log asked for a day as
 * `mm/dd/yyyy` — American order, English, three Thai controls away — and
 * the expenses month picker said "October 2026" directly above a row dated
 * "13 ต.ค. 2569". Neither can be fixed with an attribute; `lang` on the
 * element does not move it.
 *
 * So the native control stays (it is the only free picker, and the one the
 * phone already knows how to open) and its own text is made transparent,
 * with the formatted value drawn over the top. The overlay never takes a
 * click, so the whole field — including the browser's calendar button —
 * still behaves exactly as the native one did.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate, formatMonth } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    modelValue: string
    type?: 'date' | 'month'
    placeholder?: string
    ariaLabel?: string
  }>(),
  { type: 'date', placeholder: '', ariaLabel: undefined },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const { locale } = useI18n()

const display = computed(() => {
  if (!props.modelValue) return props.placeholder
  return props.type === 'month'
    ? formatMonth(props.modelValue, locale.value)
    : formatDate(props.modelValue, locale.value)
})

function onInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <span class="localised-date relative inline-flex items-center">
    <input
      :type="type"
      :value="modelValue"
      :aria-label="ariaLabel"
      class="min-h-11 w-full rounded-lg border border-brand-pink/25 bg-brand-black pr-9 pl-3 text-sm"
      @input="onInput"
    />
    <!-- Reads the value out of the input it covers, so it cannot drift from
         what the field actually holds. -->
    <span
      class="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm"
      :class="modelValue ? 'text-white' : 'text-white/40'"
    >
      {{ display }}
    </span>
  </span>
</template>

<style scoped>
/* Both properties: `color` alone leaves the value visible in WebKit, which
   is the browser most of this club is on. The calendar button is drawn by
   the browser in its own colours and is unaffected. */
.localised-date input {
  color: transparent;
  -webkit-text-fill-color: transparent;
}
.localised-date input::-webkit-calendar-picker-indicator {
  filter: invert(1);
  opacity: 0.55;
}
</style>
