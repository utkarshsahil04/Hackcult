'use client'

import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { Box, Compass, RotateCw } from 'lucide-react'

type Props = {
  monumentId: string
  lang?: 'en' | 'hi'
  className?: string
}

type Hotspot = {
  id: string
  title: { en: string; hi: string }
  desc: { en: string; hi: string }
  position: [number, number, number]
}

const monumentHotspots: Record<string, Hotspot[]> = {
  'taj-mahal': [
    {
      id: 'dome',
      title: { en: 'Central Onion Dome (Amrud)', hi: 'मुख्य संगमरमरी गुंबद' },
      desc: {
        en: 'A double dome soaring 35m, designed with an inner acoustic ceiling and outer visual shell topped with a lotus finial.',
        hi: '35 मीटर ऊंचा दोहरा गुंबद, आंतरिक ध्वनिक छत और कमल के कलश वाले बाहरी आवरण से निर्मित।',
      },
      position: [0, 4.2, 0],
    },
    {
      id: 'minarets',
      title: { en: 'Outward-Tilting Minarets', hi: 'बाहर की ओर झुकी चार मीनारें' },
      desc: {
        en: 'Four 40m minarets erected with a deliberate 2-degree outward tilt so that in earthquakes they collapse away from the tomb.',
        hi: '40 मीटर ऊंची मीनारें जानबूझकर 2 डिग्री बाहर की ओर झुकाई गईं ताकि भूकंप में मकबरे को क्षति न पहुंचे।',
      },
      position: [3.8, 2.5, 3.8],
    },
    {
      id: 'iwan',
      title: { en: 'Vaulted Arch (Pishtaq)', hi: 'पिश्ताक (भव्य मेहराब)' },
      desc: {
        en: 'Monumental recessed gateway featuring geometric Pietra Dura floral inlay and Quranic calligraphy in black marble.',
        hi: 'भव्य मेहराबी प्रवेश द्वार जिस पर पिएट्रा ड्यूरा की जड़ाऊ नक्काशी और सुलेख अंकित है।',
      },
      position: [0, 1.2, 2.1],
    },
    {
      id: 'plinth',
      title: { en: 'Elevated Marble Plinth', hi: 'ऊंचा संगमरमर चबूतरा' },
      desc: {
        en: 'A raised platform isolating the sacred monument above the flood line of the adjacent Yamuna river.',
        hi: 'यमुना नदी के बाढ़ स्तर से ऊपर स्मारक को सुरक्षित रखने वाला उठा हुआ चबूतरा।',
      },
      position: [2.5, -0.6, 2.5],
    },
  ],
  'qutub-minar': [
    {
      id: 'storeys',
      title: { en: 'Tapering Fluted Storeys', hi: 'क्रमशः संकरी होती 5 मंजिलें' },
      desc: {
        en: '72.5m tower of red and buff sandstone with alternating angular and rounded flutings on the lower tiers.',
        hi: '72.5 मीटर ऊंचा लाल व बलुआ पत्थर का विजय स्तंभ, जिसकी निचली मंजिलों पर कोणीय व गोल धारियां हैं।',
      },
      position: [0, 2.5, 0],
    },
    {
      id: 'balconies',
      title: { en: 'Projecting Muqarnas Balconies', hi: 'मुकरना आधारित छज्जे' },
      desc: {
        en: 'Cantilevered balconies supported by intricate stalactite-vault corbels and Arabic inscriptional friezes.',
        hi: 'बारीक नक्काशीदार कोष्ठकों और सुलेख पट्टियों पर टिके हुए बाहर निकले झरोखे।',
      },
      position: [0, 1.0, 1.2],
    },
  ],
}

export function Monument3DViewer({ monumentId, lang = 'en', className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [activeHotspot, setActiveHotspot] = useState<Hotspot | null>(null)
  const [autoRotate, setAutoRotate] = useState(true)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xeadbc0)

    // Camera setup
    const width = container.clientWidth || 400
    const height = container.clientHeight || 340
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
    camera.position.set(6.5, 5.0, 8.5)
    camera.lookAt(0, 1.5, 0)

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    container.innerHTML = ''
    container.appendChild(renderer.domElement)

    // Lights
    const ambientLight = new THREE.AmbientLight(0xfff5ea, 0.75)
    scene.add(ambientLight)

    const sunLight = new THREE.DirectionalLight(0xffecd2, 1.4)
    sunLight.position.set(8, 12, 6)
    sunLight.castShadow = true
    sunLight.shadow.mapSize.width = 1024
    sunLight.shadow.mapSize.height = 1024
    scene.add(sunLight)

    const fillLight = new THREE.DirectionalLight(0xd9c4a1, 0.6)
    fillLight.position.set(-8, 4, -6)
    scene.add(fillLight)

    // Architectural Group
    const modelGroup = new THREE.Group()
    scene.add(modelGroup)

    // Materials
    const marbleWhite = new THREE.MeshStandardMaterial({
      color: 0xfcf9f2,
      roughness: 0.28,
      metalness: 0.05,
    })
    const sandstoneRed = new THREE.MeshStandardMaterial({
      color: 0xb5452b,
      roughness: 0.65,
      metalness: 0.05,
    })
    const goldMaterial = new THREE.MeshStandardMaterial({
      color: 0xe8a317,
      roughness: 0.2,
      metalness: 0.8,
    })
    const basePlinthMat = new THREE.MeshStandardMaterial({
      color: 0xdfd2be,
      roughness: 0.5,
    })
    const waterMat = new THREE.MeshStandardMaterial({
      color: 0x6ba4b8,
      roughness: 0.1,
      metalness: 0.6,
      transparent: true,
      opacity: 0.85,
    })

    // Ground platform
    const groundGeo = new THREE.BoxGeometry(12, 0.2, 12)
    const groundMesh = new THREE.Mesh(groundGeo, basePlinthMat)
    groundMesh.position.y = -0.6
    groundMesh.receiveShadow = true
    modelGroup.add(groundMesh)

    // Procedural reconstructions
    if (monumentId === 'qutub-minar') {
      // Qutub Minar 5-storey tapering tower
      const storeys = [
        { bottomR: 1.4, topR: 1.2, h: 1.8, y: 0.3, mat: sandstoneRed },
        { bottomR: 1.2, topR: 1.0, h: 1.5, y: 1.95, mat: sandstoneRed },
        { bottomR: 1.0, topR: 0.8, h: 1.3, y: 3.35, mat: marbleWhite },
        { bottomR: 0.8, topR: 0.65, h: 1.1, y: 4.55, mat: marbleWhite },
        { bottomR: 0.65, topR: 0.5, h: 0.9, y: 5.55, mat: sandstoneRed },
      ]

      storeys.forEach((s) => {
        const geo = new THREE.CylinderGeometry(s.topR, s.bottomR, s.h, 28)
        const mesh = new THREE.Mesh(geo, s.mat)
        mesh.position.y = s.y
        mesh.castShadow = true
        mesh.receiveShadow = true
        modelGroup.add(mesh)

        // Balcony ring
        const ringGeo = new THREE.CylinderGeometry(s.bottomR * 1.18, s.bottomR * 1.18, 0.14, 28)
        const ring = new THREE.Mesh(ringGeo, goldMaterial)
        ring.position.y = s.y - s.h / 2 + 0.07
        ring.castShadow = true
        modelGroup.add(ring)
      })

      // Top cupola finial
      const cupolaGeo = new THREE.ConeGeometry(0.5, 0.8, 20)
      const cupola = new THREE.Mesh(cupolaGeo, goldMaterial)
      cupola.position.y = 6.4
      modelGroup.add(cupola)
    } else {
      // Default: Taj Mahal Reconstructed Model
      // 1. Plinth (square marble terrace)
      const plinthGeo = new THREE.BoxGeometry(6.6, 0.45, 6.6)
      const plinth = new THREE.Mesh(plinthGeo, marbleWhite)
      plinth.position.y = -0.3
      plinth.castShadow = true
      plinth.receiveShadow = true
      modelGroup.add(plinth)

      // 2. Main Tomb Cube with Chamfered Corners
      const tombGeo = new THREE.BoxGeometry(3.6, 2.6, 3.6)
      const tomb = new THREE.Mesh(tombGeo, marbleWhite)
      tomb.position.y = 1.05
      tomb.castShadow = true
      tomb.receiveShadow = true
      modelGroup.add(tomb)

      // 3. Vaulted Iwans (Recessed Arches) on 4 faces
      const iwanMat = new THREE.MeshStandardMaterial({
        color: 0x5a4e3f,
        roughness: 0.6,
      })
      const iwanGeo = new THREE.BoxGeometry(1.4, 1.8, 0.25)
      const offsets: [number, number, number, number][] = [
        [0, 1.1, 1.8, 0], // front
        [0, 1.1, -1.8, 0], // back
        [1.8, 1.1, 0, Math.PI / 2], // right
        [-1.8, 1.1, 0, Math.PI / 2], // left
      ]
      offsets.forEach(([x, y, z, rot]) => {
        const archMesh = new THREE.Mesh(iwanGeo, iwanMat)
        archMesh.position.set(x, y, z)
        archMesh.rotation.y = rot
        modelGroup.add(archMesh)
      })

      // 4. Central Drum (Cylinder below dome)
      const drumGeo = new THREE.CylinderGeometry(1.3, 1.3, 0.7, 32)
      const drum = new THREE.Mesh(drumGeo, marbleWhite)
      drum.position.y = 2.7
      drum.castShadow = true
      modelGroup.add(drum)

      // 5. Bulbous Onion Dome (Amrud)
      const domeGeo = new THREE.SphereGeometry(1.35, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.68)
      const dome = new THREE.Mesh(domeGeo, marbleWhite)
      dome.position.y = 3.05
      dome.scale.set(1.0, 1.25, 1.0)
      dome.castShadow = true
      modelGroup.add(dome)

      // 6. Brass Kalasa Finial
      const finialPole = new THREE.CylinderGeometry(0.04, 0.04, 0.8, 12)
      const finial = new THREE.Mesh(finialPole, goldMaterial)
      finial.position.y = 4.65
      modelGroup.add(finial)

      const finialBall = new THREE.SphereGeometry(0.12, 16, 16)
      const ball = new THREE.Mesh(finialBall, goldMaterial)
      ball.position.y = 4.8
      modelGroup.add(ball)

      // 7. Corner Chattris (4 Pavilions around main dome)
      const chattriPositions: [number, number][] = [
        [1.2, 1.2],
        [-1.2, 1.2],
        [1.2, -1.2],
        [-1.2, -1.2],
      ]
      chattriPositions.forEach(([cx, cz]) => {
        const cDrum = new THREE.CylinderGeometry(0.32, 0.32, 0.45, 16)
        const cDrumMesh = new THREE.Mesh(cDrum, marbleWhite)
        cDrumMesh.position.set(cx, 2.58, cz)
        modelGroup.add(cDrumMesh)

        const cDome = new THREE.SphereGeometry(0.34, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.5)
        const cDomeMesh = new THREE.Mesh(cDome, marbleWhite)
        cDomeMesh.position.set(cx, 2.8, cz)
        modelGroup.add(cDomeMesh)
      })

      // 8. Four Corner Minarets with Outward 2-degree Tilt
      const minaretPositions: [number, number, number, number][] = [
        [2.8, 2.8, 0.035, -0.035],
        [-2.8, 2.8, 0.035, 0.035],
        [2.8, -2.8, -0.035, -0.035],
        [-2.8, -2.8, -0.035, 0.035],
      ]
      minaretPositions.forEach(([mx, mz, rotX, rotZ]) => {
        const mGroup = new THREE.Group()
        mGroup.position.set(mx, -0.07, mz)
        mGroup.rotation.x = rotX
        mGroup.rotation.z = rotZ

        // Shaft (tapering cylinder)
        const mGeo = new THREE.CylinderGeometry(0.2, 0.32, 3.8, 20)
        const mMesh = new THREE.Mesh(mGeo, marbleWhite)
        mMesh.position.y = 1.9
        mMesh.castShadow = true
        mGroup.add(mMesh)

        // Minaret Balconies
        ;[1.0, 2.1, 3.1].forEach((by) => {
          const bGeo = new THREE.CylinderGeometry(0.34, 0.34, 0.09, 16)
          const bMesh = new THREE.Mesh(bGeo, goldMaterial)
          bMesh.position.y = by
          mGroup.add(bMesh)
        })

        // Cupola on top
        const topDome = new THREE.SphereGeometry(0.24, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.5)
        const topDomeMesh = new THREE.Mesh(topDome, marbleWhite)
        topDomeMesh.position.y = 3.9
        mGroup.add(topDomeMesh)

        modelGroup.add(mGroup)
      })

      // 9. Charbagh Front Reflecting Pool (Water Channel)
      const poolGeo = new THREE.BoxGeometry(2.0, 0.06, 3.8)
      const pool = new THREE.Mesh(poolGeo, waterMat)
      pool.position.set(0, -0.48, 4.4)
      modelGroup.add(pool)
    }

    // Interactive Drag Orbit & Touch controls
    let isDragging = false
    let prevMouseX = 0
    let prevMouseY = 0
    let rotationSpeedY = 0
    let rotationSpeedX = 0

    const onPointerDown = (e: PointerEvent) => {
      isDragging = true
      prevMouseX = e.clientX
      prevMouseY = e.clientY
    }

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return
      const deltaX = e.clientX - prevMouseX
      const deltaY = e.clientY - prevMouseY
      prevMouseX = e.clientX
      prevMouseY = e.clientY

      rotationSpeedY = deltaX * 0.006
      rotationSpeedX = deltaY * 0.003
      modelGroup.rotation.y += rotationSpeedY
      camera.position.y = Math.max(1.5, Math.min(10, camera.position.y - rotationSpeedX * 4))
      camera.lookAt(0, 1.5, 0)
    }

    const onPointerUp = () => {
      isDragging = false
    }

    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const zoomFactor = e.deltaY * 0.004
      const newDistance = camera.position.length() + zoomFactor
      if (newDistance > 4.5 && newDistance < 18) {
        camera.position.multiplyScalar(newDistance / camera.position.length())
      }
    }

    container.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
    container.addEventListener('wheel', onWheel, { passive: false })

    // Responsive resize handler
    const onResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    // Animation Loop
    let animId = 0
    const animate = () => {
      animId = requestAnimationFrame(animate)

      // Idle auto-rotation when not interacting
      if (autoRotate && !isDragging) {
        modelGroup.rotation.y += 0.0045
      }

      // Smooth inertia decay when user releases drag
      if (!isDragging && Math.abs(rotationSpeedY) > 0.0001) {
        modelGroup.rotation.y += rotationSpeedY
        rotationSpeedY *= 0.92
      }

      renderer.render(scene, camera)
    }
    animate()

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      container.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', onPointerUp)
      container.removeEventListener('wheel', onWheel)
      renderer.dispose()
      if (container) container.innerHTML = ''
    }
  }, [monumentId, autoRotate])

  const hotspots = monumentHotspots[monumentId] ?? monumentHotspots['taj-mahal']

  return (
    <div className={`relative flex flex-col overflow-hidden rounded-2xl border border-[#E8A317]/50 bg-[#EADBC0] shadow-xl ${className}`}>
      {/* Label Badge */}
      <div className="absolute left-3 top-3 z-10 flex items-center gap-2 rounded-full border border-[#E8A317]/40 bg-[#FBF6EC]/90 px-3 py-1 text-xs font-semibold text-[#8F3221] shadow-sm backdrop-blur">
        <Box size={13} className="text-[#E8A317]" aria-hidden="true" />
        <span>{lang === 'hi' ? '3D वास्तुकला पुनर्निर्माण' : '3D Architectural Reconstruction'}</span>
      </div>

      {/* Control Buttons */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-1.5 rounded-full border border-[#E8A317]/30 bg-[#FBF6EC]/90 p-1 shadow-sm backdrop-blur">
        <button
          onClick={() => setAutoRotate((v) => !v)}
          className={`grid size-8 place-items-center rounded-full transition-colors ${autoRotate ? 'bg-[#E8A317] text-[#1F1A14]' : 'text-[#5A4E3F] hover:bg-[#EADBC0]'}`}
          title={autoRotate ? 'Pause rotation' : 'Auto rotate'}
          type="button"
        >
          <RotateCw size={14} className={autoRotate ? 'animate-spin' : ''} style={{ animationDuration: '6s' }} />
        </button>
      </div>

      {/* 3D WebGL Canvas Viewport */}
      <div
        ref={containerRef}
        className="h-[360px] sm:h-[420px] lg:h-[480px] w-full cursor-grab active:cursor-grabbing touch-none select-none"
        aria-label="Interactive 3D model"
      />

      {/* Hotspot Chips */}
      <div className="relative z-10 border-t border-[#E8A317]/25 bg-[#FBF6EC]/95 p-3">
        <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-[#8F3221]">
          <Compass size={13} className="text-[#E8A317]" />
          <span>{lang === 'hi' ? 'वास्तुशिल्प विशेषताएं (क्लिक करें):' : 'Architectural Hotspots (tap to inspect):'}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {hotspots.map((h) => {
            const isSelected = activeHotspot?.id === h.id
            return (
              <button
                key={h.id}
                onClick={() => setActiveHotspot(isSelected ? null : h)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  isSelected
                    ? 'bg-[#B5452B] text-[#FBF6EC] shadow-sm'
                    : 'border border-[#E8A317]/40 bg-[#EADBC0]/50 text-[#1F1A14] hover:bg-[#E8A317]/20'
                }`}
                type="button"
              >
                {h.title[lang]}
              </button>
            )
          })}
        </div>

        {/* Selected Hotspot Explanation Panel */}
        {activeHotspot && (
          <div className="mt-2.5 rounded-xl border border-[#E8A317]/50 bg-[#FBF6EC] p-3 text-xs leading-relaxed text-[#5A4E3F] shadow-sm">
            <p className="font-semibold text-[#1F1A14]">{activeHotspot.title[lang]}</p>
            <p className="mt-0.5">{activeHotspot.desc[lang]}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Monument3DViewer
