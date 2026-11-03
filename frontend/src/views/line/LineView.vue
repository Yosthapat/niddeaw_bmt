<script setup lang="ts">
/**
 * What the club's LINE Official Account opens (a LIFF app): the member is
 * signed in by LINE, and links that LINE account to their name in the club.
 *
 * They pick a name; an admin confirms it at the court (ManageMembersView's
 * LineLinkPanel). Until then nothing is linked, so nobody can claim someone
 * else. Once linked, this page is where check-in and bills will live.
 *
 * Who they are comes from LINE, never from the page: the ID token LIFF
 * gives is checked by our backend with LINE before it believes it.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineCheckinState, LineStatus, LineTonight, LinkOption } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { closeLiff, liffCanScan, liffIdToken, liffScanCheckinCode, liffSignInAgain, liffSignedIn } from '@/composables/useLiff'
import { ApiError } from '@/api/client'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import LineJoinForm from '@/components/line/LineJoinForm.vue'
import LineCheckin from '@/components/line/LineCheckin.vue'
import LineCheckout from '@/components/line/LineCheckout.vue'
import LineBills from '@/components/line/LineBills.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

type Phase = 'loading' | 'off' | 'error' | 'ready'
const phase = ref<Phase>('loading')
const problem = ref('')
const token = ref('')
const me = ref<LineStatus | null>(null)
const options = ref<LinkOption[]>([])
const query = ref('')
const picked = ref<string | null>(null)
const sending = ref(false)
const actionError = ref('')
// The sign-up form is open. The OA's "สมัครสมาชิก" button opens
// /line/register (the LIFF URL with /register on the end), straight to it.
const joining = ref(false)
const joinWarning = ref('')
// Tonight's QR, scanned: /line/checkin?c=<code> (or LINE's own scanner,
// from the linked card). Shown over everything else until they close it.
const checkin = ref<LineCheckinState | null>(null)
const checkinCode = ref('')
const canScan = ref(false)
// A linked member's other screens: tonight's checkout and their bills
// (/line/checkout, /line/bills — the OA menu's "เช็คเอาท์ จ่ายเงิน").
type Screen = 'home' | 'checkout' | 'bills'
const screen = ref<Screen>('home')
const tonight = ref<LineTonight | null>(null)

async function start(): Promise<void> {
  phase.value = 'loading'
  try {
    const config = await lineApi.getLineConfig()
    if (!config.enabled || !config.liff_id) {
      phase.value = 'off'
      return
    }
    const idToken = await liffIdToken(config.liff_id)
    if (!idToken) return // LINE is taking them to log in; the page comes back
    let status: LineStatus
    try {
      status = await lineApi.startLineSession(idToken)
    } catch (e) {
      if (e instanceof ApiError && e.status === 401 && liffSignInAgain()) return
      throw e
    }
    liffSignedIn()
    canScan.value = liffCanScan()
    token.value = status.token ?? ''
    me.value = status
    if (!status.player) await loadOptions()
    joining.value = route.params.section === 'register' && !status.player && !status.pending && !status.application
    const code = typeof route.query.c === 'string' ? route.query.c : ''
    if (route.params.section === 'checkin' && code) await openCheckin(code)
    if (status.player && (route.params.section === 'checkout' || route.params.section === 'bills')) {
      await go(route.params.section)
    }
    phase.value = 'ready'
  } catch (e) {
    problem.value = apiErrorMessage(e, t('line.startFailed'))
    phase.value = 'error'
  }
}

async function loadOptions(): Promise<void> {
  options.value = await lineApi.getLinkOptions(token.value)
}

const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = q
    ? options.value.filter((o) => o.nickname.toLowerCase().includes(q) || o.member_code.toLowerCase().includes(q))
    : options.value
  return list.slice(0, 60)
})
const pickedOption = computed(() => options.value.find((o) => o.id === picked.value) ?? null)

async function confirm(): Promise<void> {
  if (!pickedOption.value || sending.value) return
  sending.value = true
  actionError.value = ''
  try {
    me.value = await lineApi.requestLink(token.value, pickedOption.value.id)
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('line.pickFailed'))
    await loadOptions()
  } finally {
    sending.value = false
  }
}

async function pickAgain(): Promise<void> {
  sending.value = true
  try {
    me.value = await lineApi.cancelLink(token.value)
    picked.value = null
    query.value = ''
    await loadOptions()
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('line.pickFailed'))
  } finally {
    sending.value = false
  }
}

function onSent(status: LineStatus, warning: string): void {
  me.value = status
  joinWarning.value = warning
  joining.value = false
}

async function withdrawJoin(): Promise<void> {
  sending.value = true
  actionError.value = ''
  try {
    me.value = await lineApi.cancelJoin(token.value)
    joinWarning.value = ''
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('line.pickFailed'))
  } finally {
    sending.value = false
  }
}

async function openCheckin(code: string): Promise<void> {
  checkinCode.value = code
  checkin.value = await lineApi.getCheckin(token.value, code)
}

async function scan(): Promise<void> {
  actionError.value = ''
  try {
    const code = await liffScanCheckinCode()
    if (!code) {
      actionError.value = t('lineCheckin.notOurQr')
      checkin.value = null
      return
    }
    void router.replace({ path: '/line/checkin', query: { c: code } })
    await openCheckin(code)
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('lineCheckin.scanFailed'))
  }
}

async function go(next: Screen): Promise<void> {
  actionError.value = ''
  if (next === 'checkout') tonight.value = await lineApi.getTonight(token.value)
  screen.value = next
  void router.replace(next === 'home' ? '/line' : `/line/${next}`)
}

function leaveCheckin(next: 'link' | 'join' | 'done'): void {
  checkin.value = null
  joining.value = next === 'join'
  void router.replace('/line')
  if (next === 'done') void closeLiff()
}

onMounted(start)
</script>

<template>
  <main class="home-world min-h-dvh">
    <div class="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 pt-5 pb-[calc(20px+env(safe-area-inset-bottom,0px))]">
      <div class="flex items-center gap-2.5">
        <img src="/pwa-icons/pwa-64x64.png" alt="" width="36" height="36" class="h-9 w-9 rounded-full" />
        <span class="font-display text-lg font-bold">นิดเดียว<span class="text-brand-pink">BMT</span></span>
      </div>

      <!-- starting -->
      <div v-if="phase === 'loading'" class="world-card flex flex-1 items-center justify-center p-8 text-white/65" role="status">
        {{ t('line.starting') }}
      </div>

      <!-- LINE not set up on the server yet -->
      <div v-else-if="phase === 'off'" class="world-card p-6 text-center">
        <img src="/hero/cat-color.webp" alt="" width="120" height="120" class="mx-auto h-28 w-28 object-contain" />
        <h1 class="world-title mt-3 text-xl">{{ t('line.offTitle') }}</h1>
        <p class="mt-2 text-sm text-white/70">{{ t('line.offBody') }}</p>
      </div>

      <div v-else-if="phase === 'error'" class="world-card p-6 text-center">
        <h1 class="world-title text-xl">{{ t('line.errorTitle') }}</h1>
        <p class="mt-2 text-sm text-white/70" role="alert">{{ problem }}</p>
        <button type="button" class="glass-pill mx-auto mt-4" @click="start">{{ t('line.retry') }}</button>
      </div>

      <template v-else-if="me">
        <div class="flex items-center gap-3 rounded-2xl border border-[#06c755]/40 bg-[#06c755]/10 p-3">
          <span class="ring-line shrink-0 rounded-full">
            <PlayerAvatar :name="me.line_name" :avatar-url="me.line_picture" size="md" round />
          </span>
          <span class="min-w-0">
            <span class="block text-xs text-white/65">{{ t('line.signedInAs') }}</span>
            <span class="block truncate font-medium">{{ me.line_name }}</span>
          </span>
        </div>

        <!-- tonight's QR, scanned -->
        <LineCheckin
          v-if="checkin"
          :key="checkinCode"
          :token="token"
          :code="checkinCode"
          :initial="checkin"
          :waiting="!!(me.pending || me.application)"
          :can-scan="canScan"
          @link="leaveCheckin('link')"
          @join="leaveCheckin('join')"
          @scan="scan"
          @done="leaveCheckin('done')"
        />

        <LineCheckout v-else-if="me.player && screen === 'checkout' && tonight" :token="token" :initial="tonight" @bills="go('bills')" />
        <LineBills v-else-if="me.player && screen === 'bills'" :token="token" @back="go('home')" />

        <!-- linked: who they are, and what's coming -->
        <section v-else-if="me.player" class="world-card flex flex-col items-center gap-3 p-6 text-center">
          <p class="world-eyebrow">LINKED</p>
          <PlayerAvatar :name="me.player.nickname" :avatar-url="me.player.avatar_url" size="lg" round />
          <h1 class="world-title text-2xl">{{ me.player.nickname }}</h1>
          <span class="inline-flex items-center gap-1.5 text-sm text-white/70">
            <TierMascot :tier="me.player.elo_level" :size="22" :interactive="false" />
            {{ me.player.member_code }}
          </span>
          <p class="text-sm text-white/70">{{ canScan ? t('line.linkedBodyScan') : t('line.linkedBody') }}</p>
          <button v-if="canScan" type="button" class="scan-cta flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl font-display text-base font-bold" @click="scan">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M4 12h16" /></svg>
            {{ t('lineCheckin.scan') }}
          </button>
          <div class="grid w-full grid-cols-2 gap-2">
            <button type="button" class="glass-pill justify-center" @click="go('checkout')">{{ t('lineCheckout.open') }}</button>
            <button type="button" class="glass-pill justify-center" @click="go('bills')">{{ t('lineCheckout.myBills') }}</button>
          </div>
          <p v-if="actionError" class="text-sm text-status-error" role="alert">{{ actionError }}</p>
          <RouterLink :to="`/members/${me.player.id}`" class="glass-pill">{{ t('line.myProfile') }}</RouterLink>
        </section>

        <!-- signing up: not in the club yet -->
        <LineJoinForm
          v-else-if="joining"
          :token="token"
          :line-name="me.line_name"
          :line-picture="me.line_picture"
          :application="me.application"
          :members="options"
          @sent="onSent"
          @back="joining = false"
        />

        <!-- signed up, waiting for the admin -->
        <section v-else-if="me.application" class="flex flex-1 flex-col items-center gap-3 text-center">
          <span class="sent-ring mt-2 rounded-full">
            <PlayerAvatar :name="me.application.nickname" :avatar-url="me.application.photo_url" size="xl" round />
          </span>
          <h1 class="world-title text-2xl">{{ t('lineJoin.sentTitle') }}</h1>
          <p class="text-white/80">
            <b class="font-display font-bold text-[#ff9fd6]">{{ me.application.nickname }}</b>
            <template v-if="me.application.dominant_hand">
              · {{ me.application.dominant_hand === 'left' ? t('lineJoin.leftHanded') : t('lineJoin.rightHanded') }}
            </template>
          </p>
          <p v-if="joinWarning" class="text-sm text-[#ffd34d]" role="alert">{{ joinWarning }}</p>
          <ul class="world-card w-full space-y-2 p-4 text-left text-sm">
            <li><span class="text-[#ffd34d]">●</span> {{ t('lineJoin.sentWait') }}</li>
            <li><span class="text-white/40">●</span> {{ t('lineJoin.sentMeanwhile') }}</li>
          </ul>
          <p v-if="actionError" class="text-sm text-status-error" role="alert">{{ actionError }}</p>
          <div class="mt-auto flex w-full flex-col gap-2">
            <button type="button" class="glass-pill w-full justify-center" :disabled="sending" @click="joining = true">
              {{ t('lineJoin.edit') }}
            </button>
            <button type="button" class="min-h-11 text-sm text-white/60" :disabled="sending" @click="withdrawJoin">
              {{ t('lineJoin.withdraw') }}
            </button>
          </div>
        </section>

        <!-- picked, waiting for the admin -->
        <section v-else-if="me.pending" class="flex flex-1 flex-col items-center gap-3 text-center">
          <img src="/hero/cat-color.webp" alt="" width="140" height="140" class="h-32 w-32 object-contain drop-shadow-[0_14px_18px_rgb(234_76_164/0.45)]" />
          <h1 class="world-title text-2xl">{{ t('line.sentTitle') }}</h1>
          <p class="text-white/80">
            {{ t('line.sentFor') }}
            <b class="font-medium text-[#ff9fd6]">{{ me.pending.player.nickname }} ({{ me.pending.player.member_code }})</b>
          </p>
          <ul class="world-card w-full space-y-2 p-4 text-left text-sm">
            <li><span class="text-[#ffd34d]">●</span> {{ t('line.sentWait') }}</li>
            <li><span class="text-white/40">●</span> {{ t('line.sentAfter') }}</li>
          </ul>
          <p v-if="actionError" class="text-sm text-status-error" role="alert">{{ actionError }}</p>
          <button type="button" class="glass-pill mt-auto w-full justify-center" :disabled="sending" @click="pickAgain">
            {{ t('line.pickAgain') }}
          </button>
        </section>

        <!-- who are you? -->
        <section v-else class="flex flex-1 flex-col gap-3">
          <div>
            <p class="world-eyebrow">LINK LINE</p>
            <h1 class="world-title mt-1 text-2xl">{{ t('line.whoTitle') }}</h1>
            <p class="mt-1 text-sm text-white/70">{{ t('line.whoBody') }}</p>
          </div>
          <input
            v-model="query"
            type="search"
            :placeholder="t('line.searchPlaceholder')"
            :aria-label="t('line.searchPlaceholder')"
            class="min-h-12 rounded-2xl border border-white/20 bg-white/10 px-4 text-base text-white outline-none placeholder:text-white/50 focus:border-brand-pink"
          />
          <ul class="flex flex-col gap-2" role="radiogroup" :aria-label="t('line.whoTitle')">
            <li v-for="o in shown" :key="o.id">
              <button
                type="button"
                role="radio"
                :aria-checked="picked === o.id"
                :disabled="o.taken"
                class="pick flex min-h-16 w-full items-center gap-3 rounded-2xl border px-3 py-2 text-left disabled:opacity-45"
                :class="picked === o.id ? 'on' : ''"
                @click="picked = o.id"
              >
                <PlayerAvatar :name="o.nickname" :avatar-url="o.avatar_url" size="md" round />
                <span class="min-w-0 flex-1">
                  <span class="block truncate font-display font-bold">{{ o.nickname }}</span>
                  <span class="block text-xs text-white/60">
                    {{ o.member_code }} · {{ o.taken ? t('line.taken') : t('line.games', { n: o.games }) }}
                  </span>
                </span>
                <TierMascot :tier="o.elo_level" :size="30" :interactive="false" />
                <span class="radio" aria-hidden="true" />
              </button>
            </li>
            <li v-if="shown.length === 0" class="world-card p-4 text-center text-sm text-white/60">{{ t('line.noMatch') }}</li>
          </ul>
          <div class="sticky bottom-0 mt-auto flex flex-col gap-2 bg-gradient-to-t from-[#0b0518] via-[#0b0518]/95 to-transparent pt-4 pb-1">
            <p v-if="actionError" class="text-sm text-status-error" role="alert">{{ actionError }}</p>
            <button
              type="button"
              class="cta min-h-14 rounded-2xl font-display text-base font-bold"
              :disabled="!pickedOption || sending"
              @click="confirm"
            >
              {{ pickedOption ? t('line.itsMe', { name: pickedOption.nickname }) : t('line.pickFirst') }}
            </button>
            <button type="button" class="min-h-11 text-sm font-medium text-[#ff9fd6] underline-offset-4 hover:underline" @click="joining = true">
              {{ t('line.notListed') }}
            </button>
          </div>
        </section>

        <button v-if="me.player && !checkin && screen === 'home'" type="button" class="glass-pill mt-auto w-full justify-center" @click="closeLiff">{{ t('line.close') }}</button>
      </template>
    </div>
  </main>
</template>

<style scoped>
.scan-cta {
  background: linear-gradient(#5dffa0, #06c755);
  color: #02240f;
  box-shadow: 0 8px 22px rgb(6 199 85 / 0.4);
}
.sent-ring {
  box-shadow:
    0 0 0 3px #ffd34d,
    0 0 30px rgb(255 211 77 / 0.45);
}
.ring-line {
  box-shadow: 0 0 0 2px #06c755;
}
.pick {
  border-color: rgb(255 255 255 / 0.12);
  background: rgb(255 255 255 / 0.05);
}
.pick.on {
  border-color: #ff8fd0;
  background: rgb(234 76 164 / 0.16);
  box-shadow: 0 0 0 1px rgb(255 143 208 / 0.4);
}
.radio {
  display: flex;
  width: 22px;
  height: 22px;
  flex: none;
  border-radius: 50%;
  border: 2px solid rgb(255 255 255 / 0.35);
}
.on .radio {
  border-color: #ff8fd0;
  background: #ff8fd0;
  box-shadow: inset 0 0 0 4px #2a0d22;
}
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
/* Solid, not faded: the list scrolls under this bar, and a see-through
   button let the names behind it show through its label. */
.cta:disabled {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
