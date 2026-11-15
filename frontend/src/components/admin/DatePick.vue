<script setup lang="ts">
/**
 * A day (and, if asked, a time) picked without typing a digit.
 *
 * The browser's own date field on a desktop is a row of mm/dd/yyyy blanks to
 * type into, in the browser's language, with a calendar button too faint to
 * see on this dark theme. Here the whole field is the button: a tap anywhere
 * opens the calendar (on a phone, the phone's own wheel), the chosen day reads
 * in the page's language with its weekday, the time is a list to pick from,
 * and the likely answers sit underneath as one-tap chips.
 *
 * The value is the native one, so callers keep what they had:
 * "YYYY-MM-DD" for a day, "YYYY-MM-DDTHH:mm" (device time) with a time.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

export interface QuickPick {
  label: string
  value: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    withTime?: boolean
    placeholder?: string
    /** What a newly picked day gets as its time. */
    defaultTime?: string
    quick?: QuickPick[]
    ariaLabel?: string
  }>(),
  { withTime: false, placeholder: '', defaultTime: '20:00', quick: () => [], ariaLabel: undefined },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const { locale } = useI18n()
const native = ref<HTMLInputElement | null>(null)

const day = computed(() => props.modelValue.slice(0, 10))
const time = computed(() => (props.withTime ? props.modelValue.slice(11, 16) : ''))

const shown = computed(() => {
  if (!day.value) return ''
  const [y, m, d] = day.value.split('-').map(Number)
  return new Intl.DateTimeFormat(locale.value === 'th' ? 'th-TH' : 'en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(y, m - 1, d))
})

/** Every half hour through the day, and a minute to midnight for a deadline. */
const times = computed(() => {
  const out: string[] = []
  for (let h = 6; h < 24; h++) for (const m of ['00', '30']) out.push(`${String(h).padStart(2, '0')}:${m}`)
  out.push('23:59')
  if (time.value && !out.includes(time.value)) out.push(time.value)
  return out.sort()
})

function openCalendar(): void {
  // Chrome and Edge open the calendar on any click this way; a phone opens
  // its own picker from the tap itself, and an older browser at least lands
  // in the field.
  try {
    native.value?.showPicker()
  } catch {
    native.value?.focus()
  }
}

function onDay(event: Event): void {
  const picked = (event.target as HTMLInputElement).value
  if (!picked) return
  emit('update:modelValue', props.withTime ? `${picked}T${time.value || props.defaultTime}` : picked)
}

function onTime(event: Event): void {
  if (!day.value) return
  emit('update:modelValue', `${day.value}T${(event.target as HTMLSelectElement).value}`)
}
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex gap-2">
      <span class="relative flex min-h-11 flex-1 items-center gap-2 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 text-sm">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" class="h-[18px] w-[18px] shrink-0 text-brand-pink" aria-hidden="true">
          <rect x="3" y="4.5" width="18" height="16.5" rx="2.5" /><path d="M3 9.5h18M8 3v3M16 3v3" />
        </svg>
        <span :class="shown ? 'font-medium text-white' : 'text-white/40'">{{ shown || placeholder }}</span>
        <!-- The real field, unseen, over the whole box: a tap anywhere is a tap on it. -->
        <input
          ref="native"
          type="date"
          :value="day"
          :aria-label="ariaLabel"
          class="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          @click="openCalendar"
          @change="onDay"
        />
      </span>
      <select
        v-if="withTime"
        :value="time"
        :disabled="!day"
        :aria-label="ariaLabel"
        class="min-h-11 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 text-sm text-white disabled:opacity-40"
        @change="onTime"
      >
        <option v-if="!time" value="" disabled>--:--</option>
        <option v-for="x in times" :key="x" :value="x">{{ x }}</option>
      </select>
    </div>
    <div v-if="quick.length" class="flex flex-wrap gap-1.5">
      <button
        v-for="q in quick"
        :key="q.label"
        type="button"
        class="min-h-9 rounded-full border px-3 text-xs"
        :class="q.value === modelValue ? 'border-brand-pink bg-brand-pink/20 font-semibold text-white' : 'border-white/15 text-white/70 hover:border-white/30'"
        :aria-pressed="q.value === modelValue"
        @click="emit('update:modelValue', q.value)"
      >
        {{ q.label }}
      </button>
    </div>
  </div>
</template>
