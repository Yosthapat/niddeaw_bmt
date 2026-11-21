import { ref, watch } from 'vue'

/**
 * What a member chose for the season on this device: snow on or off.
 * The music is never remembered as "on": a browser will not start sound
 * without a tap, so it always waits for one.
 */
const SNOW_KEY = 'niddeaw_xmas_snow'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

export const snowOn = ref(read(SNOW_KEY) !== 'off')
watch(snowOn, (on) => {
  try {
    localStorage.setItem(SNOW_KEY, on ? 'on' : 'off')
  } catch {
    // storage blocked: the choice lasts for this visit
  }
})
