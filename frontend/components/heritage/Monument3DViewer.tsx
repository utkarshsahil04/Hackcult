'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { Compass, Minus, Pause, Play, Plus, RotateCcw } from 'lucide-react'
import { architectureParts } from '@/lib/architecture'
import { buildMonument } from './monument-models'

type Props = { monumentId: string; name: string; lang?: 'en' | 'hi'; className?: string }
type Controls = { turn: (d: number) => void; tilt: (d: number) => void; zoom: (f: number) => void; reset: () => void; focus: (i: number) => void; rotate: (on: boolean) => void }

const BACKDROP = 0xeee2cb
const START = { theta: 0.62, phi: 1.1 }

const copy = {
  en: { model: 'Illustrative 3D model, not to scale', parts: 'Parts of this building', hint: 'Tap a number to learn about that part. Drag to turn the model.', pause: 'Pause rotation', play: 'Rotate model', reset: 'Reset view', zoomIn: 'Zoom in', zoomOut: 'Zoom out', none: 'The 3D model can’t run on this device. The list of parts below still works.', label: (name: string) => `3D model of ${name}. Use the arrow keys to turn it and plus or minus to zoom.` },
  hi: { model: 'चित्रात्मक 3D मॉडल, अनुपात सटीक नहीं', parts: 'इस इमारत के भाग', hint: 'किसी भाग के बारे में जानने के लिए उसका नंबर चुनें। मॉडल घुमाने के लिए खींचें।', pause: 'घूमना रोकें', play: 'मॉडल घुमाएं', reset: 'दृश्य रीसेट करें', zoomIn: 'पास लाएं', zoomOut: 'दूर ले जाएं', none: 'यह 3D मॉडल इस उपकरण पर नहीं चल सकता। नीचे भागों की सूची फिर भी उपलब्ध है।', label: (name: string) => `${name} का 3D मॉडल। घुमाने के लिए तीर कुंजियां और ज़ूम के लिए प्लस या माइनस दबाएं।` },
}

export function Monument3DViewer({ monumentId, name, lang = 'en', className = '' }: Props) {
  const stageRef = useRef<HTMLDivElement | null>(null)
  const pinRefs = useRef<(HTMLButtonElement | null)[]>([])
  const controls = useRef<Controls | null>(null)
  const model = useMemo(() => buildMonument(monumentId), [monumentId])
  const [active, setActive] = useState<number | null>(null)
  const [rotating, setRotating] = useState(true)
  const [failed, setFailed] = useState(false)
  const text = copy[lang]

  useEffect(() => () => model.dispose(), [model])

  useEffect(() => {
    const stage = stageRef.current
    if (!stage) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true })
    } catch {
      queueMicrotask(() => setFailed(true))
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.08
    const canvas = renderer.domElement
    canvas.className = 'absolute inset-0 size-full'
    stage.prepend(canvas)

    const box = new THREE.Box3().setFromObject(model.group)
    const center = box.getCenter(new THREE.Vector3())
    const fit = box.getBoundingSphere(new THREE.Sphere()).radius

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(BACKDROP)
    // The fog only fades the display floor into the backdrop. It starts beyond the far side of the model.
    scene.fog = new THREE.Fog(BACKDROP, fit * 4.5, fit * 8)
    scene.add(new THREE.HemisphereLight(0xfff6e6, 0xb9a27e, 1.25))
    const sun = new THREE.DirectionalLight(0xffe6c4, 2.5)
    sun.position.copy(center).add(new THREE.Vector3(fit * 0.9, fit * 1.5, fit * 0.7))
    sun.target.position.copy(center)
    sun.castShadow = true
    sun.shadow.mapSize.setScalar(window.innerWidth < 768 ? 1024 : 2048)
    sun.shadow.bias = -0.0004
    sun.shadow.normalBias = 0.02
    Object.assign(sun.shadow.camera, { left: -fit * 1.25, right: fit * 1.25, top: fit * 1.25, bottom: -fit * 1.25, near: 0.1, far: fit * 4 })
    scene.add(sun, sun.target)
    const floor = new THREE.Mesh(new THREE.CircleGeometry(fit * 6, 48).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xdfcdaa, roughness: 1 }))
    floor.position.set(center.x, box.min.y - 0.02, center.z)
    floor.receiveShadow = true
    scene.add(model.group, floor)

    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, fit * 12)
    // Closer than the whole bounding sphere: it is dominated by the flat ground, which is seen at an angle.
    const home = fit / Math.sin(THREE.MathUtils.degToRad(18)) * 0.82
    const opening = model.view ?? START
    const view = { ...opening, radius: home }
    const goal: { theta: number | null; phi: number | null } = { theta: null, phi: null }
    let auto = !reduced
    let dragging = false
    let last = { x: 0, y: 0 }
    let dirty = true
    let visible = true
    let width = 1
    let height = 1

    const spots = model.spots.map((spot) => new THREE.Vector3(...spot.at))
    const scratch = new THREE.Vector3()
    const toCamera = new THREE.Vector3()
    const toSpot = new THREE.Vector3()

    function placePins() {
      toCamera.copy(camera.position).sub(center).normalize()
      spots.forEach((spot, i) => {
        const pin = pinRefs.current[i]
        if (!pin) return
        scratch.copy(spot).project(camera)
        const x = (scratch.x + 1) * 0.5 * width
        const y = (1 - scratch.y) * 0.5 * height
        toSpot.copy(spot).sub(center).setY(0).normalize()
        const away = toSpot.dot(toCamera) < -0.25
        pin.style.transform = `translate3d(${x - 24}px, ${y - 24}px, 0)`
        pin.style.opacity = away ? '.4' : '1'
        pin.style.visibility = x < 8 || y < 8 || x > width - 8 || y > height - 8 ? 'hidden' : 'visible'
      })
    }

    function resize() {
      width = stage!.clientWidth || 1
      height = stage!.clientHeight || 1
      camera.aspect = width / height
      // Narrow stages need the camera further back to keep the whole model in frame.
      camera.fov = camera.aspect < 1 ? 36 / Math.max(camera.aspect, 0.55) : 36
      camera.updateProjectionMatrix()
      renderer.setSize(width, height, false)
      dirty = true
    }
    const observer = new ResizeObserver(resize)
    observer.observe(stage)
    resize()

    const sight = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; dirty = true })
    sight.observe(stage)

    let frame = 0
    let previous = performance.now()
    function animate(now: number) {
      frame = requestAnimationFrame(animate)
      const dt = Math.min((now - previous) / 1000, 0.1)
      previous = now
      if (!visible) return
      if (auto && !dragging && goal.theta === null) {
        view.theta += dt * 0.16
        dirty = true
      }
      if (goal.theta !== null) {
        const ease = reduced ? 1 : 1 - Math.exp(-dt * 4.5)
        view.theta += (goal.theta - view.theta) * ease
        view.phi += ((goal.phi ?? view.phi) - view.phi) * ease
        if (Math.abs(goal.theta - view.theta) < 0.002) goal.theta = null
        dirty = true
      }
      if (!dirty) return
      dirty = false
      camera.position.set(
        center.x + view.radius * Math.sin(view.phi) * Math.sin(view.theta),
        center.y + view.radius * Math.cos(view.phi),
        center.z + view.radius * Math.sin(view.phi) * Math.cos(view.theta),
      )
      camera.lookAt(center)
      camera.updateMatrixWorld()
      renderer.render(scene, camera)
      placePins()
    }
    frame = requestAnimationFrame(animate)

    const clampPhi = (phi: number) => THREE.MathUtils.clamp(phi, 0.35, 1.5)
    const onDown = (event: PointerEvent) => {
      dragging = true
      last = { x: event.clientX, y: event.clientY }
      goal.theta = null
      canvas.setPointerCapture(event.pointerId)
    }
    const onMove = (event: PointerEvent) => {
      if (!dragging) return
      view.theta -= (event.clientX - last.x) * 0.007
      // On touch, vertical movement scrolls the page, so only a mouse or pen tilts the view.
      if (event.pointerType !== 'touch') view.phi = clampPhi(view.phi - (event.clientY - last.y) * 0.005)
      last = { x: event.clientX, y: event.clientY }
      dirty = true
    }
    const onUp = () => { dragging = false }
    // Plain scrolling must keep moving the page. Trackpad pinches arrive with ctrlKey set.
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey) return
      event.preventDefault()
      controls.current?.zoom(1 + event.deltaY * 0.004)
    }
    canvas.addEventListener('pointerdown', onDown)
    canvas.addEventListener('pointermove', onMove)
    canvas.addEventListener('pointerup', onUp)
    canvas.addEventListener('pointercancel', onUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })

    controls.current = {
      turn: (d) => { goal.theta = null; view.theta += d; dirty = true },
      tilt: (d) => { view.phi = clampPhi(view.phi + d); dirty = true },
      zoom: (f) => { view.radius = THREE.MathUtils.clamp(view.radius * f, home * 0.35, home * 1.25); dirty = true },
      reset: () => { goal.theta = opening.theta; goal.phi = opening.phi; view.theta %= Math.PI * 2; view.radius = home; dirty = true },
      focus: (i) => {
        const spot = spots[i]
        const azimuth = Math.atan2(spot.x - center.x, spot.z - center.z)
        // Take the short way round to the angle that faces this part.
        const delta = Math.atan2(Math.sin(azimuth - view.theta), Math.cos(azimuth - view.theta))
        goal.theta = view.theta + delta
        goal.phi = clampPhi(Math.max(view.phi, 0.95))
        auto = false
        dirty = true
      },
      rotate: (on) => { auto = on; dirty = true },
    }

    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      sight.disconnect()
      controls.current = null
      canvas.removeEventListener('pointerdown', onDown)
      canvas.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerup', onUp)
      canvas.removeEventListener('pointercancel', onUp)
      canvas.removeEventListener('wheel', onWheel)
      scene.remove(model.group)
      floor.geometry.dispose()
      ;(floor.material as THREE.Material).dispose()
      sun.shadow.map?.dispose()
      renderer.dispose()
      canvas.remove()
    }
  }, [model])

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) queueMicrotask(() => setRotating(false))
    queueMicrotask(() => setActive(null))
  }, [monumentId])

  function choose(index: number) {
    if (active === index) {
      setActive(null)
      return
    }
    setActive(index)
    setRotating(false)
    controls.current?.focus(index)
  }

  function toggleRotation() {
    controls.current?.rotate(!rotating)
    setRotating(!rotating)
  }

  function onKeyDown(event: React.KeyboardEvent) {
    const action: Record<string, () => void> = {
      ArrowLeft: () => controls.current?.turn(-0.2),
      ArrowRight: () => controls.current?.turn(0.2),
      ArrowUp: () => controls.current?.tilt(-0.1),
      ArrowDown: () => controls.current?.tilt(0.1),
      '+': () => controls.current?.zoom(0.88),
      '=': () => controls.current?.zoom(0.88),
      '-': () => controls.current?.zoom(1.14),
    }
    if (action[event.key]) {
      event.preventDefault()
      action[event.key]()
    }
  }

  const activePart = active === null ? null : architectureParts[model.spots[active]?.part]
  const iconButton = 'grid size-12 place-items-center rounded-full text-[#1F1A14] transition-colors hover:bg-[#EADBC0]'

  return (
    <div className={`flex flex-col overflow-hidden rounded-2xl border border-[#E8A317]/50 bg-[#FBF6EC] shadow-xl ${className}`} data-testid="monument-3d">
      <div
        aria-label={text.label(name)}
        className="relative h-[360px] w-full cursor-grab touch-pan-y select-none overflow-hidden bg-[#EEE2CB] active:cursor-grabbing focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[#E8A317] sm:h-[420px] lg:h-[min(440px,50vh)]"
        onKeyDown={onKeyDown}
        ref={stageRef}
        role="group"
        tabIndex={0}
      >
        {failed && <p className="absolute inset-0 grid place-items-center p-8 text-center text-sm text-[#5A4E3F]">{text.none}</p>}
        {!failed && model.spots.map((spot, i) => (
          <button
            aria-hidden="true"
            className="group absolute left-0 top-0 z-10 grid size-12 place-items-center rounded-full transition-opacity"
            key={`${spot.part}-${i}`}
            onClick={() => choose(i)}
            ref={(node) => { pinRefs.current[i] = node }}
            tabIndex={-1}
            type="button"
          >
            <span className={`grid size-7 place-items-center rounded-full border-2 border-[#FBF6EC] text-xs font-bold shadow-md transition-transform group-hover:scale-110 ${active === i ? 'scale-110 bg-[#E8A317] text-[#1F1A14]' : 'bg-[#B5452B] text-[#FBF6EC]'}`}>{i + 1}</span>
          </button>
        ))}
        <p className="pointer-events-none absolute left-3 top-3 z-20 max-w-[60%] rounded-full bg-[#FBF6EC]/90 px-3 py-1.5 text-[11px] font-semibold leading-tight text-[#8F3221] shadow-sm backdrop-blur">{text.model}</p>
        {!failed && (
          <div className="absolute right-2 top-2 z-20 flex flex-col items-center rounded-full border border-[#E8A317]/30 bg-[#FBF6EC]/90 shadow-sm backdrop-blur">
            <button aria-label={rotating ? text.pause : text.play} className={iconButton} onClick={toggleRotation} title={rotating ? text.pause : text.play} type="button">{rotating ? <Pause aria-hidden="true" size={16} /> : <Play aria-hidden="true" size={16} />}</button>
            <button aria-label={text.zoomIn} className={iconButton} onClick={() => controls.current?.zoom(0.8)} title={text.zoomIn} type="button"><Plus aria-hidden="true" size={16} /></button>
            <button aria-label={text.zoomOut} className={iconButton} onClick={() => controls.current?.zoom(1.25)} title={text.zoomOut} type="button"><Minus aria-hidden="true" size={16} /></button>
            <button aria-label={text.reset} className={iconButton} onClick={() => { setActive(null); controls.current?.reset() }} title={text.reset} type="button"><RotateCcw aria-hidden="true" size={16} /></button>
          </div>
        )}
      </div>

      <div className="border-t border-[#E8A317]/25 p-3">
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-[#8F3221]"><Compass aria-hidden="true" className="text-[#E8A317]" size={13} />{text.parts}</p>
        <div className="flex flex-wrap gap-1.5">
          {model.spots.map((spot, i) => (
            <button
              aria-pressed={active === i}
              className={`inline-flex min-h-12 items-center gap-2 rounded-full border px-3 text-xs font-medium transition-colors ${active === i ? 'border-[#B5452B] bg-[#B5452B] text-[#FBF6EC]' : 'border-[#E8A317]/40 bg-[#EADBC0]/40 text-[#1F1A14] hover:bg-[#E8A317]/20'}`}
              key={`${spot.part}-${i}`}
              onClick={() => choose(i)}
              type="button"
            >
              <span aria-hidden="true" className="font-bold">{i + 1}</span>
              {architectureParts[spot.part].title[lang]}
            </button>
          ))}
        </div>
        <div aria-live="polite" className="mt-2.5 min-h-16 rounded-xl border border-[#E8A317]/40 bg-[#FBF6EC] p-3 text-sm leading-relaxed text-[#5A4E3F]">
          {activePart ? <><p className="fraunces text-base text-[#1F1A14]">{activePart.title[lang]}</p><p className="mt-0.5">{activePart.desc[lang]}</p></> : <p>{text.hint}</p>}
        </div>
      </div>
    </div>
  )
}

export default Monument3DViewer
