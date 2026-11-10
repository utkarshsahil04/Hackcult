import { describe, expect, it } from 'vitest'
import { monuments } from './catalog'
import { regionOf } from './journey'
import { passportPages, stampDate, stampTilt } from './passport'

describe('heritage passport', () => {
  it('has one stamp per monument, grouped by city', () => {
    const { pages, collected, total } = passportPages([{ id: 'taj-mahal', date: '2026-11-04' }])
    expect(total).toBe(monuments.length)
    expect(pages.flatMap((page) => page.stamps)).toHaveLength(monuments.length)
    expect(collected).toBe(1)
    const agra = pages.find((page) => page.region === 'Agra')!
    expect(agra.stamps.find((stamp) => stamp.monument.id === 'taj-mahal')?.date).toBe('2026-11-04')
    expect(agra.complete).toBe(false)
  })

  it('marks a city complete only when every stamp is collected', () => {
    const delhi = monuments.filter((monument) => regionOf(monument) === 'Delhi').map(({ id }) => ({ id, date: '2026-01-01' }))
    expect(passportPages(delhi).pages.map((page) => page.complete)).toEqual([true, false])
  })

  it('tilts deterministically within a few degrees', () => {
    for (const { id } of monuments) {
      expect(stampTilt(id)).toBe(stampTilt(id))
      expect(Math.abs(stampTilt(id))).toBeLessThanOrEqual(6)
    }
  })

  it('formats the visit day without timezone drift', () => {
    expect(stampDate('2026-11-04', 'en')).toBe('4 November 2026')
  })
})
