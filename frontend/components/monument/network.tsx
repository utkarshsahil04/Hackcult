'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { MonumentArt } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { getMonument, monuments } from '@/lib/catalog'
import connections from '@/lib/connections.json'

type Kind = { en: string; hi: string; color: string }

// Colour is not the only cue: every connection also names its kind in words below the graph.
const KINDS: Record<string, Kind> = {
  architectural_influence: { en: 'Architectural influence', hi: 'वास्तुकला का प्रभाव', color: '#B5452B' },
  successor_of: { en: 'Successor of', hi: 'का उत्तराधिकारी', color: '#C28A0E' },
  same_dynasty: { en: 'Same dynasty', hi: 'एक ही राजवंश', color: '#2F6F5E' },
  same_patron: { en: 'Same patron', hi: 'एक ही संरक्षक', color: '#5B4B8A' },
  historical_event: { en: 'Shared event', hi: 'साझा घटना', color: '#1F6C8F' },
  capital_relationship: { en: 'Capital link', hi: 'राजधानी से संबंध', color: '#8F3221' },
  burial_association: { en: 'Burial link', hi: 'समाधि से संबंध', color: '#5A4E3F' },
  co_located_world_heritage: { en: 'Same World Heritage site', hi: 'एक ही विश्व धरोहर स्थल', color: '#7A8F1F' },
}
const kindOf = (type: string): Kind => KINDS[type] ?? { en: type.replaceAll('_', ' '), hi: type.replaceAll('_', ' '), color: '#5A4E3F' }

// Only monuments with sourced connections can appear, so the ring never holds an empty node.
const linked = new Set(connections.flatMap((link) => [link.from, link.to]))
const ring = monuments.filter((m) => linked.has(m.id)).sort((a, b) => a.city.localeCompare(b.city) || a.id.localeCompare(b.id))
const place = new Map(ring.map((m, index) => {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / ring.length
  return [m.id, { x: 50 + 40 * Math.cos(angle), y: 50 + 40 * Math.sin(angle) }]
}))

export function ConnectionNetwork() {
  const { lang, setLang, t } = useLang()
  const [selected, setSelected] = useState<string | null>(null)
  const involved = (link: (typeof connections)[number]) => link.from === selected || link.to === selected
  const shown = selected ? connections.filter(involved) : []

  return (
    <main className="shell mx-auto max-w-2xl px-5 pb-12 pt-4 lg:pt-10" lang={lang}>
      <header className="mb-5 flex items-center justify-between lg:hidden">
        <Link aria-label={t.back} className="grid size-12 place-items-center rounded-full" href="/explore"><ArrowLeft aria-hidden="true" /></Link>
        <Toggle lang={lang} setLang={setLang} />
      </header>
      <Link className="link-primary hidden min-h-12 items-center gap-2 text-sm lg:inline-flex" href="/explore"><ArrowLeft aria-hidden="true" size={18} />{t.back}</Link>
      <h1 className="fraunces mt-3 text-4xl">{lang === 'hi' ? 'स्मारक कैसे जुड़े हैं' : 'How the monuments connect'}</h1>
      <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">
        {lang === 'hi'
          ? `${ring.length} स्मारकों के बीच ${connections.length} संबंध। हर संबंध दो स्वतंत्र प्रकाशकों के स्रोतों पर टिका है। किसी स्मारक को छुएं।`
          : `${connections.length} connections between ${ring.length} monuments. Each one rests on two independent publishers. Tap a monument to see how it links.`}
      </p>

      <div className="relative mx-auto my-8 aspect-square w-full max-w-lg" data-testid="connection-network">
        <svg aria-hidden="true" className="absolute inset-0 size-full" viewBox="0 0 100 100">
          {connections.map((link) => {
            const a = place.get(link.from)
            const b = place.get(link.to)
            if (!a || !b) return null
            const on = !selected || involved(link)
            return <line key={`${link.from}-${link.to}-${link.type}`} opacity={on ? 1 : 0.1} stroke={kindOf(link.type).color} strokeWidth={selected && on ? 0.9 : 0.45} x1={a.x} x2={b.x} y1={a.y} y2={b.y} />
          })}
        </svg>
        <div className="absolute left-1/2 top-1/2 w-32 -translate-x-1/2 -translate-y-1/2 text-center">
          {selected && <p className="fraunces rounded-md bg-[#FBF6EC]/90 px-1 text-sm leading-tight text-[#1F1A14]">{getMonument(selected).name[lang]}</p>}
        </div>
        {ring.map((m) => {
          const spot = place.get(m.id)!
          const on = !selected || selected === m.id || shown.some((link) => link.from === m.id || link.to === m.id)
          return (
            <button aria-label={m.name[lang]} aria-pressed={selected === m.id} className={`absolute size-12 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-2 shadow-md transition-opacity ${selected === m.id ? 'border-[#B5452B]' : 'border-[#E8A317]'} ${on ? '' : 'opacity-30'}`} key={m.id} onClick={() => setSelected(selected === m.id ? null : m.id)} style={{ left: `${spot.x}%`, top: `${spot.y}%` }} type="button">
              <MonumentArt alt="" className="size-full" id={m.id} />
            </button>
          )
        })}
      </div>

      {selected ? (
        <ul className="space-y-3" data-testid="connection-list">
          {shown.map((link) => {
            const other = getMonument(link.from === selected ? link.to : link.from)
            const kind = kindOf(link.type)
            return (
              <li className="rounded-xl border border-[#B5452B]/15 bg-[#FBF6EC] p-4" key={`${link.from}-${link.to}-${link.type}`}>
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[#5A4E3F]"><span aria-hidden="true" className="size-2.5 rounded-full" style={{ background: kind.color }} />{kind[lang]}</p>
                <Link className="fraunces mt-1 inline-flex min-h-12 items-center text-xl underline-offset-2 hover:underline" href={`/monument/${other.id}`}>{other.name[lang]}</Link>
                <p className="text-[15px] leading-[1.7]">{lang === 'hi' ? link.note_hi : link.note}</p>
                <p className="mt-2 text-xs text-[#5A4E3F]">{lang === 'hi' ? 'स्रोत' : 'Sources'}: {link.publishers.join(' · ')}</p>
              </li>
            )
          })}
        </ul>
      ) : (
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2" data-testid="connection-legend">
          {Object.entries(KINDS).map(([type, kind]) => (
            <li className="flex items-center gap-2 text-sm" key={type}><span aria-hidden="true" className="h-1 w-6 rounded-full" style={{ background: kind.color }} />{kind[lang]} ({connections.filter((link) => link.type === type).length})</li>
          ))}
        </ul>
      )}
    </main>
  )
}
