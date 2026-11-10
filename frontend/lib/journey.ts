import { useSyncExternalStore } from 'react'
import { distanceKm, eraOf, findMonument, nearestMonuments, type Monument } from './catalog'

// shortcut: saved in this browser only, so clearing site data loses it, upgrade with accounts (backend/docs/PROFILE_ARCHITECTURE.md).
function createStore<T>(key: string, parse: (raw: unknown) => T, empty: T) {
  let cache: T | undefined
  const listeners = new Set<() => void>()
  const read = () => {
    if (cache === undefined) {
      try {
        const raw = localStorage.getItem(key)
        cache = raw ? parse(JSON.parse(raw)) : empty
      } catch {
        cache = empty
      }
    }
    return cache
  }
  const write = (next: T) => {
    cache = next
    try {
      localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // Storage can be blocked. The change still applies until the page is closed.
    }
    listeners.forEach((listener) => listener())
  }
  const subscribe = (listener: () => void) => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== key) return
      cache = undefined
      listener()
    }
    listeners.add(listener)
    window.addEventListener('storage', onStorage)
    return () => {
      listeners.delete(listener)
      window.removeEventListener('storage', onStorage)
    }
  }
  return { read, write, useValue: () => useSyncExternalStore(subscribe, read, () => empty) }
}

export type Visit = { id: string; date: string }
export type Journey = { name: string; visits: Visit[] }

/** Stored data can be stale or edited by hand, so keep only what is still valid. */
export function parseJourney(raw: unknown): Journey {
  const data = (raw ?? {}) as { name?: unknown; visits?: unknown }
  const seen = new Set<string>()
  const visits = (Array.isArray(data.visits) ? data.visits : []).filter((visit: Visit) => {
    if (typeof visit?.id !== 'string' || !findMonument(visit.id) || seen.has(visit.id)) return false
    seen.add(visit.id)
    return /^\d{4}-\d{2}-\d{2}$/.test(String(visit.date))
  }) as Visit[]
  return { name: typeof data.name === 'string' ? data.name.slice(0, 60) : '', visits }
}

export const parseTour = (raw: unknown): string[] => [...new Set(Array.isArray(raw) ? raw : [])].filter((id): id is string => typeof id === 'string' && Boolean(findMonument(id)))

const journeyStore = createStore<Journey>('raahein-journey', parseJourney, { name: '', visits: [] })
const tourStore = createStore<string[]>('raahein-tour', parseTour, [])

export const useJourney = journeyStore.useValue
export const useTour = tourStore.useValue

export const today = () => new Date().toLocaleDateString('en-CA')

export function toggleVisit(id: string) {
  const journey = journeyStore.read()
  const visited = journey.visits.some((visit) => visit.id === id)
  journeyStore.write({ ...journey, visits: visited ? journey.visits.filter((visit) => visit.id !== id) : [...journey.visits, { id, date: today() }] })
}

export function setVisitDate(id: string, date: string) {
  if (!date) return
  const journey = journeyStore.read()
  journeyStore.write({ ...journey, visits: journey.visits.map((visit) => visit.id === id ? { ...visit, date } : visit) })
}

export const setJourneyName = (name: string) => journeyStore.write({ ...journeyStore.read(), name: name.slice(0, 60) })
export const clearJourney = () => journeyStore.write({ name: '', visits: [] })

export function toggleTour(id: string) {
  const tour = tourStore.read()
  tourStore.write(tour.includes(id) ? tour.filter((stop) => stop !== id) : [...tour, id])
}

/** Matches hard_max_stops in backend/app/planner/data/plan_presets.json. */
export const MAX_STOPS = 5

export const regionOf = (m: { lat: number }) => m.lat < 28 ? 'Agra' : 'Delhi'

/** Only stops in one region can share a day. */
export function tourPlanHref(tour: string[]) {
  const stops = tour.slice(0, MAX_STOPS)
  const first = stops[0] ? findMonument(stops[0]) : undefined
  return `/plan/route?${new URLSearchParams({ hours: '8', mode: 'auto', stops: String(MAX_STOPS), must: stops.join(','), city: first ? regionOf(first) : 'Delhi' })}`
}

/** Replaces the whole tour, used when saving a shared one. */
export const setTour = (stops: string[]) => tourStore.write(parseTour(stops).slice(0, MAX_STOPS))

export function tourShareHref(stops: string[], name?: string) {
  const params = new URLSearchParams({ stops: stops.slice(0, MAX_STOPS).join(',') })
  if (name?.trim()) params.set('name', name.trim().slice(0, 60))
  return `/tour?${params}`
}

/** Shared links come from anyone, so keep only known ids and a short plain-text name. */
export const parseSharedTour = (stops: string | null, name: string | null) => ({
  stops: parseTour((stops ?? '').split(',').map((id) => id.trim())).slice(0, MAX_STOPS),
  name: (name ?? '').trim().slice(0, 60),
})

export const LEVELS = [
  { min: 20, en: 'Virasat Rakshak', hi: 'विरासत रक्षक', noteEn: 'Guardian of heritage', noteHi: 'धरोहर के रक्षक' },
  { min: 10, en: 'Ghumakkad', hi: 'घुमक्कड़', noteEn: 'Seasoned wanderer', noteHi: 'अनुभवी यात्री' },
  { min: 5, en: 'Pathik', hi: 'पथिक', noteEn: 'Traveller on the path', noteHi: 'राह का यात्री' },
  { min: 0, en: 'Yatri', hi: 'यात्री', noteEn: 'At the start of the road', noteHi: 'यात्रा की शुरुआत' },
] as const

export function journeyStats(visits: Visit[], suggest = 3) {
  const ordered = [...visits].sort((a, b) => a.date.localeCompare(b.date))
  const places = ordered.map((visit) => findMonument(visit.id)).filter((m): m is Monument => Boolean(m))
  const km = places.slice(1).reduce((total, place, index) => total + distanceKm(places[index], place), 0)
  const visited = new Set(places.map((place) => place.id))
  const last = places.at(-1)
  return {
    ordered,
    places: places.length,
    cities: new Set(places.map((place) => place.city)).size,
    eras: new Set(places.map(eraOf)).size,
    km: Math.round(km),
    level: LEVELS.find((level) => places.length >= level.min) ?? LEVELS[3],
    next: last ? nearestMonuments(last, suggest + visited.size).filter(({ monument }) => !visited.has(monument.id)).slice(0, suggest).map(({ monument }) => monument) : [],
  }
}
