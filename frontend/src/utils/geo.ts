/**
 * Where this phone is, for checking in by location.
 *
 * A phone's first GPS answer is often its roughest (a cell tower, ±1 km),
 * and better ones follow within seconds. So this listens for a few seconds
 * and keeps the most accurate answer, stopping early once one is good
 * enough. It works the same in LINE's in-app browser on iPhone and Android;
 * the first time, the phone asks the member to allow location.
 */

export interface Fix {
  lat: number
  lng: number
  accuracy: number
}

export type FixProblem = 'denied' | 'unavailable' | 'unsupported'

export class FixError extends Error {
  readonly problem: FixProblem
  constructor(problem: FixProblem) {
    super(problem)
    this.problem = problem
  }
}

/** Good enough to stop listening early (metres). */
const GOOD_ENOUGH_M = 25

export function canLocate(): boolean {
  return typeof navigator !== 'undefined' && 'geolocation' in navigator
}

export function locate(maxWaitMs = 8000): Promise<Fix> {
  return new Promise((resolve, reject) => {
    if (!canLocate()) {
      reject(new FixError('unsupported'))
      return
    }
    let best: Fix | null = null
    let finished = false
    let watch: number | null = null
    const finish = (problem?: FixProblem): void => {
      if (finished) return
      finished = true
      if (watch !== null) navigator.geolocation.clearWatch(watch)
      clearTimeout(timer)
      if (best) resolve(best)
      else reject(new FixError(problem ?? 'unavailable'))
    }
    const timer = setTimeout(() => finish(), maxWaitMs)
    watch = navigator.geolocation.watchPosition(
      (pos) => {
        const fix = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }
        if (!best || fix.accuracy < best.accuracy) best = fix
        if (fix.accuracy <= GOOD_ENOUGH_M) finish()
      },
      (err) => {
        // denied is final; a slow or failed read keeps what it had, if anything
        if (err.code === err.PERMISSION_DENIED) finish('denied')
        else if (!best && err.code !== err.TIMEOUT) finish('unavailable')
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: maxWaitMs },
    )
  })
}
