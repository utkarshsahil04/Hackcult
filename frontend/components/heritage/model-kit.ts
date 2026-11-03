import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import type { PartId } from '@/lib/architecture'

export type Spot = { part: PartId; at: [number, number, number] }
export type MonumentModel = { group: THREE.Group; spots: Spot[]; view?: { theta: number; phi: number }; dispose: () => void }

const MATERIALS = {
  marble: { color: 0xf7f1e4, roughness: 0.38 },
  marbleShade: { color: 0xe6dcc6, roughness: 0.55 },
  shell: { color: 0xfbf9f3, roughness: 0.42, side: THREE.DoubleSide },
  redstone: { color: 0xab4a2d, roughness: 0.8 },
  redLight: { color: 0xc26a49, roughness: 0.82 },
  buff: { color: 0xd8b888, roughness: 0.85 },
  rubble: { color: 0x9c8f7c, roughness: 0.96 },
  rubbleDark: { color: 0x7b6f60, roughness: 0.96 },
  pink: { color: 0xd9a483, roughness: 0.72 },
  plaster: { color: 0xc4543a, roughness: 0.85 },
  black: { color: 0x2b2826, roughness: 0.32 },
  niche: { color: 0x3b2d23, roughness: 0.9 },
  gold: { color: 0xd8a32b, roughness: 0.32, metalness: 0.75 },
  copper: { color: 0x5c6f63, roughness: 0.55, metalness: 0.35 },
  water: { color: 0x6c9eb3, roughness: 0.12, metalness: 0.35 },
  lawn: { color: 0x7e9b56, roughness: 0.96 },
  path: { color: 0xd8c5a2, roughness: 0.95 },
  paving: { color: 0xc9a285, roughness: 0.92 },
  sand: { color: 0xdcc8a4, roughness: 1 },
  leaf: { color: 0x567a40, roughness: 0.95 },
  trunk: { color: 0x6a5038, roughness: 0.95 },
  flame: { color: 0xf0802a, roughness: 0.6, emissive: 0xe0601a, emissiveIntensity: 0.9 },
} satisfies Record<string, THREE.MeshStandardMaterialParameters>

export type Mat = keyof typeof MATERIALS
type Vec2 = [number, number]

const UP = new THREE.Vector3(0, 1, 0)

// Pointed arch outline, base centred at the origin, in the XY plane.
function archPath<T extends THREE.Path>(path: T, w: number, h: number, x = 0, y = 0): T {
  const r = w / 2
  const spring = y + Math.max(h - w * 0.72, h * 0.3)
  const top = y + h
  const pull = spring + (top - spring) * 0.68
  path.moveTo(x - r, y)
  path.lineTo(x - r, spring)
  path.quadraticCurveTo(x - r, pull, x, top)
  path.quadraticCurveTo(x + r, pull, x + r, spring)
  path.lineTo(x + r, y)
  path.closePath()
  return path
}

// All geometry is transformed and merged per material, so a model is about ten draw calls however detailed it is.
export class Kit {
  private readonly pieces = new Map<Mat, THREE.BufferGeometry[]>()
  private readonly spots: Spot[] = []
  private matrix = new THREE.Matrix4()
  /** Opening camera angle, for models that only read well from one side. */
  view?: { theta: number; phi: number }

  add(mat: Mat, geometry: THREE.BufferGeometry) {
    const geo = geometry.index ? geometry.toNonIndexed() : geometry
    geo.deleteAttribute('uv')
    geo.applyMatrix4(this.matrix)
    const list = this.pieces.get(mat) ?? []
    list.push(geo)
    this.pieces.set(mat, list)
  }

  /** Run fn with the origin moved, turned about Y, and optionally scaled. */
  at(x: number, y: number, z: number, fn: () => void, turn = 0, scale = 1) {
    const saved = this.matrix.clone()
    const local = new THREE.Matrix4().compose(
      new THREE.Vector3(x, y, z),
      new THREE.Quaternion().setFromAxisAngle(UP, turn),
      new THREE.Vector3(scale, scale, scale),
    )
    this.matrix.multiply(local)
    fn()
    this.matrix = saved
  }

  /** Lean everything in fn away from vertical, by small angles in radians. */
  lean(x: number, z: number, fn: () => void) {
    const saved = this.matrix.clone()
    this.matrix.multiply(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(x, 0, z)))
    fn()
    this.matrix = saved
  }

  /** Run fn once per side of a w x d rectangle, with +z pointing outward and x along that side. fn receives the side length. */
  sides(w: number, d: number, fn: (length: number, side: number) => void) {
    this.at(0, 0, d / 2, () => fn(w, 0))
    this.at(w / 2, 0, 0, () => fn(d, 1), Math.PI / 2)
    this.at(0, 0, -d / 2, () => fn(w, 2), Math.PI)
    this.at(-w / 2, 0, 0, () => fn(d, 3), -Math.PI / 2)
  }

  spot(part: PartId, x: number, y: number, z: number) {
    const v = new THREE.Vector3(x, y, z).applyMatrix4(this.matrix)
    this.spots.push({ part, at: [v.x, v.y, v.z] })
  }

  // ── Primitives. y is always the base of the shape. ─────────────────────────────────
  box(mat: Mat, w: number, h: number, d: number, x = 0, y = 0, z = 0) {
    this.add(mat, new THREE.BoxGeometry(w, h, d).translate(x, y + h / 2, z))
  }

  cyl(mat: Mat, rTop: number, rBottom: number, h: number, x = 0, y = 0, z = 0, segments = 20) {
    this.add(mat, new THREE.CylinderGeometry(rTop, rBottom, h, segments).translate(x, y + h / 2, z))
  }

  lathe(mat: Mat, profile: Vec2[], x = 0, y = 0, z = 0, segments = 28) {
    const points = profile.map(([r, h]) => new THREE.Vector2(Math.max(r, 0.0001), h))
    this.add(mat, new THREE.LatheGeometry(points, segments).translate(x, y, z))
  }

  /** Bulbous Mughal dome. Height is about 1.85 x r x tall. */
  onion(mat: Mat, r: number, x = 0, y = 0, z = 0, tall = 1) {
    const curve = new THREE.SplineCurve(([[0.8, 0], [0.98, 0.18], [1.06, 0.45], [1, 0.78], [0.8, 1.1], [0.48, 1.38], [0.2, 1.6], [0.05, 1.78], [0, 1.85]] as Vec2[]).map(([a, b]) => new THREE.Vector2(a, b)))
    this.lathe(mat, curve.getPoints(22).map((p): Vec2 => [p.x * r, p.y * r * tall]), x, y, z)
  }

  /** Plain hemisphere. squash below 1 flattens it, as on Sultanate-period tombs. */
  hemi(mat: Mat, r: number, x = 0, y = 0, z = 0, squash = 1) {
    const profile: Vec2[] = []
    for (let i = 0; i <= 12; i += 1) {
      const a = (i / 12) * (Math.PI / 2)
      profile.push([Math.cos(a) * r, Math.sin(a) * r * squash])
    }
    this.lathe(mat, profile, x, y, z, 24)
  }

  finial(x = 0, y = 0, z = 0, s = 1) {
    this.cyl('gold', 0.03 * s, 0.05 * s, 0.55 * s, x, y, z, 8)
    this.add('gold', new THREE.SphereGeometry(0.1 * s, 10, 8).translate(x, y + 0.26 * s, z))
    this.add('gold', new THREE.SphereGeometry(0.07 * s, 10, 8).translate(x, y + 0.42 * s, z))
  }

  /** Solid pointed arch on a wall's +z face. Dark, and just proud of the wall, it reads as a recess. */
  arch(mat: Mat, w: number, h: number, x = 0, y = 0, z = 0, depth = 0.04) {
    const geo = new THREE.ExtrudeGeometry(archPath(new THREE.Shape(), w, h), { depth, bevelEnabled: false, curveSegments: 6 })
    this.add(mat, geo.translate(x, y, z))
  }

  /** A row of n arches across span, centred on x. */
  arches(n: number, span: number, h: number, y = 0, z = 0, x = 0, mat: Mat = 'niche', fill = 0.68) {
    const step = span / n
    for (let i = 0; i < n; i += 1) this.arch(mat, step * fill, h, x - span / 2 + step * (i + 0.5), y, z)
  }

  /** Tall arch in a rectangular frame, standing proud of the wall (a pishtaq). */
  portal(frame: Mat, w: number, h: number, y = 0, z = 0, x = 0, proud = 0.15) {
    this.box(frame, w, h, proud, x, y, z + proud / 2)
    this.arch('niche', w * 0.68, h * 0.84, x, y, z + proud)
  }

  /** Block with a real see-through arch, lying in the XY plane and extruded along z from -d/2 to +d/2. */
  gateBlock(mat: Mat, w: number, h: number, d: number, archW: number, archH: number) {
    const shape = new THREE.Shape()
    shape.moveTo(-w / 2, 0)
    shape.lineTo(-w / 2, h)
    shape.lineTo(w / 2, h)
    shape.lineTo(w / 2, 0)
    shape.closePath()
    shape.holes.push(archPath(new THREE.Path(), archW, archH, 0, -0.01))
    this.add(mat, new THREE.ExtrudeGeometry(shape, { depth: d, bevelEnabled: false, curveSegments: 8 }).translate(0, 0, -d / 2))
  }

  /** Arch-shaped band around a real opening, base at y = 0, extruded along z and centred on z. */
  archBand(mat: Mat, w: number, h: number, band: number, d: number, z = 0) {
    const shape = archPath(new THREE.Shape(), w + band * 2, h + band * 1.3, 0, 0)
    shape.holes.push(archPath(new THREE.Path(), w, h, 0, -0.01))
    this.add(mat, new THREE.ExtrudeGeometry(shape, { depth: d, bevelEnabled: false, curveSegments: 8 }).translate(0, 0, z - d / 2))
  }

  /** Square prism with cut corners, as in the plan of many Mughal tombs. */
  chamfered(mat: Mat, w: number, h: number, cut: number, x = 0, y = 0, z = 0) {
    const r = w / 2
    const s = new THREE.Shape()
    s.moveTo(-r + cut, -r)
    s.lineTo(r - cut, -r)
    s.lineTo(r, -r + cut)
    s.lineTo(r, r - cut)
    s.lineTo(r - cut, r)
    s.lineTo(-r + cut, r)
    s.lineTo(-r, r - cut)
    s.lineTo(-r, -r + cut)
    s.closePath()
    this.add(mat, new THREE.ExtrudeGeometry(s, { depth: h, bevelEnabled: false }).rotateX(-Math.PI / 2).translate(x, y, z))
  }

  /** Tapering column whose surface alternates between flutes, as on the Qutb Minar. */
  fluted(mat: Mat, rTop: number, rBottom: number, h: number, flutes: number, y = 0, depth = 0.09) {
    const geo = new THREE.CylinderGeometry(rTop, rBottom, h, flutes * 6, 1, true).translate(0, y + h / 2, 0)
    const pos = geo.attributes.position
    for (let i = 0; i < pos.count; i += 1) {
      const px = pos.getX(i)
      const pz = pos.getZ(i)
      const k = 1 + depth * Math.abs(Math.cos(Math.atan2(pz, px) * flutes / 2))
      pos.setXYZ(i, px * k, pos.getY(i), pz * k)
    }
    geo.computeVertexNormals()
    this.add(mat, geo)
  }

  // ── Architectural parts ────────────────────────────────────────────────────────────
  chhatri(mat: Mat, dome: Mat, s = 1, x = 0, y = 0, z = 0, columns = 4) {
    this.at(x, y, z, () => {
      this.cyl(mat, 0.42 * s, 0.46 * s, 0.07 * s, 0, 0, 0, 12)
      for (let i = 0; i < columns; i += 1) {
        const a = (i / columns) * Math.PI * 2 + Math.PI / 4
        this.cyl(mat, 0.035 * s, 0.045 * s, 0.46 * s, Math.cos(a) * 0.32 * s, 0.07 * s, Math.sin(a) * 0.32 * s, 8)
      }
      this.cyl(mat, 0.48 * s, 0.36 * s, 0.07 * s, 0, 0.53 * s, 0, 12)
      this.onion(dome, 0.33 * s, 0, 0.6 * s, 0)
      this.finial(0, 1.2 * s, 0, 0.5 * s)
    })
  }

  minaret(mat: Mat, h: number, r: number, x = 0, y = 0, z = 0, options: { band?: Mat; dome?: Mat; leanX?: number; leanZ?: number; rings?: number } = {}) {
    const { band = mat, dome = mat, leanX = 0, leanZ = 0, rings = 3 } = options
    this.at(x, y, z, () => this.lean(leanX, leanZ, () => {
      this.cyl(mat, r * 0.72, r, h, 0, 0, 0, 14)
      for (let i = 1; i <= rings; i += 1) {
        const t = i / (rings + 0.15)
        const ring = r * (1 - 0.28 * t)
        this.cyl(band, ring * 1.3, ring * 1.05, h * 0.03, 0, h * t, 0, 14)
      }
      this.chhatri(mat, dome, r * 2.2, 0, h, 0, 8)
    }))
  }

  /** A row of merlons along x, length l, on top of a wall. */
  merlons(mat: Mat, l: number, y: number, z = 0, step = 0.62, w = 0.3, h = 0.28, depth = 0.22) {
    const n = Math.max(1, Math.floor(l / step))
    for (let i = 0; i < n; i += 1) this.box(mat, w, h, depth, -l / 2 + (i + 0.5) * (l / n), y, z)
  }

  /** Straight wall between two points, with battlements. */
  wall(mat: Mat, a: Vec2, b: Vec2, h: number, t: number, y = 0, merlons = true) {
    const length = Math.hypot(b[0] - a[0], b[1] - a[1])
    const turn = -Math.atan2(b[1] - a[1], b[0] - a[0])
    this.at((a[0] + b[0]) / 2, y, (a[1] + b[1]) / 2, () => {
      this.box(mat, length, h, t)
      if (merlons) {
        this.merlons(mat, length, h, t / 2 - 0.11)
        this.merlons(mat, length, h, -t / 2 + 0.11)
      }
    }, turn)
  }

  bastion(mat: Mat, r: number, h: number, x = 0, z = 0, y = 0, batter = 0.84) {
    this.cyl(mat, r * batter, r, h, x, y, z, 16)
    for (let i = 0; i < 10; i += 1) {
      const a = (i / 10) * Math.PI * 2
      this.box(mat, 0.26, 0.26, 0.2, x + Math.cos(a) * r * batter * 0.92, y + h, z + Math.sin(a) * r * batter * 0.92)
    }
  }

  /** Rectangular fort wall with a bastion at each corner and more along the sides. */
  fort(mat: Mat, w: number, d: number, h: number, t = 0.6, r = 0.8, every = 5.5) {
    const corners: Vec2[] = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]
    corners.forEach((c, i) => {
      const next = corners[(i + 1) % 4]
      this.wall(mat, c, next, h, t)
      const length = Math.hypot(next[0] - c[0], next[1] - c[1])
      const extra = Math.floor(length / every)
      for (let k = 1; k < extra; k += 1) this.bastion(mat, r * 0.8, h * 1.05, c[0] + ((next[0] - c[0]) * k) / extra, c[1] + ((next[1] - c[1]) * k) / extra)
      this.bastion(mat, r, h * 1.12, c[0], c[1])
    })
  }

  /** Base slab everything stands on. Its top is at y = 0. */
  ground(w: number, d: number, mat: Mat = 'sand', x = 0, z = 0) {
    this.box(mat, w, 0.25, d, x, -0.25, z)
  }

  /** Garden of four lawns divided by paths with a water channel down the middle of each. */
  charbagh(w: number, d: number, x = 0, z = 0, channel = 0.5) {
    const path = Math.max(channel * 2.4, 0.9)
    this.at(x, 0, z, () => {
      this.box('path', w, 0.03, d)
      const lw = (w - path) / 2
      const ld = (d - path) / 2
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) this.box('lawn', lw - 0.2, 0.08, ld - 0.2, (sx * (lw + path)) / 2, 0, (sz * (ld + path)) / 2)
      this.box('water', channel, 0.05, d - 0.4)
      this.box('water', w - 0.4, 0.05, channel)
    })
  }

  tree(x: number, z: number, s = 1, y = 0) {
    this.cyl('trunk', 0.07 * s, 0.1 * s, 0.7 * s, x, y, z, 6)
    this.add('leaf', new THREE.IcosahedronGeometry(0.6 * s, 1).scale(1, 0.95, 1).translate(x, y + 1.05 * s, z))
  }

  cypress(x: number, z: number, s = 1) {
    this.cyl('trunk', 0.05 * s, 0.06 * s, 0.25 * s, x, 0, z, 6)
    this.add('leaf', new THREE.ConeGeometry(0.26 * s, 1.5 * s, 8).translate(x, 0.95 * s, z))
  }

  build(): MonumentModel {
    const group = new THREE.Group()
    const materials: THREE.Material[] = []
    const geometries: THREE.BufferGeometry[] = []
    for (const [mat, list] of this.pieces) {
      const material = new THREE.MeshStandardMaterial(MATERIALS[mat])
      const merged = mergeGeometries(list, false)
      if (!merged) throw new Error(`could not merge ${mat} geometry`)
      list.forEach((g) => g.dispose())
      const mesh = new THREE.Mesh(merged, material)
      mesh.castShadow = mat !== 'water' && mat !== 'lawn' && mat !== 'path' && mat !== 'sand'
      mesh.receiveShadow = true
      group.add(mesh)
      materials.push(material)
      geometries.push(merged)
    }
    return {
      group,
      spots: this.spots,
      view: this.view,
      dispose: () => {
        geometries.forEach((g) => g.dispose())
        materials.forEach((m) => m.dispose())
      },
    }
  }
}
