// A strip that drifts leftward on its own and can also be swiped, dragged
// or wheeled by hand — the member photos and the sponsor logos on the home
// page.
//
// Driven by scrollLeft rather than a CSS transform: the drift and the hand
// write the same value, so they compose instead of fighting. A transform
// animation would keep sliding the content out from under the reader's
// thumb, and a transform can't be scrolled at all.
//
// The strip's content must be two identical halves. Moving scrollLeft by
// exactly one half lands on the identical pixel, so the strip can loop with
// no seam. It is kept inside a one-half window that sits in the middle of
// the track rather than at its start, leaving room on both sides: a finger
// pulling the strip back to the right has track to scroll into too, not a
// wall at zero. The more a half outruns the strip's width, the bigger that
// room — SponsorBand sizes its halves for it.
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

export interface DriftOptions {
  /** In pixels per second, so the pace stays the same whatever the content. */
  speed: number
  /** How long the drift keeps out of the way after the reader last moved it. */
  resumeAfterMs?: number
}

// A mouse press that travels less than this is a click on a link, not a drag.
const DRAG_THRESHOLD_PX = 5

export function useDriftStrip(strip: Ref<HTMLElement | null>, options: DriftOptions) {
  const resumeAfter = options.resumeAfterMs ?? 1500
  const paused = ref(false)

  let frame = 0
  let lastTime = 0
  let interactingUntil = 0
  // The drift's own position, kept as a float. Assigning sub-pixel deltas
  // straight to scrollLeft loses them to rounding, and at a slow pace the
  // strip creeps by a pixel or two a second instead of drifting.
  let position = 0
  // Whether the last frame was the drift's. When it wasn't, position is
  // re-read from the element so the drift carries on from wherever the
  // reader left the strip rather than snapping back to its own idea of it.
  let driving = false
  // What the drift last wrote, so a scroll event can tell the drift's own
  // movement from a finger's momentum still coasting after it lifted.
  let written = -1

  // Touch screens scroll the strip natively. A mouse doesn't drag-scroll
  // anything by default, so it gets the same by hand: press, pull, let go.
  let dragging = false
  let pressX = 0
  let pressScroll = 0
  let pressing = false
  let dragged = false
  // A finger on the strip. The browser owns the scroll position for the
  // length of a touch gesture and puts back any value written under it, so
  // the loop's jump has to wait until the finger lifts.
  let touching = false

  /** The same pixel of the loop, moved into the window [lo, lo + half). */
  function inWindow(el: HTMLElement, x: number): number {
    const half = el.scrollWidth / 2
    if (half <= 0) return x
    const lo = Math.max(0, (half - el.clientWidth) / 2)
    while (x >= lo + half) x -= half
    while (x < lo) x += half
    return x
  }

  function wrap(el: HTMLElement): void {
    if (touching) return
    const x = inWindow(el, el.scrollLeft)
    if (Math.abs(x - el.scrollLeft) > 0.5) el.scrollLeft = x
  }

  /** Hands control to the reader for a moment. */
  function noteInteraction(): void {
    interactingUntil = performance.now() + resumeAfter
  }

  function step(now: number): void {
    const el = strip.value
    const elapsed = lastTime === 0 ? 0 : now - lastTime
    lastTime = now
    if (el && !paused.value && !dragging && now >= interactingUntil) {
      if (!driving) {
        position = inWindow(el, el.scrollLeft)
        driving = true
      }
      // Clamped: a backgrounded tab resumes with a huge delta that would
      // teleport the strip instead of continuing it.
      position = inWindow(el, position + options.speed * (Math.min(elapsed, 100) / 1000))
      el.scrollLeft = position
      written = el.scrollLeft
    } else {
      driving = false
    }
    frame = requestAnimationFrame(step)
  }

  function onScroll(): void {
    const el = strip.value
    if (!el) return
    // Not where the drift put it: the reader moved it, or momentum from a
    // flick is still carrying it. Either way the drift waits until it stops.
    if (Math.abs(el.scrollLeft - written) > 1) {
      driving = false
      noteInteraction()
    }
    wrap(el)
  }

  function onPointerDown(event: PointerEvent): void {
    noteInteraction()
    if (event.pointerType !== 'mouse' || event.button !== 0 || !strip.value) return
    pressing = true
    dragged = false
    pressX = event.clientX
    pressScroll = strip.value.scrollLeft
  }

  function onPointerMove(event: PointerEvent): void {
    const el = strip.value
    if (!pressing || !el) return
    const dx = event.clientX - pressX
    if (!dragging && Math.abs(dx) < DRAG_THRESHOLD_PX) return
    if (!dragging) {
      dragging = true
      dragged = true
      el.setPointerCapture(event.pointerId)
    }
    el.scrollLeft = pressScroll - dx
    // Wrapping moves scrollLeft under the drag; move the anchor with it so
    // the content stays under the cursor.
    const before = el.scrollLeft
    wrap(el)
    pressScroll += el.scrollLeft - before
    noteInteraction()
  }

  function onPointerUp(event: PointerEvent): void {
    pressing = false
    if (dragging && strip.value?.hasPointerCapture(event.pointerId)) {
      strip.value.releasePointerCapture(event.pointerId)
    }
    dragging = false
    noteInteraction()
  }

  function onTouchEnd(event: TouchEvent): void {
    if (event.touches.length > 0) return
    touching = false
    noteInteraction()
    if (strip.value) wrap(strip.value)
  }

  /** A drag that ends over a logo would otherwise open it. */
  function onClickCapture(event: MouseEvent): void {
    if (!dragged) return
    dragged = false
    event.preventDefault()
    event.stopPropagation()
  }

  // Bound with v-on="handlers". The Capture / Passive suffixes are Vue's
  // spelling of the .capture / .passive modifiers in object form.
  const handlers = {
    pointerenter: (event: PointerEvent) => {
      // Holds still while someone is aiming at it with a mouse. A finger
      // "enters" on every tap and would leave it stuck until the next one.
      if (event.pointerType === 'mouse') paused.value = true
    },
    pointerleave: () => {
      paused.value = false
    },
    focusin: (event: FocusEvent) => {
      // Only for the keyboard. A mouse press on a logo focuses the link
      // too, and that focus outlives the press: the strip would stay
      // frozen long after the reader let go of it.
      const target = event.target
      if (target instanceof Element && target.matches(':focus-visible')) paused.value = true
    },
    focusout: () => {
      paused.value = false
    },
    pointerdown: onPointerDown,
    pointermove: onPointerMove,
    pointerup: onPointerUp,
    pointercancel: onPointerUp,
    clickCapture: onClickCapture,
    dragstart: (event: DragEvent) => event.preventDefault(),
    touchstartPassive: () => {
      touching = true
      noteInteraction()
    },
    touchendPassive: onTouchEnd,
    touchcancelPassive: onTouchEnd,
    wheelPassive: noteInteraction,
    scrollPassive: onScroll,
  }

  onMounted(() => {
    // Same contract the rest of the site keeps (v-reveal, CountUp, the
    // ambient blobs): no self-starting motion when the reader asked for
    // less. The strip stays swipeable either way.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    frame = requestAnimationFrame(step)
  })
  onBeforeUnmount(() => cancelAnimationFrame(frame))

  return { paused, handlers }
}
