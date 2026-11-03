import { describe, expect, it } from 'vitest'
import { getMood } from './mood'

describe('getMood', () => {
  it('maps identification states to distinct moods', () => {
    expect(getMood('/identify')).toBe('dawn')
    expect(getMood('/identify', 'uncertain')).toBe('mist')
    expect(getMood('/identify', 'error')).toBe('overcast')
  })

  it('matches the most specific route before its parent', () => {
    expect(getMood('/plan/route')).toBe('dusk')
    expect(getMood('/plan')).toBe('noon')
  })

  it.each([
    ['/monument/taj-mahal', 'golden'],
    ['/explore', 'noon'],
    ['/nearby', 'noon'],
    ['/unknown', 'golden'],
  ] as const)('maps %s to %s', (pathname, mood) => {
    expect(getMood(pathname)).toBe(mood)
  })
})
