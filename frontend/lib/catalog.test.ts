import * as THREE from 'three'
import { describe, expect, it } from 'vitest'
import { buildMonument, modelledMonuments } from '../components/heritage/monument-models'
import { architectureParts } from './architecture'
import { imageCredits, monuments, nearestMonuments } from './catalog'

describe('every monument card', () => {
  it('has a freely licensed Wikimedia photo with a credit', () => {
    for (const { id, image } of monuments) {
      const credit = imageCredits[id]
      expect(credit, id).toBeDefined()
      expect(image, id).toBe(credit.url)
      expect(credit.url, id).toMatch(/^https:\/\/(thumb|upload)\.wikimedia\.org\/wikipedia\/commons\/[^?]+$/)
      expect(credit.page, id).toMatch(/^https:\/\/commons\.wikimedia\.org\//)
      expect(credit.licence, id).toMatch(/^(cc[ -]?by|cc0|public domain)/i)
      expect(credit.artist, id).toBeTruthy()
    }
  })

  it('has its own 3D model, with marked parts that sit on the model', () => {
    for (const { id } of monuments) {
      expect(modelledMonuments, id).toContain(id)
      const model = buildMonument(id)
      const box = new THREE.Box3().setFromObject(model.group).expandByScalar(1.5)
      let triangles = 0
      model.group.traverse((node) => {
        if (node instanceof THREE.Mesh) triangles += node.geometry.attributes.position.count / 3
      })
      expect(triangles, `${id} is too heavy for a phone`).toBeLessThan(150_000)
      expect(model.spots.length, id).toBeGreaterThanOrEqual(3)
      for (const spot of model.spots) {
        expect(architectureParts[spot.part], `${id}: ${spot.part}`).toBeDefined()
        expect(box.containsPoint(new THREE.Vector3(...spot.at)), `${id}: ${spot.part} is off the model`).toBe(true)
      }
      model.dispose()
    }
  })

  it('has every part described in both languages', () => {
    for (const [id, part] of Object.entries(architectureParts)) {
      for (const lang of ['en', 'hi'] as const) {
        expect(part.title[lang], id).toBeTruthy()
        expect(part.desc[lang], id).toBeTruthy()
      }
    }
  })
})

describe('nearestMonuments', () => {
  it('leaves out the origin and sorts by distance', () => {
    const origin = monuments.find((m) => m.id === 'india-gate')!
    const near = nearestMonuments(origin, 4)
    expect(near).toHaveLength(4)
    expect(near.map((n) => n.monument.id)).not.toContain('india-gate')
    expect(near.map((n) => n.km)).toEqual([...near.map((n) => n.km)].sort((a, b) => a - b))
    expect(near[0].km).toBeLessThan(10)
  })
})
