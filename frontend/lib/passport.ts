import { monuments } from './catalog'
import { regionOf, type Visit } from './journey'

/** Tilt in whole degrees (-6..6) hashed from the id, so server and client render the same stamp. */
export const stampTilt = (id: string) => [...id].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % 9973, 7) % 13 - 6

/** Every catalog monument as a stamp, grouped Delhi then Agra, with its visit date if collected. */
export function passportPages(visits: Visit[]) {
  const dates = new Map(visits.map((visit) => [visit.id, visit.date]))
  const pages = (['Delhi', 'Agra'] as const).map((region) => {
    const stamps = monuments.filter((monument) => regionOf(monument) === region).map((monument) => ({ monument, date: dates.get(monument.id) }))
    const collected = stamps.filter((stamp) => stamp.date).length
    return { region, stamps, collected, complete: collected === stamps.length }
  })
  return { pages, collected: pages.reduce((total, page) => total + page.collected, 0), total: monuments.length }
}

/** ISO dates are calendar days, so format in UTC to keep the same day in every timezone. */
export const stampDate = (date: string, lang: 'en' | 'hi', month: 'long' | 'short' = 'long') => new Date(date).toLocaleDateString(lang === 'hi' ? 'hi-IN' : 'en-IN', { day: 'numeric', month, year: 'numeric', timeZone: 'UTC' })
