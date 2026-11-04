import { describe, expect, it } from 'vitest'
import { monuments } from './catalog'
import { journeyStats, parseJourney, parseTour, tourPlanHref } from './journey'
import { jsonLd, monumentDescription, monumentSchema } from './seo'

describe('journey data', () => {
  it('drops invalid, unknown and repeated visits', () => {
    const journey = parseJourney({ name: 'x'.repeat(99), visits: [
      { id: 'taj-mahal', date: '2026-01-02' },
      { id: 'taj-mahal', date: '2026-02-02' },
      { id: 'not-a-monument', date: '2026-01-02' },
      { id: 'red-fort', date: 'yesterday' },
      null,
    ] })
    expect(journey.name).toHaveLength(60)
    expect(journey.visits).toEqual([{ id: 'taj-mahal', date: '2026-01-02' }])
    expect(parseJourney('nonsense').visits).toEqual([])
    expect(parseTour(['taj-mahal', 'taj-mahal', 'nope', 3])).toEqual(['taj-mahal'])
  })

  it('counts distance in date order and suggests only unvisited monuments', () => {
    const stats = journeyStats([{ id: 'red-fort', date: '2026-03-01' }, { id: 'taj-mahal', date: '2026-01-01' }, { id: 'india-gate', date: '2026-02-01' }])
    expect(stats.ordered.map((visit) => visit.id)).toEqual(['taj-mahal', 'india-gate', 'red-fort'])
    expect(stats.places).toBe(3)
    expect(stats.km).toBeGreaterThan(150)
    expect(stats.level.en).toBe('Yatri')
    expect(stats.next).toHaveLength(3)
    expect(stats.next.map((m) => m.id)).not.toContain('india-gate')
  })

  it('handles an empty journey', () => {
    expect(journeyStats([])).toMatchObject({ places: 0, km: 0, next: [] })
  })

  it('reaches each level at its threshold', () => {
    const visits = (n: number) => monuments.slice(0, n).map((m) => ({ id: m.id, date: '2026-01-01' }))
    expect(journeyStats(visits(5)).level.en).toBe('Pathik')
    expect(journeyStats(visits(10)).level.en).toBe('Ghumakkad')
    expect(journeyStats(visits(20)).level.en).toBe('Virasat Rakshak')
  })

  it('plans at most 5 stops and picks the region from the first', () => {
    const params = new URL(tourPlanHref(['taj-mahal', 'agra-fort', 'akbars-tomb', 'itimad-ud-daulah', 'fatehpur-sikri', 'red-fort']), 'http://x').searchParams
    expect(params.get('must')).toBe('taj-mahal,agra-fort,akbars-tomb,itimad-ud-daulah,fatehpur-sikri')
    expect(params.get('city')).toBe('Agra')
  })
})

describe('search data', () => {
  it('keeps every description within the length search results show', () => {
    for (const monument of monuments) {
      expect(monumentDescription(monument).length, monument.id).toBeLessThanOrEqual(156)
      expect(monumentDescription(monument).length, monument.id).toBeGreaterThan(40)
    }
  })

  it('describes a monument with its location and photo', () => {
    const [place] = monumentSchema(monuments[0])['@graph'] as { geo: object; image: string; name: string }[]
    expect(place.name).toBe(monuments[0].name.en)
    expect(place.geo).toMatchObject({ latitude: monuments[0].lat })
    expect(place.image).toContain('wikimedia.org')
  })

  it('cannot break out of its script tag', () => {
    expect(jsonLd({ a: '</script><script>alert(1)</script>' })).not.toContain('<')
  })
})
