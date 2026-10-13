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
 * the famous "open it twice". The banner closes that: the new version is
 * ready, the screen says so, and the tap reloads into it.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { t } = useI18n()

// Set while the page reloads, so a second tap cannot start a second reload.
const updating = ref(false)

const { needRefresh, updateServiceWorker } = useRegisterSW({
  onRegisteredSW(_url, registration) {
    if (!registration) return
    document.addEventListener('visibilitychange', () => {
      // `update()` is a network request for the worker script; the browser
      // serves it from cache for at most 24h, and only when the page loads
      // — which a resumed iOS app never does.
      if (document.visibilityState === 'visible') void registration.update()
    })
  },
})

async function update(): Promise<void> {
  updating.value = true
  // `true` tells the waiting worker to take over, then reloads into it.
  await updateServiceWorker(true)
}
</script>

<template>
  <!-- Above the content, under the header: a club night is run with a thumb
       at the bottom of the screen, and a bar down there would sit under the
       buttons that bill people. -->
  <Transition name="update-banner">
    <div
      v-if="needRefresh"
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
