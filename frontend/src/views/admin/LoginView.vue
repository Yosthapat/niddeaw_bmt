<script setup lang="ts">
// The backend sleeps (Render free tier, see .github/workflows/keep-alive.yml),
// so the first login of the day can sit there for the better part of a
// minute through no fault of the admin's. A disabled button and a changed
// label don't carry that: nothing on screen moves, and the page reads as
// frozen. This waits behind an overlay that visibly counts, says *why* it
// is slow once the wait stops being ordinary, and gives up at a stated
// deadline instead of hanging until the browser does.
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { LOGIN_TIMEOUT_MS, login } from '@/api/admin'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

// Wrong credentials come back in well under a second, and throwing a
// full-screen overlay up for that would strobe. The button's disabled
// state covers the first moment; the overlay only takes over once the
// wait is real.
const OVERLAY_AFTER_MS = 300
// Past this the caption stops claiming to be mid-login and admits the
// wait is longer than usual. What it must not do is explain why: the
// admin can't act on how the backend is hosted, and telling them the
// server was asleep only makes the club's site sound rickety. Saying
// "still working, nothing is stuck" is the part that actually helps.
const SLOW_AFTER_MS = 8000
const TIMEOUT_SECONDS = Math.round(LOGIN_TIMEOUT_MS / 1000)

const { t } = useI18n()
const username = ref('')
const password = ref('')
const loading = ref(false)
const waiting = ref(false)
const elapsedMs = ref(0)
const error = ref<string | null>(null)

const elapsed = computed(() => Math.floor(elapsedMs.value / 1000))
const slow = computed(() => elapsedMs.value >= SLOW_AFTER_MS)
// Honest because the wait really does end at LOGIN_TIMEOUT_MS: the bar is
// how much of that budget is spent, not a guess at how far along a request
// of unknown length is.
const progress = computed(() => Math.min(100, (elapsedMs.value / LOGIN_TIMEOUT_MS) * 100))

const authStore = useAuthStore()
const router = useRouter()

let startedAt = 0
let overlayTimer: ReturnType<typeof setTimeout> | undefined
let ticker: ReturnType<typeof setInterval> | undefined

function stopWaiting(): void {
  clearTimeout(overlayTimer)
  clearInterval(ticker)
  overlayTimer = undefined
  ticker = undefined
  waiting.value = false
  document.body.style.overflow = ''
}

// Covers the success path too: the route change unmounts this view while
// the overlay is deliberately still up, and the scroll lock has to come
// off with it.
onBeforeUnmount(stopWaiting)

async function submit(): Promise<void> {
  loading.value = true
  error.value = null
  elapsedMs.value = 0
  startedAt = performance.now()
  overlayTimer = setTimeout(() => {
    waiting.value = true
    // Same scroll lock ConfirmDialog takes while it owns the screen.
    document.body.style.overflow = 'hidden'
  }, OVERLAY_AFTER_MS)
  // Four times a second so the bar slides rather than steps; the caption
  // still reads whole seconds.
  ticker = setInterval(() => {
    elapsedMs.value = performance.now() - startedAt
  }, 250)

  try {
    const { access_token } = await login({ username: username.value, password: password.value })
    authStore.login(access_token)
    // Awaited, and `loading` is deliberately left set: clearing either
    // before the route swaps would drop the overlay and flash a bare login
    // form for a frame on the way to the dashboard.
    await router.push('/admin')
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      error.value = t('login.invalidCredentials')
    } else if (e instanceof ApiError && e.status === 408) {
      error.value = t('login.timedOut', { seconds: TIMEOUT_SECONDS })
    } else {
      error.value = t('login.failed')
    }
    loading.value = false
    stopWaiting()
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-sm flex-col px-4 py-12 sm:py-16">
    <div class="hud-panel glass-panel border border-brand-pink/25 px-6 py-8">
      <div class="flex flex-col items-center gap-3">
        <span class="hud-panel bg-brand-pink p-0.5">
          <img
            src="/pwa-icons/pwa-64x64.png"
            alt="นิดเดียว Badminton Club logo"
            class="hud-panel block h-10 w-10"
          />
        </span>
        <div class="text-center">
          <h1 class="font-display text-xl font-bold text-brand-pink">{{ t('login.title') }}</h1>
          <p class="mt-1 text-xs tracking-wide text-white/40 uppercase">{{ t('login.subtitle') }}</p>
        </div>
      </div>

      <form class="mt-7 flex flex-col gap-4" @submit.prevent="submit">
        <label class="flex flex-col gap-1.5">
          <span class="text-[11px] tracking-wide text-white/45 uppercase">{{ t('login.username') }}</span>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            required
            :disabled="loading"
            class="hud-panel border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink disabled:opacity-50"
          />
        </label>
        <label class="flex flex-col gap-1.5">
          <span class="text-[11px] tracking-wide text-white/45 uppercase">{{ t('login.password') }}</span>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            :disabled="loading"
            class="hud-panel border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink disabled:opacity-50"
          />
        </label>
        <p v-if="error" class="text-sm text-status-error">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="hud-panel hud-hover mt-1 bg-brand-pink px-3 py-2.5 font-semibold text-brand-black disabled:opacity-50"
        >
          {{ loading ? t('login.loggingIn') : t('login.submit') }}
        </button>
      </form>
    </div>

    <!-- Teleported so the backdrop covers the header too, and the blur
         isn't trapped inside <main>'s stacking context. -->
    <Teleport to="body">
      <Transition name="wait-fade">
        <div
          v-if="waiting"
          class="fixed inset-0 z-50 flex items-center justify-center bg-brand-black/85 px-4 backdrop-blur-sm"
        >
          <!-- A status, not a dialog: there is nothing here to interact
               with, so it announces itself politely rather than trapping
               focus the way ConfirmDialog has to. -->
          <div
            role="status"
            aria-live="polite"
            class="hud-panel glass-panel w-full max-w-xs border border-brand-pink/30 px-6 py-7 text-center"
          >
            <div class="relative mx-auto h-20 w-20">
              <svg class="spin-ring absolute inset-0 h-20 w-20" viewBox="0 0 80 80" aria-hidden="true">
                <circle cx="40" cy="40" r="36" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-pink/15" />
                <!-- ~2πr = 226, so a 56-long dash is a quarter of the ring. -->
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  class="ring-arc text-brand-pink"
                />
              </svg>
              <!-- The same shuttlecock the home page counts matches with. -->
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="shuttle absolute inset-0 m-auto h-9 w-9 text-brand-pink-light"
                aria-hidden="true"
              >
                <path d="M5.6 6.2Q12 3.4 18.4 6.2" />
                <path d="M5.6 6.2 8.4 13.2" />
                <path d="M18.4 6.2 15.6 13.2" />
                <path d="M12 4.3V13.2" />
                <path d="M8.4 13.2h7.2" />
                <circle cx="12" cy="17" r="3.4" />
              </svg>
            </div>

            <p class="mt-5 font-display text-base font-bold text-white">
              {{ slow ? t('login.stillWorking') : t('login.loggingIn') }}
            </p>
            <p v-if="slow" class="mt-2 text-xs leading-relaxed text-white/55">
              {{ t('login.stillWorkingHint') }}
            </p>

            <!-- The proof that nothing is stuck. Everything else on this
                 panel could be a frozen frame; a number that keeps moving
                 cannot be. -->
            <p class="mt-3 text-xs tabular-nums text-brand-pink/70">
              {{ t('login.elapsed', { seconds: elapsed }) }}
            </p>
            <div class="mt-3 h-1 w-full overflow-hidden rounded-full bg-white/10">
              <div
                class="h-full rounded-full bg-brand-pink transition-[width] duration-300 ease-linear"
                :style="{ width: `${progress}%` }"
              />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </main>
</template>

<style scoped>
.wait-fade-enter-active,
.wait-fade-leave-active {
  transition: opacity 0.2s ease;
}

.wait-fade-enter-from,
.wait-fade-leave-to {
  opacity: 0;
}

.ring-arc {
  stroke-dasharray: 56 170;
}

.spin-ring {
  animation: login-spin 1.4s linear infinite;
}

.shuttle {
  animation: login-bob 1.8s ease-in-out infinite;
}

@keyframes login-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes login-bob {
  50% {
    transform: translateY(-3px) rotate(-8deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spin-ring,
  .shuttle {
    animation: none;
  }
  /* A quarter-arc frozen mid-rotation reads as a stalled spinner, so the
     ring closes into a plain dim circle instead. The counter below is
     still ticking, and it is the part that says this is alive. */
  .ring-arc {
    stroke-dasharray: none;
    opacity: 0.45;
  }
}
</style>
