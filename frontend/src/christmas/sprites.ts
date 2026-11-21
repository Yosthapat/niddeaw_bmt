/**
 * The little pictures the snow and the bursts are drawn with, painted once
 * onto small canvases so each frame only stamps them (drawImage), which is
 * far cheaper than drawing a glow every time.
 */

export const SNOW_WHITE = '#ffffff'
export const SNOW_PINK = '#ffb3dc'
export const NEON_PINK = '#ea4ca4'

function paint(w: number, h: number, draw: (g: CanvasRenderingContext2D) => void): HTMLCanvasElement {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  const g = c.getContext('2d')
  if (g) draw(g)
  return c
}

/** A soft round flake with a neon halo, 64px; drawn smaller. */
export function flakeSprite(color: string): HTMLCanvasElement {
  return paint(64, 64, (g) => {
    const r = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    r.addColorStop(0, color)
    r.addColorStop(0.22, color)
    r.addColorStop(0.32, `${color}99`)
    r.addColorStop(1, `${color}00`)
    g.fillStyle = r
    g.fillRect(0, 0, 64, 64)
  })
}

/** A six-armed snow crystal, 64px, for the bigger flakes. */
export function crystalSprite(color: string): HTMLCanvasElement {
  return paint(64, 64, (g) => {
    g.translate(32, 32)
    g.shadowColor = color
    g.shadowBlur = 8
    g.strokeStyle = color
    g.lineCap = 'round'
    g.lineWidth = 3
    for (let i = 0; i < 6; i++) {
      g.rotate(Math.PI / 3)
      g.beginPath()
      g.moveTo(0, 0)
      g.lineTo(0, -22)
      g.moveTo(0, -12)
      g.lineTo(-7, -18)
      g.moveTo(0, -12)
      g.lineTo(7, -18)
      g.stroke()
    }
  })
}

/** A shuttlecock, cork down, 64px: the club's own snowflake. */
export function shuttleSprite(): HTMLCanvasElement {
  return paint(64, 64, (g) => {
    g.translate(32, 30)
    g.shadowColor = '#ffffff'
    g.shadowBlur = 10
    // the feather skirt
    const skirt = g.createLinearGradient(0, -22, 0, 8)
    skirt.addColorStop(0, '#ffffff')
    skirt.addColorStop(1, '#e6dcf3')
    g.fillStyle = skirt
    g.beginPath()
    g.moveTo(-15, -22)
    g.lineTo(15, -22)
    g.lineTo(6, 8)
    g.lineTo(-6, 8)
    g.closePath()
    g.fill()
    g.shadowBlur = 0
    g.strokeStyle = 'rgba(150,128,190,.6)'
    g.lineWidth = 1.2
    for (let i = -2; i <= 2; i++) {
      g.beginPath()
      g.moveTo(i * 6, -22)
      g.lineTo(i * 2.4, 8)
      g.stroke()
    }
    // the band and the cork
    g.fillStyle = NEON_PINK
    g.fillRect(-7, 6, 14, 4)
    g.fillStyle = '#fff1f8'
    g.beginPath()
    g.arc(0, 12, 7, 0, Math.PI)
    g.fill()
  })
}
