/**
 * Raahein API client — all calls go through here.
 */

import { findMonument, type Monument, type Lang } from './catalog'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

// ─── helpers ──────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw Object.assign(new Error(body.message ?? `HTTP ${res.status}`), { status: res.status, code: body.code })
  }
  return res.json() as Promise<T>
}

// ─── recognition ─────────────────────────────────────────────────────────────

export type IdentifyResult =
  | { status: 'match'; monument: Monument }
  | { status: 'uncertain'; candidates: Array<{ slug: string; name: string; score: number }> }
  | { status: 'error' }

export async function identify(file: File): Promise<IdentifyResult> {
  if (!file.type.startsWith('image/') || file.size === 0 || file.size > 6 * 1024 * 1024) {
    throw new Error('Invalid image')
  }
  // A failed request is an error, never a guess: "broken" must not look like a match or like "not sure".
  let data: { status: string; candidates: Array<{ slug: string; name: string; score: number }> }
  try {
    const body = new FormData()
    body.append('photo', file)
    const res = await fetch(`${BASE}/api/recognition/identify`, { method: 'POST', body })
    if (!res.ok) return { status: 'error' }
    data = await res.json()
  } catch {
    return { status: 'error' }
  }
  const known = data.candidates.filter((c) => findMonument(c.slug))
  const top = data.candidates[0] && findMonument(data.candidates[0].slug)
  if (data.status === 'ok' && top) return { status: 'match', monument: top }
  if (data.status === 'ok' || data.status === 'uncertain') return { status: 'uncertain', candidates: known }
  return { status: 'error' }
}

// ─── monuments ────────────────────────────────────────────────────────────────

export type ApiSource = { title: string; url?: string; publisher: string; source_type: string; note?: string | null }
export type ApiClaim = { key: string; type: string; text: string; is_legend: boolean; sources: ApiSource[] }
export type ApiMonumentProfile = {
  slug: string; name: string; description: string
  latitude: number; longitude: number; era: string
  architectural_style: string; location: string; city: string
  claims: ApiClaim[]; sources: ApiSource[]
}

export async function fetchMonument(slug: string): Promise<ApiMonumentProfile | null> {
  if (!BASE) return null
  return apiFetch<ApiMonumentProfile>(`/api/monuments/${slug}`).catch(() => null)
}

export type ApiRelated = {
  monument: { slug: string; name: string; city: string }
  related: Array<{
    relation_type: string; direction: string; note?: string | null
    monument: { slug: string; name: string; city: string }
    sources: ApiSource[]
  }>
}

export async function fetchRelated(slug: string): Promise<ApiRelated | null> {
  if (!BASE) return null
  return apiFetch<ApiRelated>(`/api/monuments/${slug}/related`).catch(() => null)
}

// ─── stories ──────────────────────────────────────────────────────────────────

export type ApiStory = {
  slug: string; language: string; story_type: string
  body: string; audio_key: string | null; model_version: string; generated_at: string
}

export async function fetchStory(slug: string, language: Lang, story_type = 'visitor'): Promise<ApiStory | null> {
  if (!BASE) return null
  return apiFetch<ApiStory>(`/api/stories/${slug}?language=${language}&story_type=${story_type}`).catch(() => null)
}

// ─── places (nearby) ─────────────────────────────────────────────────────────

export type ApiPlace = {
  name: string; category: string; latitude: number; longitude: number
  osm_id?: string | null; osm_type?: string | null; source?: string | null
  associated_monument: string; distance_m?: number | null; tags?: Record<string, string> | null
}

export async function fetchNearby(slug: string, radius_m = 2000): Promise<ApiPlace[]> {
  if (!BASE) return []
  return apiFetch<ApiPlace[]>(`/api/places/nearby?monument_slug=${slug}&radius_m=${radius_m}`).catch(() => [])
}

// ─── tours / plan ─────────────────────────────────────────────────────────────

export type TourStop = { monument_slug: string; name: string; arrival_time_min: number; visit_duration_min: number; departure_time_min: number; travel_time_to_next_min?: number | null; travel_distance_to_next_m?: number | null }
export type TourPlanResponse = {
  is_feasible: boolean; status_message: string; solver_status: string; is_validated: boolean; explanation: string
  itinerary: { stops: TourStop[]; total_time_min: number; total_travel_time_min: number; total_travel_distance_m?: number | null; time_budget_min: number }
  metrics?: { stop_count: number; max_stops: number; budget_utilisation: number; travel_share: number; slack_min: number; is_optimal: boolean | null; preset: string } | null
}

export type RouteLineResponse = { source: 'roads' | 'straight'; legs: number[][][] }

export async function fetchRouteLine(stops: string[], profile: string): Promise<RouteLineResponse | null> {
  return apiFetch<RouteLineResponse>('/api/tours/route-line', { method: 'POST', body: JSON.stringify({ stops, profile }) }).catch(() => null)
}

export async function planTour(params: {
  start_monument?: string
  time_budget_minutes: number
  profile: string
  preset?: string
  interests?: string[]
  must_visit?: string[]
  max_stops?: number
  preferences?: Record<string, unknown>
}): Promise<TourPlanResponse | null> {
  return apiFetch<TourPlanResponse>('/api/tours/plan', {
    method: 'POST',
    body: JSON.stringify({ must_visit: [], preferences: {}, return_to_start: false, time_limit_seconds: 1, ...params }),
  }).catch(() => null)
}
