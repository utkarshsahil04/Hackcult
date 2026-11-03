import * as THREE from 'three'
import { Kit, type Mat, type MonumentModel } from './model-kit'

// One illustrative model per monument, composed from the parts in model-kit. They show each building's
// form and layout. They are not surveys: proportions are simplified and the viewer says so.

/** A domed tomb on the current origin: chamfered body, a portal on each face, drum, dome and corner chhatris. */
function tomb(k: Kit, o: { w: number; h: number; cut?: number; body: Mat; trim: Mat; dome: Mat; r: number; tall?: number; drum?: number; chhatri?: Mat; chhatriS?: number; onion?: boolean }) {
  const { w, h, cut = w * 0.16, body, trim, dome, r, tall = 1, drum = r * 0.45, chhatri, chhatriS = 1.2, onion = true } = o
  k.chamfered(body, w, h, cut)
  k.sides(w, w, (length) => {
    k.portal(trim, length * 0.44, h * 0.96, 0, 0, 0, 0.14)
    for (const sx of [-1, 1]) for (const level of [0.08, 0.54]) k.arch('niche', length * 0.12, h * 0.34, sx * length * 0.32, h * level, 0)
  })
  k.cyl(trim, w / 2 - cut * 0.4, w / 2 - cut * 0.4, 0.1, 0, h, 0, 8)
  k.cyl(body, r * 0.86, r * 0.9, drum, 0, h, 0, 24)
  if (onion) k.onion(dome, r, 0, h + drum, 0, tall)
  else k.hemi(dome, r, 0, h + drum, 0, tall)
  k.finial(0, h + drum + (onion ? r * 1.85 * tall : r * tall), 0, 1.4)
  if (chhatri) for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri(chhatri, chhatri, chhatriS, sx * w * 0.36, h, sz * w * 0.36)
}

/** Arcaded platform: a solid block with a row of arches on each side. */
function arcadedPlinth(k: Kit, mat: Mat, w: number, h: number, arches: number, trim?: Mat) {
  k.box(mat, w, h, w)
  k.sides(w, w, (length) => k.arches(arches, length - 0.5, h * 0.74, h * 0.05))
  if (trim) k.box(trim, w + 0.1, 0.05, w + 0.1, 0, h, 0)
}

/** Mosque front on the current origin, facing +z: arcade, taller central portal, domes behind. */
function mosque(k: Kit, o: { w: number; h: number; d: number; mat: Mat; trim: Mat; dome: Mat; arches: number; domes: [number, number][]; tall?: number }) {
  const { w, h, d, mat, trim, dome, arches, domes, tall = 1 } = o
  k.box(mat, w, h, d, 0, 0, -d / 2)
  k.arches(arches, w - 0.3, h * 0.72, 0.05, 0)
  k.portal(trim, w * 0.28, h * 1.28, 0, 0, 0, 0.16)
  k.merlons(mat, w, h, 0, 0.45, 0.16, 0.18, 0.12)
  for (const [x, r] of domes) {
    k.cyl(mat, r * 0.88, r * 0.92, r * 0.28, x, h, -d / 2, 20)
    k.onion(dome, r, x, h + r * 0.28, -d / 2, tall)
    k.finial(x, h + r * 0.28 + r * 1.85 * tall, -d / 2, r * 0.8)
  }
}

/** Fort gate facing +z: flanking towers and a real see-through arch. */
function fortGate(k: Kit, o: { w: number; h: number; d?: number; mat: Mat; trim?: Mat; tower: number; dome?: Mat; top?: number }) {
  const { w, h, d = 1.6, mat, trim = mat, tower, dome = mat, top = 3 } = o
  k.gateBlock(mat, w, h, d, w * 0.42, h * 0.66)
  k.arch('niche', w * 0.5, h * 0.74, 0, 0, d / 2)
  k.gateBlock(mat, w, h, 0.08, w * 0.42, h * 0.66)
  for (const sx of [-1, 1]) {
    k.cyl(mat, tower * 0.86, tower, h * 1.12, sx * (w / 2 + tower * 0.5), 0, d / 2 - 0.1, 8)
    k.chhatri(trim, dome, tower * 1.5, sx * (w / 2 + tower * 0.5), h * 1.12, d / 2 - 0.1, 8)
  }
  for (let i = 0; i < top; i += 1) k.chhatri(trim, dome, 0.8, -w * 0.3 + (top > 1 ? (i * w * 0.6) / (top - 1) : w * 0.3), h, d / 2 - 0.5)
}

function pillaredHall(k: Kit, mat: Mat, roof: Mat, w: number, h: number, d: number, nx: number, nz: number) {
  for (let i = 0; i < nx; i += 1) for (let j = 0; j < nz; j += 1) k.box(mat, 0.16, h, 0.16, -w / 2 + (i * w) / (nx - 1), 0, -d / 2 + (j * d) / (nz - 1))
  k.box(roof, w + 0.5, 0.14, d + 0.5, 0, h, 0)
  k.box(roof, w + 0.1, 0.18, d + 0.1, 0, h + 0.14, 0)
}

function baoli(k: Kit) {
  const width = 6
  const length = 18
  const depth = 6
  for (const sx of [-1, 1]) {
    k.box('rubbleDark', 2.4, depth, length + 2.4, sx * (width / 2 + 1.2), -depth)
    k.at(sx * (width / 2), -depth, 0, () => {
      for (let level = 0; level < 3; level += 1) k.arches(9, length - 1.5, 1.3, 0.8 + level * 1.7, 0.01)
      for (let level = 1; level < 3; level += 1) k.box('rubble', length, 0.1, 0.1, 0, level * 1.7 + 0.3, 0.05)
    }, sx * -Math.PI / 2)
  }
  const steps = 22
  const run = 13 / steps
  for (let i = 0; i < steps; i += 1) {
    const top = -i * ((depth - 0.9) / steps)
    k.box(i % 2 ? 'rubble' : 'rubbleDark', width, top + depth, run, 0, -depth, -length / 2 + run * (i + 0.5))
  }
  k.box('rubbleDark', width, 0.5, 5.2, 0, -depth, 6.4)
  k.box('water', width, 0.6, 5, 0, -depth + 0.1, 6.4)
  k.at(0, -depth, length / 2 - 0.1, () => {
    k.box('rubbleDark', width + 4.8, depth, 1.2, 0, 0, 0.7)
    k.at(0, 0, 0.1, () => {
      k.arch('niche', 1.5, 3.2, -1.5, 0.7, 0)
      k.arch('niche', 1.5, 3.2, 1.5, 0.7, 0)
      k.arches(5, 5.5, 0.8, 4.4, 0)
    }, Math.PI)
  })
  k.at(0, 0, -length / 2 - 1.2, () => {
    k.box('rubble', width + 4.8, 0.3, 2.4)
    k.box('rubbleDark', width, depth, 1.2, 0, -depth, 0.6)
    k.at(-3, 0.3, 0, () => {
      k.box('rubble', 2.2, 1.4, 2)
      k.arch('niche', 0.9, 1.1, 0, 0, 1)
      k.hemi('rubbleDark', 0.75, 0, 1.4, 0, 0.8)
    })
  })
  trees(k, [[-6, 6, 0.8], [6.2, 3, 0.7], [6, -6, 0.7], [-6.2, -3, 0.6]])
  k.spot('steps', 0, -2, -3)
  k.spot('arcade', 3, -2.6, 2)
  k.spot('water', 0, -5, 6.4)
  k.spot('prayerHall', -3, 1.9, -9.2)
}

function trees(k: Kit, list: [number, number, number?][]) {
  for (const [x, z, s] of list) k.tree(x, z, s ?? 1)
}

const builders: Record<string, (k: Kit) => void> = {
  'taj-mahal'(k) {
    k.ground(28, 34)
    k.charbagh(15, 13, 0, 14, 0.8)
    for (const sx of [-1, 1]) for (const z of [9, 11.4, 16.6, 19]) k.cypress(sx * 1.7, z)
    k.box('redstone', 22, 0.45, 12.5)
    k.box('marble', 11, 0.75, 11, 0, 0.45)
    k.at(0, 1.2, 0, () => tomb(k, { w: 6.4, h: 3.5, body: 'marble', trim: 'marbleShade', dome: 'marble', r: 2.1, drum: 1, tall: 1.05, chhatri: 'marble', chhatriS: 1.9 }))
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.minaret('marble', 6.6, 0.36, sx * 4.9, 1.2, sz * 4.9, { band: 'marbleShade', leanX: sz * 0.02, leanZ: -sx * 0.02 })
    for (const sx of [-1, 1]) k.at(sx * 8.4, 0.45, 2, () => mosque(k, { w: 4.6, h: 1.8, d: 4, mat: 'redstone', trim: 'redLight', dome: 'marble', arches: 3, domes: [[-1.3, 0.5], [0, 0.72], [1.3, 0.5]] }))
    k.spot('dome', 0, 8.6, 0)
    k.spot('pishtaq', 0, 3.2, 3.4)
    k.spot('minaret', 4.9, 6, 4.9)
    k.spot('plinth', -4.6, 1.2, 5.2)
    k.spot('charbagh', 4, 0.2, 14)
  },
  'agra-fort'(k) {
    k.ground(26, 21)
    k.fort('redstone', 22, 16, 1.6, 0.5, 0.7, 6)
    k.fort('redLight', 19, 13.4, 3, 0.7, 1, 5)
    k.at(0, 0, 6.8, () => fortGate(k, { w: 3.6, h: 3.6, mat: 'redstone', trim: 'redLight', tower: 1.1, dome: 'marble' }))
    k.at(-4.2, 0, -1.5, () => {
      k.box('redstone', 6, 2.3, 3.4)
      k.arches(5, 5.4, 1.5, 0.15, 1.7)
      k.portal('redLight', 1.5, 2.2, 0, 1.7)
      for (const sx of [-1, 1]) k.chhatri('redLight', 'redLight', 1.3, sx * 2.5, 2.3, 1.2)
    })
    k.at(4.6, 0, -3.6, () => {
      k.box('marbleShade', 5, 0.5, 2.8)
      k.at(0, 0.5, 0, () => pillaredHall(k, 'marble', 'marble', 4, 1.3, 1.7, 6, 2))
      for (const sx of [-1, 1]) k.chhatri('marble', 'gold', 1.2, sx * 1.9, 2.1, 0)
    })
    k.at(3.6, 0, 1.6, () => pillaredHall(k, 'redLight', 'redstone', 4.6, 1.5, 2, 8, 3))
    k.spot('gateway', 0, 3, 7.8)
    k.spot('rampart', -9.5, 3.4, 3.4)
    k.spot('bastion', 9.5, 3.8, 6.7)
    k.spot('palace', 4.6, 2.3, -3.6)
    k.spot('hall', 3.6, 1.9, 1.6)
  },
  'red-fort'(k) {
    k.ground(28, 21)
    k.fort('redstone', 24, 15, 3.2, 0.8, 1.1, 6)
    k.at(0, 0, 7.5, () => {
      fortGate(k, { w: 5, h: 4.4, d: 2, mat: 'redstone', trim: 'redLight', tower: 1.2, dome: 'marble', top: 7 })
    })
    k.at(0, 0, 0.6, () => {
      k.box('redLight', 7.4, 0.4, 3.6)
      k.at(0, 0.4, 0, () => pillaredHall(k, 'redstone', 'redLight', 6.6, 1.7, 2.8, 9, 3))
    })
    k.at(0, 0, -4.4, () => {
      k.box('marbleShade', 7.5, 0.4, 2.6)
      k.at(0, 0.4, 0, () => pillaredHall(k, 'marble', 'marble', 6.8, 1.4, 1.9, 9, 2))
      for (const sx of [-1, 1]) k.chhatri('marble', 'marble', 1, sx * 3.3, 2.1, 0)
    })
    k.at(-7.5, 0, -3.6, () => mosque(k, { w: 3, h: 1.4, d: 2.4, mat: 'marble', trim: 'marbleShade', dome: 'marble', arches: 3, domes: [[-0.9, 0.42], [0, 0.55], [0.9, 0.42]] }))
    k.spot('gateway', 0, 3, 8.6)
    k.spot('chhatri', 1.5, 5.4, 8)
    k.spot('rampart', 12, 3.8, -2)
    k.spot('hall', 0, 2.5, 0.6)
    k.spot('palace', 0, 2.2, -4.4)
  },
  'humayuns-tomb'(k) {
    k.ground(30, 30)
    k.charbagh(28, 28, 0, 0, 0.5)
    arcadedPlinth(k, 'redstone', 13, 1.5, 11, 'buff')
    k.at(0, 1.5, 0, () => tomb(k, { w: 8, h: 3.7, cut: 1.5, body: 'redstone', trim: 'redLight', dome: 'marble', r: 2.3, drum: 1, tall: 0.9, chhatri: 'redLight', chhatriS: 1.9 }))
    k.spot('dome', 0, 8.2, 0)
    k.spot('chhatri', 2.9, 6.4, 2.9)
    k.spot('pishtaq', 0, 3.6, 4.2)
    k.spot('arcade', -4, 1, 6.6)
    k.spot('charbagh', 8.5, 0.2, 8.5)
  },
  'qutb-complex'(k) {
    k.ground(26, 22)
    k.box('path', 16, 0.05, 12, -3.5, 0, -1)
    const stages: [Mat, number, number, number][] = [
      ['redstone', 1.6, 1.25, 5.2],
      ['redLight', 1.25, 1, 3.3],
      ['redstone', 1, 0.82, 2.5],
      ['marbleShade', 0.82, 0.68, 1.5],
      ['redLight', 0.68, 0.52, 1.4],
    ]
    let y = 0
    stages.forEach(([mat, bottom, top, h], i) => {
      k.fluted(mat, top, bottom, h, 24 - i * 2, y)
      y += h
      k.cyl('buff', top * 1.3, top * 1.04, 0.14, 0, y, 0, 24)
      k.cyl('buff', top * 1.32, top * 1.32, 0.06, 0, y + 0.14, 0, 24)
      y += 0.2
    })
    k.cyl('buff', 0.32, 0.44, 0.5, 0, y, 0, 12)
    k.hemi('buff', 0.32, 0, y + 0.5, 0)
    k.at(-7.5, 0, -2.5, () => {
      k.gateBlock('buff', 3.6, 4.6, 0.8, 2, 3.8)
      for (const sx of [-1, 1]) {
        k.at(sx * 2.8, 0, 0, () => k.gateBlock('rubble', 2, 3, 0.7, 1.05, 2.3))
        k.at(sx * 4.6, 0, 0, () => k.gateBlock('rubble', 1.6, 2.1, 0.6, 0.85, 1.5))
      }
    })
    k.cyl('black', 0.13, 0.17, 2.9, -7.5, 0, 1.6, 12)
    k.add('black', new THREE.SphereGeometry(0.2, 10, 8).translate(-7.5, 2.95, 1.6))
    k.at(5.6, 0, 4, () => {
      k.box('redstone', 3.2, 2.3, 3.2)
      k.sides(3.2, 3.2, () => k.portal('marbleShade', 1.5, 2.15, 0, 0, 0, 0.08))
      k.cyl('redstone', 1.45, 1.55, 0.3, 0, 2.3, 0, 20)
      k.hemi('marbleShade', 1.4, 0, 2.6, 0, 0.72)
    })
    k.cyl('rubble', 1.5, 1.8, 2.6, -11, 0, -7, 14)
    for (let i = 0; i < 6; i += 1) k.box('rubble', 0.22, 2, 0.22, -11 + i * 1.3, 0, 3.6)
    k.box('rubble', 7, 0.18, 0.8, -7.8, 2, 3.6)
    trees(k, [[9, -6], [10.5, 8], [-11, 8, 0.8], [6, -9, 0.9]])
    k.spot('tower', 0, y - 3, 0.8)
    k.spot('balcony', 1.35, 5.4, 0)
    k.spot('ruin', -7.5, 3.5, -2.1)
    k.spot('pillar', -7.5, 2.6, 1.6)
    k.spot('gateway', 5.6, 3.2, 5.6)
  },
  'fatehpur-sikri'(k) {
    k.ground(28, 24)
    k.box('paving', 26, 0.1, 22)
    k.at(-6.5, 0.1, -1.5, () => {
      const tiers: [number, number][] = [[7.4, 7], [6, 6], [4.4, 5], [2.9, 4], [1.5, 3]]
      let y = 0
      tiers.forEach(([w, n]) => {
        k.at(0, y, 0, () => pillaredHall(k, 'redstone', 'redLight', w, 1.15, w, n, n))
        y += 1.47
      })
      k.chhatri('redstone', 'redLight', 1.6, 0, y, 0, 8)
    })
    k.at(5.5, 0.1, -6, () => {
      for (let i = 0; i < 6; i += 1) k.box('redLight', 8 + (5 - i) * 0.4, 0.2, 2.2 + (5 - i) * 0.5, 0, i * 0.2, 1.6 + (5 - i) * 0.2)
      k.at(0, 1.2, 0, () => {
        k.gateBlock('redstone', 7, 7.5, 2.4, 2.8, 5.8)
        k.arch('niche', 3.8, 6.6, 0, 0, 1.2, 0.03)
        k.gateBlock('marbleShade', 7, 7.5, 0.05, 2.8, 5.8)
        for (let i = 0; i < 7; i += 1) k.chhatri('redstone', 'marble', 0.85, -3 + i, 7.5, 0.6)
        for (const sx of [-1, 1]) k.chhatri('redstone', 'marble', 1.3, sx * 3, 7.5, -0.4)
      })
    })
    k.at(6.5, 0.1, 4, () => {
      k.box('marbleShade', 3.8, 0.3, 3.8)
      k.at(0, 0.3, 0, () => {
        k.box('marble', 2.8, 1.7, 2.8)
        k.sides(2.8, 2.8, () => k.arches(3, 2.6, 1.3, 0.12))
        k.hemi('marble', 1.15, 0, 1.7, 0, 0.8)
        k.finial(0, 2.6, 0)
      })
    })
    k.at(-1, 0.1, 6.5, () => {
      k.box('redLight', 6.6, 0.3, 6.6)
      k.box('water', 5.8, 0.05, 5.8, 0, 0.3)
      k.box('redstone', 1.6, 0.42, 1.6, 0, 0)
      for (const [x, z, w, d] of [[-2, 0, 2.6, 0.3], [2, 0, 2.6, 0.3], [0, -2, 0.3, 2.6], [0, 2, 0.3, 2.6]]) k.box('redLight', w, 0.36, d, x, 0, z)
    })
    k.spot('tiers', -6.5, 5, -1.5)
    k.spot('gateway', 5.5, 6.5, -4.5)
    k.spot('tomb', 6.5, 2.6, 5.5)
    k.spot('water', -2.8, 0.5, 8)
    k.spot('courtyard', 0.5, 0.3, -2)
  },
  'akbars-tomb'(k) {
    k.ground(30, 36)
    k.charbagh(26, 30, 0, 2, 0.5)
    k.at(0, 0, 15.6, () => {
      k.gateBlock('redstone', 7, 4.4, 2.2, 2.2, 3.4)
      k.arch('niche', 2.9, 3.9, 0, 0, 1.1, 0.03)
      k.gateBlock('marbleShade', 7, 4.4, 0.05, 2.2, 3.4)
      for (const sx of [-1, 1]) for (const sz of [-0.9, 0.9]) k.minaret('marble', 3.8, 0.34, sx * 3.1, 4.4, sz, { band: 'marbleShade' })
    })
    const tiers: [number, number, Mat][] = [[12.5, 1.8, 'redstone'], [9.6, 1.2, 'redLight'], [7.4, 1.1, 'redstone'], [5.5, 1, 'redLight']]
    let y = 0
    tiers.forEach(([w, h, mat], i) => {
      k.at(0, y, 0, () => {
        arcadedPlinth(k, mat, w, h, Math.round(w * 1.1 - i))
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('redLight', 'marble', 1.15, sx * (w / 2 - 0.45), h, sz * (w / 2 - 0.45))
      })
      y += h
    })
    k.at(0, 0, 0, () => k.sides(12.5, 12.5, (l) => k.portal('marbleShade', l * 0.2, 3.2, 0, 0, 0, 0.2)))
    k.at(0, y, 0, () => {
      k.box('marble', 3.9, 1.1, 3.9)
      k.sides(3.9, 3.9, () => {
        for (let i = 0; i < 7; i += 1) for (let j = 0; j < 3; j += 1) k.box('marbleShade', 0.32, 0.26, 0.03, -1.56 + i * 0.52, 0.12 + j * 0.33, 0)
      })
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('marble', 'marble', 0.85, sx * 1.75, 1.1, sz * 1.75)
    })
    k.spot('tiers', -4.4, 3.6, 4.4)
    k.spot('chhatri', 3.2, 4.6, 3.2)
    k.spot('jali', 0, 5.8, 2)
    k.spot('gateway', 0, 3, 16.9)
    k.spot('charbagh', 8.5, 0.2, 9)
  },
  'itimad-ud-daulah'(k) {
    k.ground(22, 22)
    k.charbagh(20, 20, 0, 0, 0.55)
    k.box('redstone', 10, 0.5, 10)
    k.at(0, 0.5, 0, () => {
      k.box('marble', 5.8, 2.5, 5.8)
      k.sides(5.8, 5.8, () => {
        k.arches(3, 4.4, 1.6, 0.25, 0.02)
        k.box('buff', 5, 0.08, 0.02, 0, 2.05, 0.02)
        k.box('buff', 5, 0.08, 0.02, 0, 0.1, 0.02)
      })
      k.box('marbleShade', 6.2, 0.1, 6.2, 0, 2.5)
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
        k.cyl('marble', 0.62, 0.66, 3.6, sx * 2.9, 0, sz * 2.9, 8)
        k.cyl('marbleShade', 0.72, 0.72, 0.06, sx * 2.9, 2.5, sz * 2.9, 8)
        k.chhatri('marble', 'marble', 1.3, sx * 2.9, 3.6, sz * 2.9, 8)
      }
      k.at(0, 2.6, 0, () => {
        k.box('marble', 2.5, 1, 2.5)
        k.sides(2.5, 2.5, () => {
          for (let i = 0; i < 5; i += 1) for (let j = 0; j < 3; j += 1) k.box('marbleShade', 0.32, 0.24, 0.03, -0.84 + i * 0.42, 0.1 + j * 0.3, 0)
        })
        k.box('marbleShade', 2.9, 0.08, 2.9, 0, 1)
        k.at(0, 1.08, 0, () => k.lathe('marble', [[1.3, 0], [1.1, 0.22], [0.7, 0.4], [0.2, 0.5], [0, 0.52]], 0, 0, 0, 4), Math.PI / 4)
        k.finial(0, 1.6, 0, 0.7)
      })
    })
    k.at(0, 0, -9.6, () => {
      k.box('redstone', 4, 3, 1)
      k.portal('marbleShade', 1.8, 2.9, 0, 0.5)
    })
    k.spot('minaret', 2.9, 4.6, 2.9)
    k.spot('jali', 0, 3.8, 1.3)
    k.spot('arcade', 0, 1.6, 2.95)
    k.spot('plinth', -4.2, 0.5, 4.2)
    k.spot('charbagh', 6.5, 0.2, 6.5)
  },
  'jama-masjid'(k) {
    k.ground(24, 26)
    k.box('redstone', 20, 1.6, 20)
    k.sides(20, 20, (l) => k.arches(16, l - 1, 1, 0.2))
    for (let i = 0; i < 8; i += 1) k.box('redLight', 7 - i * 0.2, 0.2, 2.8 - i * 0.35, 0, i * 0.2, 11.4 - i * 0.17)
    k.box('path', 19, 0.04, 19, 0, 1.6)
    k.box('water', 2.6, 0.08, 2.6, 0, 1.6, 2)
    for (const [a, b] of [[[-9.6, -9.6], [-9.6, 9.6]], [[9.6, -9.6], [9.6, 9.6]], [[-9.6, 9.6], [9.6, 9.6]]] as [[number, number], [number, number]][]) k.wall('redLight', a, b, 1.1, 0.7, 1.6, false)
    k.at(0, 1.6, 9.6, () => {
      k.box('redstone', 5, 2.4, 1.4)
      k.portal('marbleShade', 2.4, 2.3, 0, 0.7)
      for (const sx of [-1, 1]) k.chhatri('redLight', 'marble', 1.1, sx * 2.1, 2.4, 0)
    })
    k.at(0, 1.6, -5.5, () => {
      mosque(k, { w: 16, h: 3.1, d: 4, mat: 'redstone', trim: 'marbleShade', dome: 'marble', arches: 11, domes: [[-3.6, 1.15], [0, 1.6], [3.6, 1.15]], tall: 1.05 })
      for (const [x, r] of [[-3.6, 1.15], [0, 1.6], [3.6, 1.15]]) for (const t of [0.45, 0.9, 1.3]) {
        const taper = Math.sqrt(Math.max(0.06, 1 - ((t - 0.35) / 1.5) ** 2)) * 1.06
        k.cyl('black', r * taper, r * taper, 0.05, x, 3.1 + r * 0.28 + r * t, -2, 24)
      }
      for (const sx of [-1, 1]) k.minaret('redstone', 8, 0.5, sx * 8.2, 0, -0.3, { band: 'marble', dome: 'marble', rings: 4 })
    })
    k.spot('dome', 0, 8.8, -7.5)
    k.spot('minaret', 8.2, 8.6, -5.8)
    k.spot('prayerHall', -4.4, 3.4, -5.3)
    k.spot('courtyard', 3.8, 1.8, 3)
    k.spot('gateway', 0, 3.6, 10.6)
  },
  'safdarjungs-tomb'(k) {
    k.ground(28, 28)
    k.charbagh(26, 26, 0, 0, 0.6)
    arcadedPlinth(k, 'redstone', 11, 1.9, 9, 'buff')
    k.at(0, 1.9, 0, () => {
      tomb(k, { w: 5.8, h: 4.2, cut: 0.6, body: 'buff', trim: 'redstone', dome: 'marble', r: 1.85, drum: 0.75, tall: 1.15 })
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
        k.cyl('redstone', 0.45, 0.5, 5, sx * 2.9, 0, sz * 2.9, 8)
        k.chhatri('marble', 'marble', 1.2, sx * 2.9, 5, sz * 2.9, 8)
      }
    })
    k.at(0, 0, -13, () => {
      k.box('redstone', 6, 3.4, 1.2)
      k.portal('buff', 2.6, 3.3, 0, 0.6)
      k.merlons('redLight', 6, 3.4, 0, 0.5)
    })
    k.spot('dome', 0, 9.8, 0)
    k.spot('minaret', 2.9, 7.6, 2.9)
    k.spot('pishtaq', 0, 4, 3.1)
    k.spot('arcade', 3.4, 1.1, 5.6)
    k.spot('charbagh', -8, 0.2, 8)
  },
  'purana-qila'(k) {
    k.ground(27, 22)
    k.fort('rubble', 23, 17, 3, 0.9, 1.2, 7)
    k.at(0, 0, 8.5, () => {
      k.gateBlock('redstone', 4.4, 4.6, 1.8, 1.7, 3)
      k.arch('niche', 2.2, 3.4, 0, 0, 0.9, 0.03)
      k.gateBlock('marbleShade', 4.4, 4.6, 0.06, 1.7, 3)
      k.arches(5, 4, 0.8, 3.65, 0.93)
      for (const sx of [-1, 1]) {
        k.bastion('rubble', 1.5, 4.2, sx * 3.4, 0.2)
        k.chhatri('redLight', 'marble', 1.4, sx * 1.5, 4.6, 0, 8)
      }
    })
    k.at(-4, 0, -2.5, () => {
      mosque(k, { w: 8, h: 3, d: 2.8, mat: 'redstone', trim: 'marbleShade', dome: 'marbleShade', arches: 5, domes: [[0, 1.2]], tall: 0.7 })
      for (const sx of [-1, 1]) k.at(sx * 4.1, 0, -1.4, () => k.cyl('redLight', 0.45, 0.55, 3.3, 0, 0, 0, 10))
    })
    k.at(6, 0, 1, () => {
      k.cyl('redstone', 1.7, 1.85, 2, 0, 0, 0, 8)
      k.cyl('redLight', 1.35, 1.4, 1.5, 0, 2, 0, 8)
      k.cyl('buff', 1.8, 1.8, 0.1, 0, 2, 0, 8)
      for (let i = 0; i < 8; i += 1) {
        const a = (i / 8) * Math.PI * 2 + Math.PI / 8
        k.at(Math.cos(a) * 1.63, 0.35, Math.sin(a) * 1.63, () => k.arch('niche', 0.6, 1.2, 0, 0, 0), Math.PI / 2 - a)
      }
      k.chhatri('marble', 'marble', 1.9, 0, 3.5, 0, 8)
    })
    trees(k, [[-8, 4.5], [7, 6, 0.9], [-7.5, -6, 0.8], [3.5, -5.5]])
    k.spot('gateway', 0, 3.6, 9.5)
    k.spot('rampart', -11.5, 3.5, 3)
    k.spot('bastion', 11.5, 3.7, 8.5)
    k.spot('prayerHall', -4, 2.4, -2.2)
    k.spot('tower', 6, 2.6, 2.8)
  },
  'tughlaqabad-fort'(k) {
    k.ground(28, 24, 'rubbleDark')
    k.box('sand', 27, 0.05, 23)
    const outline: [number, number][] = [[-12, -6], [-7, -10], [3, -10.5], [11, -8], [12.5, 0], [10, 8], [1, 10], [-8, 9], [-12.5, 3]]
    outline.forEach((c, i) => {
      const next = outline[(i + 1) % outline.length]
      k.wall('rubble', c, next, 3.8, 1.5)
      k.bastion('rubble', 1.5, 4.2, c[0], c[1], 0, 0.7)
    })
    k.at(1, 0, 10, () => {
      k.gateBlock('rubbleDark', 3.4, 4.2, 1.8, 1.4, 2.8)
    }, -0.2)
    k.fort('rubbleDark', 8, 7, 5, 0.9, 1.1, 8)
    for (const [x, z, w, h, d] of [[-8, 3, 3, 1.3, 2], [-6.5, -5, 2.4, 1.8, 3], [6, 4, 4, 1, 1.5], [8, -3.5, 2, 1.6, 3], [-3.5, 6, 2.5, 0.8, 1.2]]) k.box('rubble', w, h, d, x, 0, z)
    k.at(0, 0, 0, () => {
      k.gateBlock('rubble', 3, 2.4, 0.6, 1.3, 1.7)
      k.box('rubbleDark', 2, 0.9, 1.6, -1.2, 0, -1.6)
    })
    trees(k, [[-5, 8, 0.7], [5, -7, 0.8], [8, 6.5, 0.7], [-9, -5, 0.6]])
    k.spot('rampart', -2.5, 4.3, -10)
    k.spot('bastion', 11, 4.6, -8)
    k.spot('gateway', 1, 3.2, 11)
    k.spot('ruin', 6, 1.4, 4)
    k.spot('tiers', 0, 5.6, -3.5)
  },
  'jantar-mantar'(k) {
    k.ground(26, 20)
    k.box('lawn', 25, 0.05, 19)
    k.box('path', 2, 0.07, 19, 7, 0)
    k.at(-2.5, 0, 0, () => {
      const gnomon = new THREE.Shape()
      gnomon.moveTo(-4.5, 0)
      gnomon.lineTo(4.5, 0)
      gnomon.lineTo(4.5, 7)
      gnomon.closePath()
      k.add('plaster', new THREE.ExtrudeGeometry(gnomon, { depth: 1.8, bevelEnabled: false }).translate(0, 0, -0.9))
      for (let i = 1; i < 16; i += 1) {
        const t = i / 16
        k.at(-4.5 + 9 * t, 7 * t, 0, () => k.box('marble', 0.12, 0.05, 1.82))
      }
      for (const sz of [-1, 1]) {
        k.add('plaster', new THREE.TorusGeometry(4, 0.45, 8, 26, Math.PI / 2).rotateZ(Math.PI).translate(3.4, 4.2, sz * 3))
        k.add('marble', new THREE.TorusGeometry(3.56, 0.08, 6, 26, Math.PI / 2).rotateZ(Math.PI).translate(3.4, 4.2, sz * 3))
        k.box('plaster', 7.8, 0.3, 1.1, -0.1, 0, sz * 3)
      }
    })
    k.at(5.5, 0, -6, () => {
      for (const x of [-1.9, 1.9]) {
        const bowl = new THREE.TorusGeometry(1.7, 0.2, 8, 22).rotateX(Math.PI / 2).translate(x, 1.3, 0)
        k.add('marble', bowl)
        k.cyl('plaster', 1.75, 1.85, 1.3, x, 0, 0, 22)
        k.lathe('marbleShade', [[0, 0.15], [0.9, 0.3], [1.5, 0.8], [1.68, 1.31]], x, 0.02, 0)
      }
    })
    k.at(4.5, 0, 5.2, () => {
      for (let i = 0; i < 12; i += 1) {
        const a = (i / 12) * Math.PI * 2
        k.at(Math.cos(a) * 2.4, 0, Math.sin(a) * 2.4, () => {
          k.gateBlock('plaster', 1.05, 3.1, 0.3, 0.6, 2)
          k.arch('marble', 0.6, 0.5, 0, 2.3, 0.15, 0.02)
        }, Math.PI / 2 - a)
      }
      k.cyl('plaster', 0.3, 0.4, 2.6, 0, 0, 0, 12)
      k.cyl('marbleShade', 2.2, 2.2, 0.08, 0, 0, 0, 24)
    })
    trees(k, [[-10, 7.5], [-11, -6.5], [10.5, 7.8, 0.9], [10.5, -2.4, 0.8], [-3, 8, 0.8]])
    k.spot('gnomon', -2.5, 3.8, 0.9)
    k.spot('dial', -1.9, 1.7, 3)
    k.spot('dial', 5.5, 1.5, -6)
    k.spot('hall', 4.5, 3.1, 5.2)
  },
  'mehrauli-archaeological-park'(k) {
    k.ground(28, 24)
    k.box('lawn', 27, 0.05, 23)
    k.box('path', 1.1, 0.07, 22, 0, 0, 0)
    k.box('path', 26, 0.07, 1.1, 0, 0, 1)
    k.at(-6, 0, -4, () => mosque(k, { w: 8, h: 3.6, d: 3, mat: 'buff', trim: 'redstone', dome: 'marbleShade', arches: 5, domes: [[0, 1.2]], tall: 0.68 }))
    k.at(6.5, 0, -5, () => {
      for (const [x, z, turn, w] of [[0, 2, 0, 5], [0, -2, 0, 5], [2.3, 0, Math.PI / 2, 4], [-2.3, 0, Math.PI / 2, 4]] as [number, number, number, number][]) k.at(x, 0, z, () => k.gateBlock('rubble', w, 3, 0.55, 1.7, 2.2), turn)
      k.box('rubbleDark', 1.4, 1.2, 1.4, 1.6, 3, 2)
      k.box('rubbleDark', 1.2, 0.8, 1.2, -1.7, 3, -2)
    })
    k.at(6, 0, 6, () => {
      k.box('rubble', 8, 0.6, 6)
      for (let i = 0; i < 5; i += 1) k.box(i % 2 ? 'buff' : 'rubbleDark', 6.8 - i * 0.9, 0.05, 4.8 - i * 0.8, 0, 0.6 + i * 0.008, 0)
      k.box('water', 2.6, 0.08, 1.2, 0, 0.61, 0)
      k.arches(5, 6.5, 0.4, 0.1, 3.01)
    })
    k.at(-6.5, 0, 6, () => {
      k.cyl('rubble', 1.8, 2.8, 1.2, 0, 0, 0, 14)
      k.chhatri('buff', 'buff', 2.4, 0, 1.2, 0, 8)
    })
    trees(k, [[-11, -8], [-2, 8.5, 0.8], [11, 1, 0.9], [2, -9], [-11, 1.5, 0.8], [11.5, -10, 0.8], [1.5, 5, 0.7], [-1.8, -6.5, 0.7]])
    k.spot('prayerHall', -6, 2.6, -3.7)
    k.spot('ruin', 6.5, 2.9, -2.8)
    k.spot('steps', 6, 0.9, 7.5)
    k.spot('chhatri', -6.5, 3.4, 6)
    k.spot('garden', 0.8, 0.4, -9)
  },
  'lodhi-gardens'(k) {
    k.ground(28, 26)
    k.box('lawn', 27, 0.05, 25)
    k.box('path', 26, 0.07, 1.1, 0, 0, 0.8)
    k.box('path', 1.1, 0.07, 24, -1, 0, 0)
    const squareTomb = (x: number, z: number, mat: Mat, r: number, kiosk: boolean) => k.at(x, 0, z, () => {
      k.box(mat, 5.6, 4, 5.6)
      k.sides(5.6, 5.6, () => {
        k.portal('buff', 2.1, 3.1, 0, 0, 0, 0.08)
        for (const sx of [-1, 1]) for (const y of [0.3, 2.3]) k.arch('niche', 0.8, 1.3, sx * 1.9, y, 0)
      })
      k.box('buff', 5.8, 0.1, 5.8, 0, 4)
      k.cyl(mat, r * 0.86, r * 0.95, 0.5, 0, 4.1, 0, 16)
      k.hemi(mat, r, 0, 4.6, 0, 0.84)
      k.finial(0, 4.6 + r * 0.84, 0, 0.9)
      if (kiosk) for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('buff', mat, 0.9, sx * 2.4, 4.1, sz * 2.4)
    })
    squareTomb(-7, -6.5, 'rubble', 2.4, true)
    squareTomb(6.5, -7, 'rubbleDark', 2.3, false)
    k.at(-3.2, 0, -10.5, () => mosque(k, { w: 4, h: 2.4, d: 1.8, mat: 'buff', trim: 'rubble', dome: 'rubble', arches: 3, domes: [] }))
    k.at(5.5, 0, 6.5, () => {
      k.box('rubble', 7, 0.5, 7)
      k.at(0, 0.5, 0, () => {
        k.cyl('rubble', 2.9, 3, 2.4, 0, 0, 0, 8)
        for (let i = 0; i < 8; i += 1) {
          const a = (i / 8) * Math.PI * 2 + Math.PI / 8
          k.at(Math.cos(a) * 2.75, 0.2, Math.sin(a) * 2.75, () => k.arches(3, 2, 1.5), Math.PI / 2 - a)
        }
        k.cyl('buff', 2.05, 2.1, 0.8, 0, 2.4, 0, 8)
        k.hemi('rubble', 1.95, 0, 3.2, 0, 0.85)
        k.finial(0, 4.85, 0, 0.9)
        for (let i = 0; i < 8; i += 1) {
          const a = (i / 8) * Math.PI * 2
          k.chhatri('buff', 'rubble', 0.9, Math.cos(a) * 2.45, 2.4, Math.sin(a) * 2.45)
        }
      })
    })
    trees(k, [[-12, 3, 1.2], [-8, 6, 1.1], [-4.5, 9, 1], [0.5, -9.5, 1.2], [11.5, -1, 1.1], [12, 11, 1], [0, 10.5, 1.2], [-11.5, 10, 1.3], [-12, -11, 1], [11.5, -11.5, 1]])
    k.spot('dome', -7, 6.5, -6.5)
    k.spot('chhatri', 7.95, 3.3, 6.5)
    k.spot('arcade', 5.5, 1.6, 9.2)
    k.spot('pishtaq', 6.5, 2.2, -4.1)
    k.spot('garden', -7, 0.4, 3.5)
  },
  'india-gate'(k) {
    k.view = { theta: 0.42, phi: 1.2 }
    k.ground(20, 40)
    k.box('path', 8, 0.04, 39, 0, 0, 0)
    for (const sx of [-1, 1]) {
      k.box('lawn', 5.6, 0.07, 38, sx * 7, 0)
      k.box('water', 1.5, 0.08, 15, sx * 4.9, 0, 10)
    }
    for (let i = 0; i < 3; i += 1) k.box('redstone', 13 - i * 0.8, 0.28, 6.4 - i * 0.7, 0, i * 0.28)
    k.at(0, 0.84, 0, () => {
      k.gateBlock('buff', 10, 12, 4, 4.6, 9.2)
      k.archBand('rubbleDark', 4.3, 9, 0.15, 3.96)
      for (const z of [-2, 2]) k.archBand('marbleShade', 4.6, 9.2, 0.3, 0.1, z)
      for (const sx of [-1, 1]) k.at(sx * 5.01, 0, 0, () => k.arch('niche', 2, 5, 0, 0.2, 0, 0.03), sx * Math.PI / 2)
      k.box('redLight', 10.3, 0.5, 4.3, 0, 0)
      k.box('marbleShade', 10.5, 0.14, 4.5, 0, 9.8)
      k.box('buff', 8.8, 1, 3.4, 0, 12)
      k.box('marbleShade', 9.1, 0.12, 3.7, 0, 12)
      k.box('buff', 6.8, 0.8, 3, 0, 13)
      k.box('buff', 4.6, 0.7, 2.6, 0, 13.8)
      k.cyl('buff', 1.25, 1.35, 0.5, 0, 14.5, 0, 24)
      k.lathe('marbleShade', [[0.3, 0], [1.05, 0.45], [1.32, 0.7], [1.2, 0.72], [0.3, 0.3]], 0, 15, 0)
    })
    k.at(0, 0, 12, () => {
      k.box('redstone', 4.4, 0.4, 4.4)
      k.at(0, 0.4, 0, () => {
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.box('buff', 0.35, 2.8, 0.35, sx * 1.3, 0, sz * 1.3)
        k.box('buff', 3.3, 0.45, 3.3, 0, 2.8)
        k.hemi('buff', 1.2, 0, 3.25, 0, 0.9)
        k.finial(0, 4.3, 0, 0.8)
      })
    })
    k.spot('memorialArch', 0, 8.6, 2.2)
    k.spot('dome', 0, 15.8, 0)
    k.spot('plinth', -6, 0.9, 2.6)
    k.spot('chhatri', 0, 3.8, 13.6)
    k.spot('water', 4.9, 0.4, 12)
  },
  'lotus-temple'(k) {
    k.ground(30, 30)
    k.cyl('path', 13.5, 13.8, 0.28, 0, 0, 0, 48)
    k.cyl('marbleShade', 8.6, 9, 0.7, 0, 0.28, 0, 36)
    for (let i = 0; i < 9; i += 1) {
      const a = (i / 9) * Math.PI * 2 + Math.PI / 9
      k.at(Math.cos(a) * 10.9, 0.28, Math.sin(a) * 10.9, () => {
        k.box('marbleShade', 3.8, 0.09, 2.9)
        k.box('water', 3.3, 0.14, 2.4)
      }, Math.PI / 2 - a)
    }
    // Curved shell: u runs up the petal, v across it, and z is the outward direction.
    const petal = (height: number, width: number, base: number, lean: number, curl: number) => {
      const rows = 14
      const cols = 10
      const position: number[] = []
      const pointAt = (u: number, v: number): [number, number, number] => {
        const across = width * Math.sin(Math.PI * u ** 0.72) ** 0.85 * v
        const sag = (1 - v * v) * Math.sin(Math.PI * u) * width * 0.34
        return [across, height * u, base + lean * u + curl * u * u - sag]
      }
      for (let r = 0; r < rows; r += 1) for (let c = 0; c < cols; c += 1) {
        const u0 = r / rows
        const u1 = (r + 1) / rows
        const v0 = -1 + (2 * c) / cols
        const v1 = -1 + (2 * (c + 1)) / cols
        position.push(...pointAt(u0, v0), ...pointAt(u0, v1), ...pointAt(u1, v1), ...pointAt(u0, v0), ...pointAt(u1, v1), ...pointAt(u1, v0))
      }
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3))
      geo.computeVertexNormals()
      geo.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array((position.length / 3) * 2), 2))
      return geo
    }
    const ring = (count: number, offset: number, make: () => THREE.BufferGeometry) => {
      for (let i = 0; i < count; i += 1) {
        const a = (i / count) * Math.PI * 2 + offset
        k.at(0, 0.98, 0, () => k.add('shell', make()), a)
      }
    }
    ring(9, 0, () => petal(9.4, 2.3, 2.6, -1.9, 0))
    ring(9, Math.PI / 9, () => petal(7.9, 2.9, 4.1, -1.6, 2))
    ring(9, 0, () => petal(4.6, 3, 7, 0.1, 1.5))
    k.cyl('marble', 3.4, 4.5, 4.5, 0, 0.98, 0, 18)
    for (let i = 0; i < 2; i += 1) k.box('marbleShade', 8, 0.2, 2.2 - i * 0.7, 0, 0.28 + i * 0.2, 9.4 - i * 0.3)
    k.spot('petals', 1.2, 7.8, 3.2)
    k.spot('petals', 6.6, 3.8, 3.4)
    k.spot('water', 7.2, 0.5, 8.6)
    k.spot('plinth', -6.2, 1, 6.2)
  },
  'hauz-khas-complex'(k) {
    k.ground(28, 26)
    k.box('lawn', 27, 0.05, 25)
    k.at(4.5, 0, 5, () => {
      k.box('path', 15, 0.1, 13)
      for (let i = 0; i < 3; i += 1) k.box('rubble', 14 - i, 0.04, 12 - i, 0, 0.1 + i * 0.003)
      k.box('water', 12, 0.13, 10)
      k.chhatri('rubble', 'rubble', 1.8, 3.5, 0.13, -1, 8)
    })
    const range = (length: number, storey: number) => {
      k.box('rubble', length, storey, 2.2)
      k.arches(Math.floor(length / 1.2), length - 0.4, storey * 0.72, 0.05, 1.1)
      k.box('rubbleDark', length, 0.08, 2.5, 0, storey)
      k.box('buff', length, storey, 1.8, 0, storey + 0.08, -0.2)
      k.arches(Math.floor(length / 1.2), length - 0.4, storey * 0.72, storey + 0.13, 0.7)
      k.box('rubbleDark', length, 0.06, 2.1, 0, storey * 2 + 0.08, -0.2)
    }
    k.at(4.5, 0, -2.5, () => range(15, 1.3))
    k.at(-4.2, 0, 5, () => range(13, 1.3), -Math.PI / 2)
    k.at(-5.6, 0, -4, () => {
      k.box('rubble', 4.6, 3.2, 4.6)
      k.sides(4.6, 4.6, () => k.portal('buff', 1.9, 2.8, 0, 0, 0, 0.08))
      k.cyl('rubble', 1.7, 1.85, 0.5, 0, 3.2, 0, 8)
      k.hemi('marbleShade', 1.75, 0, 3.7, 0, 0.86)
      k.finial(0, 5.2, 0, 0.9)
    })
    for (const [x, z] of [[1, -4.6], [6, -4.6], [10, -4.6]]) k.chhatri('buff', 'rubble', 1.8, x, 2.8, z, 8)
    trees(k, [[-11, 3], [-10.5, 9.5, 1.1], [-11, -10], [-1, -9.5, 1.1], [9, -9.5], [12.5, 9, 0.8]])
    k.spot('tank', 6, 0.3, 6)
    k.spot('arcade', 6, 1.4, -1.3)
    k.spot('tomb', -5.6, 5.4, -4)
    k.spot('chhatri', 6, 3.8, -4.6)
    k.spot('garden', -11, 0.4, 2)
  },
  'agrasen-ki-baoli'(k) {
    // Turned and framed so the opening view looks down the steps towards the water.
    k.view = { theta: 0.14, phi: 0.82 }
    k.at(0, 0, 0, () => baoli(k), Math.PI)
  },
  'feroz-shah-kotla'(k) {
    k.ground(28, 24)
    k.box('lawn', 27, 0.05, 23)
    for (const [a, b, h] of [[[-12, -9], [-3, -10], 3.2], [[3, -9.8], [12, -9], 2.6], [[12, -9], [12.5, 2], 2.2], [[-12, -9], [-12.5, 6], 2.8]] as [[number, number], [number, number], number][]) k.wall('rubble', a, b, h, 1)
    k.bastion('rubble', 1.2, 3.6, -12, -9)
    k.bastion('rubble', 1.1, 3, 12, -9)
    k.at(4, 0, -2, () => {
      const tiers: [number, number][] = [[9, 1.8], [6.6, 1.6], [4.4, 1.4]]
      let y = 0
      tiers.forEach(([w, h]) => {
        k.at(0, y, 0, () => {
          k.box(y ? 'rubbleDark' : 'rubble', w, h, w)
          k.sides(w, w, (l) => k.arches(Math.max(3, Math.floor(l / 1.3)), l - 0.4, h * 0.7, 0.05))
        })
        y += h
      })
      k.cyl('buff', 0.13, 0.26, 5.6, 0, y, 0, 14)
      k.finial(0, y + 5.6, 0, 0.8)
    })
    k.at(-6, 0, -2, () => {
      k.box('rubble', 8, 1.6, 7)
      k.sides(8, 7, (l) => k.arches(Math.floor(l / 1.2), l - 0.4, 1.1, 0.05))
      k.at(0, 1.6, -2.8, () => k.gateBlock('rubble', 6.6, 2.6, 0.5, 1.4, 1.9))
      k.at(-3.6, 1.6, 0, () => k.gateBlock('rubbleDark', 3, 1.6, 0.5, 1, 1.1), Math.PI / 2)
    })
    k.at(-7, 0, 6.5, () => {
      k.cyl('rubble', 2.7, 2.9, 1, 0, 0, 0, 22)
      k.cyl('water', 2.15, 2.15, 1.02, 0, 0, 0, 22)
    })
    trees(k, [[9, 7, 1.1], [3.5, 8.5], [-1, 6, 0.8], [11, 3.5, 0.8], [-11, 9, 0.9]])
    k.spot('pillar', 4, 8.8, -2)
    k.spot('tiers', 7.2, 2.6, 1.2)
    k.spot('ruin', -6, 3.4, -4.6)
    k.spot('rampart', -7, 3.6, -9.5)
    k.spot('steps', -7, 1.2, 6.5)
  },
  'rashtrapati-bhavan'(k) {
    k.ground(40, 34)
    k.box('path', 16, 0.05, 10, 0, 0, 12)
    k.charbagh(24, 10, 0, -13, 0.4)
    k.at(0, 0, 0, () => {
      k.box('redstone', 34, 1.2, 8)
      k.arches(32, 33, 0.8, 0.1, 4.01)
      k.at(0, 1.2, 0, () => {
        for (const sx of [-1, 1]) k.at(sx * 11, 0, 0, () => {
          k.box('buff', 12, 3, 7)
          for (let i = 0; i < 12; i += 1) for (const y of [0.5, 1.8]) k.box('niche', 0.42, 0.75, 0.04, -5.5 + i, y, 3.5)
          k.box('marbleShade', 12.4, 0.12, 7.4, 0, 3)
          for (const x of [-4.5, 0, 4.5]) k.chhatri('buff', 'buff', 1.1, x, 3.1, 3)
        })
        k.box('buff', 11, 4.2, 9)
        k.box('marbleShade', 11.4, 0.14, 9.4, 0, 4.2)
        for (let i = 0; i < 12; i += 1) k.cyl('marbleShade', 0.15, 0.18, 3.4, -4.95 + i * 0.9, 0, 4.9, 12)
        k.box('marbleShade', 11, 0.7, 1.2, 0, 3.4, 4.9)
        for (let i = 0; i < 5; i += 1) k.box('redLight', 9.5 - i * 0.2, 0.24, 2.4 - i * 0.4, 0, -1.2 + i * 0.24, 6.4 - i * 0.05)
        k.cyl('buff', 3.15, 3.25, 1.6, 0, 4.34, 0, 28)
        for (let i = 0; i < 18; i += 1) {
          const a = (i / 18) * Math.PI * 2
          k.cyl('marbleShade', 0.09, 0.09, 1.2, Math.cos(a) * 3.3, 4.5, Math.sin(a) * 3.3, 8)
        }
        k.cyl('marbleShade', 3.5, 3.5, 0.14, 0, 5.75, 0, 28)
        k.hemi('copper', 3, 0, 5.9, 0, 0.96)
        k.finial(0, 8.7, 0, 1.2)
      })
    })
    k.at(0, 0, 13.5, () => {
      k.box('redLight', 2, 0.5, 2)
      k.cyl('buff', 0.12, 0.25, 7, 0, 0.5, 0, 14)
      k.finial(0, 7.5, 0, 1)
    })
    k.spot('dome', 0, 9, 1.5)
    k.spot('portico', -3, 3.6, 5.3)
    k.spot('wings', 11, 3.6, 3.7)
    k.spot('pillar', 0, 7.4, 13.5)
    k.spot('charbagh', 7, 0.2, -13)
  },
  'sunder-nursery'(k) {
    k.ground(26, 32)
    k.box('lawn', 25, 0.05, 31)
    k.at(0, 0, 3, () => {
      k.box('path', 6.6, 0.07, 19)
      k.box('water', 3, 0.1, 18)
      for (const z of [-7, -3.5, 0, 3.5, 7]) for (const sx of [-1, 1]) k.box('redstone', 1.1, 0.5, 1.1, sx * 2.4, 0, z)
      for (const z of [-5.2, -1.7, 1.7, 5.2]) for (const sx of [-1, 1]) k.box('leaf', 1.5, 0.35, 2, sx * 4.8, 0, z)
    })
    k.at(0, 0, -11, () => {
      k.box('redstone', 7.4, 0.6, 7.4)
      k.at(0, 0.6, 0, () => {
        k.box('buff', 4.8, 3.2, 4.8)
        k.sides(4.8, 4.8, () => k.portal('redstone', 2, 2.9, 0, 0, 0, 0.08))
        k.cyl('buff', 1.7, 1.85, 0.55, 0, 3.2, 0, 16)
        k.hemi('marbleShade', 1.75, 0, 3.75, 0, 0.92)
        k.finial(0, 5.35, 0, 0.9)
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('redLight', 'marble', 1, sx * 2.1, 3.2, sz * 2.1)
      })
    })
    k.chhatri('redstone', 'marble', 3, 0, 0.1, 14, 8)
    trees(k, [[-9, -9, 1.2], [9, -9, 1.2], [-10.5, 0, 1.1], [10.5, 0, 1.1], [-9.5, 8], [9.5, 8], [-10.5, 14, 1.2], [10.5, 14, 1.2], [-6, 13, 0.9], [6, 13, 0.9]])
    k.spot('water', 0, 0.3, 4)
    k.spot('dome', 0, 5.8, -11)
    k.spot('chhatri', 0, 3, 14)
    k.spot('garden', -4.8, 0.5, -2)
    k.spot('plinth', 3.7, 0.7, -7.3)
  },
  'abdul-rahim-khan-i-khana-tomb'(k) {
    k.ground(22, 22)
    k.box('lawn', 21, 0.05, 21)
    arcadedPlinth(k, 'rubble', 13, 1.5, 11, 'rubbleDark')
    k.at(0, 1.5, 0, () => {
      k.box('rubble', 8, 5.2, 8)
      k.sides(8, 8, () => {
        k.portal('buff', 3.3, 5, 0, 0, 0, 0.12)
        for (const sx of [-1, 1]) for (const y of [0.3, 2.8]) {
          k.box('redLight', 1.2, 2, 0.04, sx * 2.8, y - 0.1, 0)
          k.arch('niche', 0.9, 1.7, sx * 2.8, y, 0.04)
        }
      })
      k.box('rubbleDark', 8.3, 0.12, 8.3, 0, 5.2)
      k.cyl('rubble', 2.45, 2.65, 1.2, 0, 5.3, 0, 16)
      k.hemi('rubbleDark', 2.6, 0, 6.5, 0, 0.96)
      k.finial(0, 9, 0, 1)
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('rubble', 'rubbleDark', 1.7, sx * 3.1, 5.3, sz * 3.1, 8)
    })
    trees(k, [[-9.3, -9.3, 0.9], [9.3, -9.3], [-9.3, 9.3], [9.3, 9.3, 0.9]])
    k.spot('dome', 0, 9.2, 1.8)
    k.spot('pishtaq', 0, 4.4, 4.2)
    k.spot('arcade', -4, 1, 6.6)
    k.spot('chhatri', 3.1, 8.2, 3.1)
    k.spot('ruin', -2.8, 4, 4.1)
  },
  'khirki-masjid'(k) {
    k.ground(24, 24)
    k.box('path', 23, 0.04, 23)
    const size = 16
    k.box('rubble', size, 2.8, size)
    k.sides(size, size, (l) => {
      for (const y of [0.5, 1.7]) for (let i = 0; i < 12; i += 1) if (Math.abs(i - 5.5) > 1.2) k.box('niche', 0.46, 0.7, 0.04, -l / 2 + 1 + i * ((l - 2) / 11), y, 0)
    })
    const cells = 5
    const cell = size / cells
    const openCourts = new Set(['1,1', '3,1', '1,3', '3,3'])
    for (let i = 0; i < cells; i += 1) for (let j = 0; j < cells; j += 1) {
      const x = -size / 2 + cell * (i + 0.5)
      const z = -size / 2 + cell * (j + 0.5)
      if (openCourts.has(`${i},${j}`)) {
        k.box('path', cell - 0.4, 0.03, cell - 0.4, x, 2.8, z)
        k.box('niche', cell - 0.7, 0.02, cell - 0.7, x, 2.83, z)
      } else {
        for (const dx of [-0.8, 0, 0.8]) for (const dz of [-0.8, 0, 0.8]) k.hemi('rubbleDark', 0.38, x + dx, 2.8, z + dz, 0.75)
      }
    }
    k.sides(size, size, (_, side) => {
      if (side === 3) return
      k.box('rubbleDark', 4, 4, 1.4, 0, 0, 0.2)
      k.arch('niche', 1.5, 2.8, 0, 0, 0.9)
      for (const sx of [-1, 1]) k.cyl('rubble', 0.4, 0.62, 4.6, sx * 2.1, 0, 0.6, 12)
    })
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.cyl('rubbleDark', 0.75, 1.15, 3.8, sx * size / 2, 0, sz * size / 2, 14)
    k.spot('rooftopDomes', 0, 3.6, 0)
    k.spot('courtyard', -3.2, 3, 3.2)
    k.spot('jali', 5.6, 1.5, 8.05)
    k.spot('gateway', 0, 3.2, 9.3)
    k.spot('bastion', 8, 3.8, 8)
  },
  'nizamuddin-dargah'(k) {
    k.ground(24, 24)
    k.box('marbleShade', 23, 0.06, 23)
    k.at(0, 0, 1.5, () => {
      k.box('marble', 7.6, 0.3, 7.6)
      k.at(0, 0.3, 0, () => {
        k.box('marble', 3.6, 2.9, 3.6)
        k.box('marbleShade', 6.8, 0.12, 6.8, 0, 2.1)
        k.sides(6.4, 6.4, (l) => {
          for (let i = 0; i < 7; i += 1) {
            const x = -l / 2 + (i * l) / 6
            k.box('marble', 0.22, 2.1, 0.22, x, 0, 0)
          }
          for (let i = 0; i < 6; i += 1) k.arch('marbleShade', 0.86, 1.8, -l / 2 + (i + 0.5) * (l / 6), 0.05, -0.06)
        })
        k.cyl('marble', 1.4, 1.5, 0.5, 0, 2.9, 0, 24)
        k.onion('marble', 1.65, 0, 3.4, 0, 1.08)
        k.finial(0, 6.7, 0, 1.2)
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) k.chhatri('marble', 'marble', 0.8, sx * 3, 2.22, sz * 3)
      })
    })
    k.at(0, 0, -7.5, () => mosque(k, { w: 11, h: 3.6, d: 3.4, mat: 'redstone', trim: 'redLight', dome: 'marbleShade', arches: 5, domes: [[-3.3, 1], [0, 1.4], [3.3, 1]], tall: 0.75 }))
    for (const [x, z] of [[-8.2, 5.5], [8.2, 3]]) k.at(x, 0, z, () => {
      k.box('marble', 2.6, 1.8, 2.6)
      k.sides(2.6, 2.6, () => k.arches(3, 2.3, 1.2, 0.2))
      k.hemi('marble', 1, 0, 1.8, 0, 0.9)
      k.finial(0, 2.7, 0, 0.7)
    })
    k.spot('dargah', 0, 7, 1.5)
    k.spot('arcade', 0, 1.6, 5.2)
    k.spot('prayerHall', -3, 3.3, -7.3)
    k.spot('courtyard', 7.5, 0.3, 8.5)
    k.spot('tomb', -8.2, 3.2, 5.5)
  },
  'raj-ghat'(k) {
    k.ground(32, 32)
    k.box('lawn', 31, 0.05, 31)
    k.box('path', 2, 0.07, 31, 0, 0, 0)
    k.box('path', 31, 0.07, 2, 0, 0, 0)
    k.box('lawn', 16, 0.5, 16)
    for (const [a, b] of [[[-8, -8], [8, -8]], [[8, -8], [8, 8]], [[8, 8], [1.6, 8]], [[-1.6, 8], [-8, 8]], [[-8, 8], [-8, -8]]] as [[number, number], [number, number]][]) k.wall('rubble', a, b, 1.2, 0.6, 0, false)
    for (const sx of [-1, 1]) k.box('rubbleDark', 0.7, 1.7, 0.7, sx * 1.8, 0, 8)
    k.box('marbleShade', 10, 0.09, 10, 0, 0.5)
    k.box('path', 2, 0.04, 3.2, 0, 0.5, 6.5)
    k.at(0, 0.59, 0, () => {
      k.box('black', 5.8, 0.3, 5.8)
      k.box('black', 4.4, 0.45, 4.4, 0, 0.3)
      k.at(0, 0.75, -1.6, () => {
        k.cyl('gold', 0.55, 0.36, 0.5)
        k.add('flame', new THREE.ConeGeometry(0.34, 1.3, 12).translate(0, 1.15, 0))
      })
    })
    for (const [x, z] of [[-12, -12], [12, -12], [-12, 12], [12, 12], [-12, -2.8], [12, 3], [-3, -12], [4, 12], [-12, 5], [12, -5], [4, -12], [-4, 12]]) k.tree(x, z, 1.5)
    k.spot('memorial', 1.9, 1.3, 1.6)
    k.spot('flame', 0, 3.1, -1.6)
    k.spot('enclosure', -8, 1.4, 3)
    k.spot('garden', 8.8, 0.4, 8.8)
  },
  'akshardham-delhi'(k) {
    k.ground(36, 36)
    k.box('water', 34, 0.1, 34)
    k.box('path', 28, 0.2, 28)
    k.sides(25, 25, (l) => {
      k.box('redstone', l + 2.4, 1.7, 2.4)
      k.arches(Math.floor(l / 1.1), l + 1.4, 1.2, 0.15, 1.21)
      k.at(0, 1.7, 0, () => {
        k.box('redLight', l + 2, 1.2, 1.9)
        k.arches(Math.floor(l / 1.1), l + 1, 0.82, 0.12, 0.96)
      })
      for (let i = 0; i < 9; i += 1) k.hemi('pink', 0.45, -l / 2 + (i * l) / 8, 2.9, 0, 1.15)
    })
    k.box('pink', 13, 1, 13)
    k.sides(13, 13, (l) => {
      for (let i = 0; i < 18; i += 1) k.box('redstone', 0.38, 0.46, 0.2, -l / 2 + 0.4 + (i * (l - 0.8)) / 17, 0.25, 0.08)
    })
    for (let i = 0; i < 5; i += 1) k.box('pink', 5 - i * 0.2, 0.2, 2.6 - i * 0.4, 0, i * 0.2, 7.6 - i * 0.2)
    k.at(0, 1, 0, () => {
      k.box('marbleShade', 11, 0.3, 11)
      k.at(0, 0.3, 0, () => {
        k.sides(9.2, 9.2, (l) => {
          for (let i = 0; i < 10; i += 1) k.cyl('pink', 0.15, 0.18, 2.5, -l / 2 + (i * l) / 9, 0, 0, 10)
          k.arches(9, l - 0.2, 2.1, 0.05, -0.1, 0, 'redLight', 0.72)
        })
        k.box('pink', 6.8, 2.5, 6.8)
        k.box('marbleShade', 10.4, 0.18, 10.4, 0, 2.5)
        k.box('pink', 8.4, 0.9, 8.4, 0, 2.68)
        k.box('marbleShade', 8.9, 0.14, 8.9, 0, 3.58)
        for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
          k.at(sx * 3.5, 3.72, sz * 3.5, () => {
            k.cyl('pink', 0.9, 0.95, 0.7, 0, 0, 0, 12)
            k.onion('pink', 0.95, 0, 0.7, 0, 0.95)
            k.finial(0, 2.35, 0, 0.8)
          })
        }
        for (const [x, z] of [[3.5, 0], [-3.5, 0], [0, 3.5], [0, -3.5]]) {
          k.at(x, 3.72, z, () => {
            k.cyl('pink', 0.7, 0.75, 0.6, 0, 0, 0, 12)
            k.onion('pink', 0.74, 0, 0.6, 0, 0.92)
            k.finial(0, 1.86, 0, 0.6)
          })
        }
        k.cyl('pink', 2.1, 2.35, 1.5, 0, 3.72, 0, 16)
        k.cyl('marbleShade', 2.5, 2.5, 0.12, 0, 5.22, 0, 16)
        k.onion('pink', 2.25, 0, 5.34, 0, 1.02)
        k.finial(0, 9.6, 0, 1.6)
      })
    })
    k.spot('dome', 0, 10, 1.5)
    k.spot('shrine', -3.5, 3.5, 4.8)
    k.spot('plinth', 6.6, 1, 6.6)
    k.spot('colonnade', 5, 3.4, 13.7)
    k.spot('water', 16.2, 0.3, 10)
  },
  'fatehpuri-masjid'(k) {
    k.ground(22, 24)
    k.box('paving', 21, 0.12, 23)
    k.at(0, 0.12, -3.5, () => {
      mosque(k, { w: 15, h: 3.8, d: 4.4, mat: 'redstone', trim: 'marbleShade', dome: 'redLight', arches: 7, domes: [[0, 2.3]], tall: 0.82 })
      for (const sx of [-1, 1]) k.minaret('redstone', 6.4, 0.42, sx * 7.4, 0, -0.5, { band: 'marble', dome: 'marble' })
    })
    for (const [a, b] of [[[-10, -3], [-10, 11]], [[10, -3], [10, 11]], [[-10, 11], [-2, 11]], [[2, 11], [10, 11]]] as [[number, number], [number, number]][]) k.wall('redstone', a, b, 1.8, 1, 0.12, false)
    for (const x of [-9.45, 9.45]) k.at(x, 0.12, 4, () => k.arches(11, 13, 1.2, 0.2, 0, 0), x > 0 ? -Math.PI / 2 : Math.PI / 2)
    k.at(0, 0.12, 11, () => {
      k.box('redstone', 4, 3.2, 1.5)
      k.portal('marbleShade', 2, 3.1, 0, -0.75, 0, 0.06)
    })
    k.at(0, 0.12, 3.5, () => {
      k.box('marbleShade', 4, 0.3, 4)
      k.box('water', 3.5, 0.33, 3.5)
    })
    k.spot('dome', 0, 7.6, -5.7)
    k.spot('pishtaq', 0, 3.4, -3.2)
    k.spot('minaret', 7.4, 6.6, -4)
    k.spot('water', 1.5, 0.6, 3.5)
    k.spot('courtyard', -5.5, 0.4, 5.5)
  },
}

export const modelledMonuments = Object.keys(builders)

/** Unknown slugs get a plain domed tomb, so a site added to the database still shows something honest. */
export function buildMonument(id: string): MonumentModel {
  const kit = new Kit()
  const build = builders[id] ?? ((k: Kit) => {
    k.ground(14, 14)
    k.box('buff', 10, 0.6, 10)
    k.at(0, 0.6, 0, () => tomb(k, { w: 5, h: 3, body: 'buff', trim: 'redstone', dome: 'buff', r: 1.6 }))
    k.spot('dome', 0, 6.4, 0)
    k.spot('pishtaq', 0, 2, 2.65)
    k.spot('plinth', 3.8, 0.6, 3.8)
  })
  build(kit)
  return kit.build()
}
