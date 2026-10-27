/**
 * The home hero as a live three.js scene.
 *
 * Loaded on demand by HomeHero.vue (a dynamic import, so none of three.js
 * is in the bundle a visitor downloads first) and only on a device that
 * looks able to run it. Everything here has a CSS twin in HomeHero.vue,
 * which is what everyone sees first and what a slow device keeps.
 *
 * What is in it: a neon grid floor sliding toward the viewer, a striped sun
 * on the horizon, a hologram podium with a beam, the club's cat standing in
 * it, three modelled shuttlecocks, four drink mascots at different depths,
 * and dust rising through the beam, with a bloom pass for the neon glow.
 *
 * The cat is not a 3D model. It is the baked art (tools/art/bake_3d.py) on
 * a finely divided plane, each vertex pushed toward the camera by the depth
 * map from the same script, so when the camera moves the head and body
 * stand out of the picture for real. It holds up to roughly ±25°; the
 * camera never turns further than that.
 */
import * as THREE from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js'

/** The cat plane's width and height, in world units. */
const CAT = 3.7

export interface HeroSceneOptions {
  canvas: HTMLCanvasElement
  /** Follow the mouse. Without one the camera drifts on its own. */
  followPointer: boolean
  /** Every two seconds: the measured frame rate and whether bloom is still on. */
  onFps?: (fps: number, bloom: boolean) => void
  /** Even without bloom this device cannot keep up: go back to CSS. */
  onGiveUp: (reason: string) => void
}

export interface HeroScene {
  /** Size the drawing buffer and place the cat over `anchor`, both in CSS px of the canvas. */
  layout(width: number, height: number, anchor: DOMRectReadOnly): void
  /** Stop drawing while the hero is off screen; start again when it is back. */
  setRunning(on: boolean): void
  dispose(): void
}

type Place = [x: number, y: number, z: number, scale: number]

const VERT_UV = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }'

function loadTexture(loader: THREE.TextureLoader, url: string, srgb = true): Promise<THREE.Texture> {
  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (t) => {
        if (srgb) t.colorSpace = THREE.SRGBColorSpace
        resolve(t)
      },
      undefined,
      reject,
    )
  })
}

function canvasTexture(w: number, h: number, draw: (g: CanvasRenderingContext2D) => void): THREE.CanvasTexture {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  const g = c.getContext('2d')
  if (g) draw(g)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

const softDot = (): THREE.CanvasTexture =>
  canvasTexture(64, 64, (g) => {
    const r = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    r.addColorStop(0, 'rgba(255,255,255,1)')
    r.addColorStop(0.35, 'rgba(255,255,255,.55)')
    r.addColorStop(1, 'rgba(255,255,255,0)')
    g.fillStyle = r
    g.fillRect(0, 0, 64, 64)
  })

const feathers = (): THREE.CanvasTexture =>
  canvasTexture(256, 128, (g) => {
    const lin = g.createLinearGradient(0, 0, 0, 128)
    lin.addColorStop(0, '#ffffff')
    lin.addColorStop(1, '#e6dcf3')
    g.fillStyle = lin
    g.fillRect(0, 0, 256, 128)
    g.strokeStyle = 'rgba(150,128,190,.55)'
    g.lineWidth = 2
    for (let i = 0; i < 16; i++) {
      const x = ((i + 0.5) * 256) / 16
      g.beginPath()
      g.moveTo(x, 0)
      g.lineTo(x, 128)
      g.stroke()
    }
  })

export async function createHeroScene(opts: HeroSceneOptions): Promise<HeroScene> {
  const { canvas } = opts
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' })
  const pixelRatio = Math.min(window.devicePixelRatio, 1.75)
  renderer.setPixelRatio(pixelRatio)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  // The cat's colours are baked; tone mapping would shift them.
  renderer.toneMapping = THREE.NoToneMapping

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x07030f)
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 220)
  const clock = new THREE.Clock(false)

  const loader = new THREE.TextureLoader()
  const [catTex, depthTex, ...tierTex] = await Promise.all([
    loadTexture(loader, '/hero/cat-color.webp'),
    loadTexture(loader, '/hero/cat-depth.png', false),
    loadTexture(loader, '/tiers/beer.webp'),
    loadTexture(loader, '/tiers/absinthe.webp'),
    loadTexture(loader, '/tiers/wine.webp'),
    loadTexture(loader, '/tiers/soju.webp'),
  ])
  catTex.anisotropy = renderer.capabilities.getMaxAnisotropy()

  // --- sky: a gradient wall behind the far end of the floor
  const sky = new THREE.Mesh(
    new THREE.PlaneGeometry(700, 160),
    new THREE.ShaderMaterial({
      depthWrite: false,
      vertexShader:
        'varying float vY; void main(){ vec4 w = modelMatrix * vec4(position, 1.); vY = w.y; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: `varying float vY;
        void main(){
          vec3 top = vec3(.027, .012, .06), mid = vec3(.08, .04, .17), hz = vec3(.30, .11, .45);
          float t = clamp(vY / 30., 0., 1.);
          vec3 c = mix(hz, mid, smoothstep(0., .25, t));
          gl_FragColor = vec4(mix(c, top, smoothstep(.25, 1., t)), 1.);
        }`,
    }),
  )
  sky.position.set(0, 50, -150)
  scene.add(sky)

  {
    const n = 420
    const p = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      p[i * 3] = (Math.random() - 0.5) * 220
      p[i * 3 + 1] = 4 + Math.random() * 60
      p[i * 3 + 2] = -146 + Math.random() * 4
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(p, 3))
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 0.35, map: softDot(), transparent: true, depthWrite: false, color: 0xffe6f4 })))
  }

  // --- the striped sun, and its glow
  const sunUniforms = { uTime: { value: 0 } }
  const sun = new THREE.Mesh(
    new THREE.PlaneGeometry(44, 44),
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: sunUniforms,
      vertexShader: VERT_UV,
      fragmentShader: `varying vec2 vUv; uniform float uTime;
        void main(){
          float r = length(vUv * 2. - 1.);
          float edge = smoothstep(1., .985, r);
          float y = vUv.y;
          vec3 top = vec3(1., .9, .96), mid = vec3(1., .42, .78), bot = vec3(.56, .3, .95);
          vec3 c = y > .5 ? mix(mid, top, (y - .5) * 2.) : mix(bot, mid, y * 2.);
          float cut = 1.;
          if (y < .56) { float k = (.56 - y) / .56; cut = step(k * .62, fract(y * 10. + uTime * .12)); }
          gl_FragColor = vec4(c * .92, edge * cut);
        }`,
    }),
  )
  const sunGlow = new THREE.Mesh(
    new THREE.PlaneGeometry(110, 110),
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: VERT_UV,
      fragmentShader:
        'varying vec2 vUv; void main(){ float d = length(vUv - .5) * 2.; float a = pow(max(0., 1. - d), 2.2) * .3; gl_FragColor = vec4(vec3(1., .35, .75) * a, 1.); }',
    }),
  )
  scene.add(sun, sunGlow)

  // --- the floor: an antialiased neon grid sliding toward the viewer
  const floorUniforms = { uTime: { value: 0 } }
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(260, 160),
    new THREE.ShaderMaterial({
      uniforms: floorUniforms,
      vertexShader:
        'varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: `varying vec3 vW; uniform float uTime;
        float grid(vec2 p){ vec2 g = abs(fract(p - .5) - .5) / fwidth(p); return 1. - min(min(g.x, g.y), 1.); }
        void main(){
          float g = grid(vec2(vW.x, vW.z - uTime * 1.1));
          float near = exp(-max(0., 8. - vW.z) * .045);
          vec3 c = vec3(.05, .018, .1) + vec3(1., .36, .76) * (.32 + .78 * near) * g;
          c += vec3(1., .3, .7) * .22 * exp(-length(vW.xz) * .6);
          gl_FragColor = vec4(mix(c, vec3(.3, .11, .45), smoothstep(14., 70., -vW.z)), 1.);
        }`,
    }),
  )
  floor.rotation.x = -Math.PI / 2
  floor.position.z = -60
  scene.add(floor)

  const seam = new THREE.Mesh(
    new THREE.PlaneGeometry(400, 3),
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: VERT_UV,
      fragmentShader:
        'varying vec2 vUv; void main(){ float a = exp(-abs(vUv.y - .5) * 14.) * smoothstep(0., .3, vUv.x) * smoothstep(1., .7, vUv.x); gl_FragColor = vec4(vec3(1.1, .45, .85) * a, 1.); }',
    }),
  )
  seam.position.set(0, 0.2, -139.5)
  scene.add(seam)

  // --- podium and beam, at the cat's feet (the world origin)
  const neon = (hex: number, k: number): THREE.MeshBasicMaterial =>
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(hex).multiplyScalar(k),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    })
  const rings = [
    new THREE.Mesh(new THREE.RingGeometry(1.86, 1.93, 128), neon(0xff7ccb, 1.9)),
    new THREE.Mesh(new THREE.RingGeometry(1.36, 1.39, 128), neon(0xffc4e6, 1.2)),
  ]
  for (const r of rings) {
    r.rotation.x = -Math.PI / 2
    r.position.y = 0.02
    scene.add(r)
  }
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(1.95, 96),
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: VERT_UV,
      fragmentShader:
        'varying vec2 vUv; void main(){ float d = length(vUv - .5) * 2.; gl_FragColor = vec4(mix(vec3(1., .45, .8), vec3(.6, .35, .95), d) * (1. - d) * .5, 1.); }',
    }),
  )
  disc.rotation.x = -Math.PI / 2
  disc.position.y = 0.01
  scene.add(disc)

  const beamUniforms = { uTime: { value: 0 } }
  // BackSide: only the far wall of the beam, so it lights the stage behind
  // the cat instead of fogging the cat.
  const beam = new THREE.Mesh(
    new THREE.CylinderGeometry(1.75, 1.45, 4.2, 64, 1, true),
    new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      uniforms: beamUniforms,
      vertexShader: VERT_UV,
      fragmentShader: `varying vec2 vUv; uniform float uTime;
        void main(){
          float a = pow(1. - vUv.y, 1.6) * .24;
          a *= .75 + .25 * sin(uTime * 2.2 + vUv.y * 9.);
          a *= .55 + .45 * sin(vUv.x * 37.7 + uTime * .8);
          gl_FragColor = vec4(vec3(1., .42, .82) * a, 1.);
        }`,
    }),
  )
  beam.position.y = 2.1
  scene.add(beam)

  // --- the cat
  const segments = window.innerWidth < 700 ? 160 : 240
  const cat = new THREE.Mesh(
    new THREE.PlaneGeometry(CAT, CAT, segments, segments),
    new THREE.MeshStandardMaterial({
      map: catTex, // for its alpha; colour comes from the emissive copy below
      color: 0x000000,
      emissive: 0xffffff,
      emissiveMap: catTex,
      emissiveIntensity: 0.94, // just under the bloom threshold: the cat itself never glows
      displacementMap: depthTex,
      displacementScale: 0.62,
      roughness: 1,
      metalness: 0,
      transparent: true,
      alphaTest: 0.03,
    }),
  )
  scene.add(cat)

  scene.add(new THREE.HemisphereLight(0xb9a2ff, 0x5a1440, 1.4))
  const key = new THREE.DirectionalLight(0xffffff, 2.6)
  key.position.set(-4, 7, 6)
  scene.add(key)
  const pink = new THREE.PointLight(0xff5fb8, 12, 0, 2)
  pink.position.set(0, 1.2, 2)
  scene.add(pink)

  // --- shuttlecocks, modelled
  const skirtMat = new THREE.MeshStandardMaterial({ map: feathers(), side: THREE.DoubleSide, roughness: 0.55, transparent: true, opacity: 0.97 })
  const corkMat = new THREE.MeshStandardMaterial({ color: 0xffe9f4, roughness: 0.35, emissive: 0x3a0a22 })
  const bandMat = new THREE.MeshStandardMaterial({ color: 0xea4ca4, roughness: 0.3, emissive: 0x6d1247, emissiveIntensity: 0.8 })
  const skirtGeo = new THREE.CylinderGeometry(0.5, 0.15, 0.78, 40, 1, true)
  const bandGeo = new THREE.TorusGeometry(0.155, 0.028, 12, 40)
  const corkGeo = new THREE.SphereGeometry(0.17, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2)
  const shuttles = [0, 1, 2].map(() => {
    const g = new THREE.Group()
    const skirt = new THREE.Mesh(skirtGeo, skirtMat)
    skirt.position.y = 0.39
    const band = new THREE.Mesh(bandGeo, bandMat)
    band.rotation.x = Math.PI / 2
    band.position.y = 0.035
    g.add(skirt, band, new THREE.Mesh(corkGeo, corkMat))
    scene.add(g)
    return g
  })

  // --- drink mascots: flat sprites at different depths, so the camera parallaxes them
  const sprites = tierTex.map((t) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }))
    scene.add(s)
    return s
  })

  // --- dust rising through the beam
  const dustCount = 220
  const dustPos = new Float32Array(dustCount * 3)
  const dustSpeed = new Float32Array(dustCount)
  for (let i = 0; i < dustCount; i++) {
    const a = Math.random() * Math.PI * 2
    const r = Math.sqrt(Math.random()) * 2.4
    dustPos[i * 3] = Math.cos(a) * r
    dustPos[i * 3 + 1] = Math.random() * 5
    dustPos[i * 3 + 2] = Math.sin(a) * r
    dustSpeed[i] = 0.2 + Math.random() * 0.5
  }
  const dustGeo = new THREE.BufferGeometry()
  const dustAttr = new THREE.BufferAttribute(dustPos, 3)
  dustGeo.setAttribute('position', dustAttr)
  scene.add(
    new THREE.Points(
      dustGeo,
      new THREE.PointsMaterial({
        size: 0.07,
        map: softDot(),
        color: new THREE.Color(0xff8fd0).multiplyScalar(1.4),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    ),
  )

  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, camera))
  // Threshold 1.0: only what is drawn brighter than white (the neon) glows.
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.42, 0.38, 1.0)
  composer.addPass(bloom)
  composer.addPass(new OutputPass())

  // --- framing
  let view = { r: 10, tx: 0, ty: 1.8, eye: 1 }
  const placements: { shuttles: Place[]; sprites: Place[] } = { shuttles: [], sprites: [] }
  let width = 1
  let height = 1

  function layout(w: number, h: number, anchor: DOMRectReadOnly): void {
    width = w
    height = h
    renderer.setSize(w, h, false)
    composer.setSize(w, h)
    const aspect = w / h
    camera.aspect = aspect
    camera.fov = 38
    camera.updateProjectionMatrix()
    const tanv = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
    // Far enough back that the cat is as tall as the anchor box, and aimed
    // so that its centre lands on the box's centre.
    const r = CAT / ((anchor.height / h) * 2 * tanv)
    const ax = ((anchor.x + anchor.width / 2) / w) * 2 - 1
    const ay = 1 - ((anchor.y + anchor.height / 2) / h) * 2
    const tx = -ax * r * tanv * aspect
    const ty = CAT / 2 - ay * r * tanv
    view = { r, tx, ty, eye: r * 0.1 }
    // The sun goes straight behind the cat as seen from the camera.
    const k = (r + 147) / r
    sun.position.set(tx - tx * k, ty + view.eye + 7, -147)
    sunGlow.position.set(sun.position.x, sun.position.y - 1, -148)
    const wide = w >= 900 && aspect >= 0.9
    placements.shuttles = wide
      ? [[1.45, 0.95, 2.2, 0.7], [2.4, 3.1, -0.8, 0.62], [-3.3, 0.25, -1.5, 0.75]]
      : [[-1.45, 3.75, 1.6, 0.62], [1.75, 2.35, -0.9, 0.5], [-3.6, 5.2, -6, 0.8]]
    placements.sprites = wide
      ? [[-3.0, 3.6, -3.4, 0.95], [2.0, 3.9, -1.2, 1.05], [3.0, 2.1, -2.2, 0.85], [-1.85, 0.8, 1.6, 0.9]]
      : [[-1.75, 1.75, -2.4, 0.75], [1.55, 3.95, -1.1, 0.78], [2.25, 0.95, -2.6, 0.62], [1.5, 1.0, 1.5, 0.72]]
    shuttles.forEach((s, i) => s.scale.setScalar(placements.shuttles[i][3]))
    sprites.forEach((s, i) => s.scale.setScalar(placements.sprites[i][3]))
  }

  // --- motion
  let yaw = 0
  let pitch = 0
  let tYaw = 0
  let tPitch = 0
  const onPointer = (e: PointerEvent): void => {
    tYaw = (e.clientX / window.innerWidth - 0.5) * 0.44
    tPitch = (e.clientY / window.innerHeight - 0.5) * 0.16
  }
  if (opts.followPointer) window.addEventListener('pointermove', onPointer)

  let raf = 0
  let bloomOn = true
  let measuringFrom = 0
  let frames = 0
  let warmUntil = 0

  function frame(): void {
    raf = requestAnimationFrame(frame)
    const dt = Math.min(clock.getDelta(), 0.1)
    const t = clock.elapsedTime
    if (!opts.followPointer) {
      tYaw = Math.sin(t * 0.3) * 0.24
      tPitch = Math.sin(t * 0.19) * 0.06
    }
    yaw += (tYaw - yaw) * 0.05
    pitch += (tPitch - pitch) * 0.05
    camera.position.set(view.tx + Math.sin(yaw) * view.r, view.ty + view.eye + pitch * view.r, Math.cos(yaw) * view.r)
    camera.lookAt(view.tx, view.ty, 0)

    floorUniforms.uTime.value = t
    sunUniforms.uTime.value = t
    beamUniforms.uTime.value = t
    cat.position.set(0, CAT / 2 - 0.06 + Math.sin(t * 1.05) * 0.07, 0)
    rings.forEach((m, i) => {
      m.material.opacity = 0.8 + 0.2 * Math.sin(t * 2 + i * 1.7)
    })
    shuttles.forEach((s, i) => {
      const [x, y, z] = placements.shuttles[i]
      s.position.set(x, y + Math.sin(t * 0.9 + i * 2.1) * 0.14, z)
      s.rotation.set(0.5 + Math.sin(t * 0.5 + i) * 0.25, t * (0.35 + i * 0.12), -0.6 + Math.cos(t * 0.4 + i) * 0.2)
    })
    sprites.forEach((s, i) => {
      const [x, y, z] = placements.sprites[i]
      s.position.set(x, y + Math.sin(t * 0.8 + i * 1.3) * 0.12, z)
      s.material.rotation = Math.sin(t * 0.6 + i) * 0.12
    })
    for (let i = 0; i < dustCount; i++) {
      let y = dustPos[i * 3 + 1] + dustSpeed[i] * dt
      if (y > 5) y = 0
      dustPos[i * 3 + 1] = y
    }
    dustAttr.needsUpdate = true

    if (bloomOn) composer.render()
    else renderer.render(scene, camera)

    // Keep score on the wall clock. Below 45 fps, drop the bloom and the
    // extra pixels; below 26 even then, hand the hero back to CSS.
    const now = performance.now()
    if (now < warmUntil) return
    if (!measuringFrom) measuringFrom = now
    frames++
    if (now - measuringFrom < 2000) return
    const fps = (frames * 1000) / (now - measuringFrom)
    frames = 0
    measuringFrom = now
    if (fps < 45 && bloomOn) {
      bloomOn = false
      renderer.setPixelRatio(1)
      renderer.setSize(width, height, false)
    } else if (fps < 26 && !bloomOn) {
      cancelAnimationFrame(raf)
      raf = 0
      opts.onGiveUp(`${Math.round(fps)} fps`)
      return
    }
    opts.onFps?.(fps, bloomOn)
  }

  function setRunning(on: boolean): void {
    if (on && !raf) {
      clock.start()
      warmUntil = performance.now() + 1500
      measuringFrom = 0
      frames = 0
      frame()
    } else if (!on && raf) {
      cancelAnimationFrame(raf)
      raf = 0
      clock.stop()
    }
  }

  function dispose(): void {
    setRunning(false)
    window.removeEventListener('pointermove', onPointer)
    scene.traverse((o) => {
      const mesh = o as THREE.Mesh
      mesh.geometry?.dispose()
      const mats = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : []
      for (const m of mats) {
        for (const v of Object.values(m)) if (v instanceof THREE.Texture) v.dispose()
        m.dispose()
      }
    })
    composer.dispose()
    renderer.dispose()
    renderer.forceContextLoss()
  }

  return { layout, setRunning, dispose }
}
