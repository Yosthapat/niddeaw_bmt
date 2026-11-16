<script setup lang="ts">
/**
 * "There is a new version — tap to update."
 *
 * Added on a phone's home screen, this app is served by a service worker:
 * every screen comes out of a cache that only changes when a new worker
 * installs. Two things then keep a club night on an old build.
 *
 * iOS does not reload a home-screen app when you come back to it — it
 * resumes the process it suspended, so the page never loads again and the
 * browser never goes looking for a new worker. Until the app is swiped out
 * of the app switcher, it can sit on last week's code for days. So this
 * asks for a check every time the app comes back to the foreground, which
 * is the moment a phone app is used.
 *
 * And even on a real reload, the page you are looking at was already
 * painted from the old cache before the new worker finished installing —
 * the famous "open it twice".
 *
 * Waiting for a tap left phones on old code: nobody taps a banner they
 * didn't expect. So the new version now goes in by itself whenever that
 * can't cost anything:
 *
 * - the app was just opened, or brought back, and nothing has been typed
 *   since the page loaded — there is nothing on screen to lose;
 * - the next time someone moves to another page — the page they leave is
 *   gone anyway.
 *
 * Only someone part way through a form keeps the old build until they
 * move on or tap the banner, which still shows for them: the admin on a
 * court with a half-filled bill is why the update was never forced.
 *
 * And a phone whose worker never notices the deploy at all — an iPhone in
 * Safari stayed on the old build with no banner — is caught by asking the
 * server which build it has (/version.json, see vite.config.ts). If that is
 * newer than this page and no new worker turns up, the banner shows anyway,
 * and its tap drops the old worker and its caches and loads the page fresh.
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { t } = useI18n()
const router = useRouter()

/** How long after the app opens, or comes back, an update found then is
 *  taken as "on opening" rather than "while in use". */
const FRESH_MS = 10_000
/** A long-open tab still hears about a deploy within this time. */
const RECHECK_MS = 30 * 60_000

let swRegistration: ServiceWorkerRegistration | undefined
let freshSince = Date.now()
// Anything typed since this page loaded. Never cleared: what was typed is
// still on screen after the phone comes back to the app.
let typed = false
const markTyped = (): void => {
  typed = true
}
document.addEventListener('input', markTyped, true)
document.addEventListener('change', markTyped, true)

// Set while the page reloads, so a second tap cannot start a second reload.
const updating = ref(false)

/** How long a new worker gets to show up once the server says there is a
 *  newer build, before the page stops waiting for it. */
const WORKER_GRACE_MS = 8_000
// The server has a newer build than this page, and no new worker came.
const stale = ref(false)
let staleTimer: number | undefined
async function checkVersion(): Promise<void> {
  if (__BUILD_SHA__ === 'dev' || stale.value) return
  try {
    const res = await fetch(`/version.json?t=${Date.now()}`, { cache: 'no-store' })
    if (!res.ok) return
    const { sha } = (await res.json()) as { sha?: unknown }
    if (typeof sha !== 'string' || sha === 'dev' || sha === __BUILD_SHA__) return
    void swRegistration?.update()
    window.clearTimeout(staleTimer)
    staleTimer = window.setTimeout(() => {
      if (needRefresh.value || newVersionInCharge) return
      stale.value = true
      // Just opened and nothing typed: nothing to lose, as with a worker.
      // Once per build per tab, so a server that says "new" but still hands
      // out the old page can't keep it reloading.
      if (!typed && Date.now() - freshSince < FRESH_MS + WORKER_GRACE_MS && onceFor(sha)) void update()
    }, WORKER_GRACE_MS)
  } catch {
    // Offline, or no version file yet: the worker's own check still runs.
  }
}
function onceFor(sha: string): boolean {
  try {
    const key = `pwa-fresh-load:${sha}`
    if (sessionStorage.getItem(key)) return false
    sessionStorage.setItem(key, '1')
    return true
  } catch {
    return false
  }
}

const { needRefresh, updateServiceWorker } = useRegisterSW({
  onRegisteredSW(_url, registration) {
    if (!registration) return
    swRegistration = registration
    document.addEventListener('visibilitychange', () => {
      // `update()` is a network request for the worker script; the browser
      // serves it from cache for at most 24h, and only when the page loads
      // — which a resumed iOS app never does.
      if (document.visibilityState === 'visible') {
        freshSince = Date.now()
        void registration.update()
      }
    })
    setInterval(() => {
      if (document.visibilityState === 'visible') void registration.update()
    }, RECHECK_MS)
  },
})

// The server's build, asked at the same moments as the worker: on opening,
// on coming back to the app, and every half hour while it is open.
void checkVersion()
const onVisible = (): void => {
  if (document.visibilityState === 'visible') void checkVersion()
}
document.addEventListener('visibilitychange', onVisible)
const versionTimer = window.setInterval(onVisible, RECHECK_MS)

// The reload, once the new worker has taken over. The plugin's own reload
// listens for workbox's "controlling" with isUpdate set, which a worker
// found by the update() calls above — not by the page's own register() —
// does not always carry; controllerchange is the browser's own signal.
//
// It also fires on its own when a worker told to take over earlier only
// gets to once the old one is idle (see update()). Then it reloads only
// while the app has just opened and nothing has been typed; otherwise the
// next page change does it.
let reloading = false
let newVersionInCharge = false
const reload = (): void => {
  if (reloading) return
  reloading = true
  window.location.reload()
}
const onControllerChange = (): void => {
  newVersionInCharge = true
  if (updating.value || (!typed && Date.now() - freshSince < FRESH_MS)) reload()
}
navigator.serviceWorker?.addEventListener('controllerchange', onControllerChange)

async function update(): Promise<void> {
  if (updating.value) return
  if (!needRefresh.value) return freshLoad()
  updating.value = true
  // Tells the waiting worker to take over; onControllerChange reloads.
  await updateServiceWorker(true)
  // And once more straight to the worker the browser says is waiting, in
  // case the plugin's copy of the registration has not caught up with it.
  // A second SKIP_WAITING to a worker already activating does nothing.
  swRegistration?.waiting?.postMessage({ type: 'SKIP_WAITING' })
  // A browser holds the new worker back while the old one is still
  // answering a request. Reloading ends those requests; the new worker then
  // takes over and onControllerChange brings the page onto it.
  window.setTimeout(fallbackReload, 4000)
}

// No new worker to hand over to (stale): let the old one go with its
// caches, and load the page from the network. The new build registers its
// own worker as it loads.
async function freshLoad(): Promise<void> {
  updating.value = true
  try {
    const registrations = (await navigator.serviceWorker?.getRegistrations()) ?? []
    await Promise.all(registrations.map((r) => r.unregister()))
    const keys = 'caches' in window ? await caches.keys() : []
    await Promise.all(keys.map((k) => caches.delete(k)))
  } catch {
    // Whatever could not be cleared, the reload below still asks the network.
  }
  reload()
}

// At most once a minute, so a worker that never takes over can't keep the
// page reloading. sessionStorage: it is the reload itself that must not
// forget it, and it may be unavailable (private mode), when this just
// doesn't fall back.
const FALLBACK_KEY = 'pwa-update-fallback-at'
function fallbackReload(): void {
  if (reloading) return
  try {
    const last = Number(sessionStorage.getItem(FALLBACK_KEY) ?? 0)
    if (Date.now() - last < 60_000) return
    sessionStorage.setItem(FALLBACK_KEY, String(Date.now()))
  } catch {
    return
  }
  reload()
}

// Found just as the app opened, before anything was typed: go straight in.
watch(needRefresh, (ready) => {
  if (ready && !typed && Date.now() - freshSince < FRESH_MS) void update()
})

// Moving to another page: the reload lands on the page they were going to.
const stopAfterEach = router.afterEach((to, from, failure) => {
  if (failure || to.fullPath === from.fullPath) return
  if (newVersionInCharge) reload()
  else if (needRefresh.value || stale.value) void update()
})

onBeforeUnmount(() => {
  stopAfterEach()
  document.removeEventListener('input', markTyped, true)
  document.removeEventListener('change', markTyped, true)
  navigator.serviceWorker?.removeEventListener('controllerchange', onControllerChange)
  document.removeEventListener('visibilitychange', onVisible)
  window.clearInterval(versionTimer)
  window.clearTimeout(staleTimer)
})
</script>

<template>
  <!-- Above the content, under the header: a club night is run with a thumb
       at the bottom of the screen, and a bar down there would sit under the
       buttons that bill people. -->
  <Transition name="update-banner">
    <div
      v-if="needRefresh || stale"
      class="fixed inset-x-0 top-0 z-30 flex justify-center px-3 pt-3"
      role="status"
    >
      <button
        type="button"
        :disabled="updating"
        class="hud-panel tap gap-2 border border-brand-pink bg-brand-surface-raised px-4 text-sm font-semibold text-white shadow-lg disabled:opacity-60"
        @click="update"
      >
        <span class="relative flex h-2 w-2 shrink-0">
          <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-pink opacity-75" />
          <span class="relative inline-flex h-2 w-2 rounded-full bg-brand-pink" />
        </span>
        {{ updating ? t('update.updating') : t('update.available') }}
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.update-banner-enter-active {
  transition:
    opacity 0.25s ease,
    translate 0.25s ease;
}
.update-banner-enter-from {
  opacity: 0;
  translate: 0 -0.75rem;
}
</style>
