'use client'

import { useEffect, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { getMonument, monuments } from '@/lib/catalog'

export type RouteLine = number[][][]
export type MapProps = {
  /** Numbers these monuments in order and shows only them, unless `background` adds context. */
  stops?: string[]
  /** Draws a line through `stops`. */
  route?: boolean
  /** Road shape per leg. Until it arrives, or if unavailable, legs are straight lines. */
  line?: RouteLine | null
  /** Leg to emphasise and zoom to. */
  activeLeg?: number | null
  /** Other monuments shown as small markers, which can be chosen with `onPick`. */
  background?: string[]
  onPick?: (id: string) => void
}

const STOP_ICON = (label: string) => L.divIcon({ className: 'dome-pin', html: `<span>${label}</span>`, iconSize: [32, 32], iconAnchor: [16, 16] })
const SMALL_ICON = L.divIcon({ className: 'dome-pin dome-pin-small', html: '<span></span>', iconSize: [20, 20], iconAnchor: [10, 10] })
const TRAVEL_SECONDS_PER_LEG = 5

const point = (id: string): L.LatLngTuple => { const m = getMonument(id); return [m.lat, m.lng] }

/** Position along a polyline, for t from 0 to 1. */
function along(line: L.LatLngTuple[], lengths: number[], total: number, t: number): L.LatLngTuple {
  let distance = t * total
  for (let i = 1; i < line.length; i += 1) {
    if (distance <= lengths[i - 1] || i === line.length - 1) {
      const share = lengths[i - 1] ? Math.min(distance / lengths[i - 1], 1) : 0
      return [line[i - 1][0] + (line[i][0] - line[i - 1][0]) * share, line[i - 1][1] + (line[i][1] - line[i - 1][1]) * share]
    }
    distance -= lengths[i - 1]
  }
  return line[0]
}

export default function LeafletMap({ route = false, stops, line, activeLeg = null, background, onPick }: MapProps) {
  const element = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const pick = useRef(onPick)
  const stopKey = stops?.join(',') ?? ''
  const backgroundKey = background?.join(',') ?? ''
  const lineKey = JSON.stringify(line ?? null)

  useEffect(() => { pick.current = onPick }, [onPick])

  useEffect(() => {
    if (!element.current) return
    const created = L.map(element.current, { zoomControl: false }).setView([27.8, 78], 6)
    L.control.zoom({ position: 'bottomright' }).addTo(created)
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' }).addTo(created)
    const pane = tiles.getContainer()
    if (pane) pane.style.filter = 'sepia(.28) saturate(.78) brightness(1.04)'
    map.current = created
    return () => {
      created.remove()
      map.current = null
    }
  }, [])

  // Markers: changing the selection must not rebuild the map or lose its tiles.
  useEffect(() => {
    const current = map.current
    if (!current) return
    const layer = L.layerGroup().addTo(current)
    const ids = stopKey ? stopKey.split(',') : []
    const others = backgroundKey ? backgroundKey.split(',').filter((id) => !ids.includes(id)) : ids.length ? [] : monuments.map((m) => m.id)
    const addMarker = (id: string, icon: L.DivIcon, z: number) => {
      const monument = getMonument(id)
      const marker = L.marker(point(id), { title: monument.name.en, icon, zIndexOffset: z }).addTo(layer)
      if (pick.current) {
        marker.on('click', () => pick.current?.(id))
      } else {
        const link = document.createElement('a')
        link.href = `/monument/${monument.id}`
        link.textContent = `${monument.name.en} · ${monument.city}`
        marker.bindPopup(link)
      }
    }
    others.forEach((id) => addMarker(id, pick.current ? SMALL_ICON : STOP_ICON(''), 0))
    ids.forEach((id, index) => addMarker(id, STOP_ICON(String(index + 1)), 1000))
    const everything = [...ids, ...others].map(point)
    if (everything.length) current.fitBounds(L.latLngBounds(everything), { padding: [48, 48], maxZoom: 14, animate: false })
    return () => { layer.remove() }
  }, [stopKey, backgroundKey])

  // The route: one casing and one flowing line per leg, plus a marker that travels it in order.
  useEffect(() => {
    const current = map.current
    if (!current || !route || !stopKey) return
    const ids = stopKey.split(',')
    if (ids.length < 2) return
    const shaped: RouteLine | null = JSON.parse(lineKey)
    const straight = ids.slice(1).map((id, index): L.LatLngTuple[] => [point(ids[index]), point(id)])
    const legs: L.LatLngTuple[][] = shaped?.length === straight.length ? shaped.map((leg) => leg.map(([lat, lng]): L.LatLngTuple => [lat, lng])) : straight
    const layer = L.layerGroup().addTo(current)
    legs.forEach((leg, index) => {
      const active = activeLeg === index
      const dimmed = activeLeg !== null && !active
      L.polyline(leg, { color: '#FBF6EC', weight: active ? 11 : 8, opacity: dimmed ? .5 : .95, interactive: false }).addTo(layer)
      L.polyline(leg, { color: '#8F3221', weight: active ? 7 : 5, opacity: dimmed ? .35 : 1, interactive: false }).addTo(layer)
      L.polyline(leg, { color: '#F6D58A', weight: active ? 3 : 2, opacity: dimmed ? .4 : 1, dashArray: '2 14', lineCap: 'round', className: 'route-flow', interactive: false }).addTo(layer)
    })
    if (activeLeg !== null && legs[activeLeg]) current.fitBounds(L.latLngBounds(legs[activeLeg]), { padding: [70, 70], maxZoom: 15 })
    else current.fitBounds(L.latLngBounds(legs.flat()), { padding: [48, 48], maxZoom: 14 })

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return () => { layer.remove() }

    // The traveller follows the whole route, then starts again, so the order of travel is obvious.
    const path = activeLeg !== null && legs[activeLeg] ? legs[activeLeg] : legs.flat()
    const lengths = path.slice(1).map((p, index) => current.distance(path[index], p))
    const total = lengths.reduce((sum, value) => sum + value, 0)
    const traveller = L.marker(path[0], { icon: L.divIcon({ className: 'route-traveller', iconSize: [18, 18], iconAnchor: [9, 9] }), interactive: false, keyboard: false, zIndexOffset: 2000 }).addTo(layer)
    const duration = (activeLeg !== null ? 1 : legs.length) * TRAVEL_SECONDS_PER_LEG * 1000
    const began = performance.now()
    let frame = 0
    const move = (now: number) => {
      frame = requestAnimationFrame(move)
      if (total) traveller.setLatLng(along(path, lengths, total, ((now - began) % duration) / duration))
    }
    frame = requestAnimationFrame(move)
    return () => {
      cancelAnimationFrame(frame)
      layer.remove()
    }
  }, [route, stopKey, lineKey, activeLeg])

  return <div aria-label={route ? 'Planned route map' : 'Monument map'} className="h-full w-full" ref={element} role="region" />
}
