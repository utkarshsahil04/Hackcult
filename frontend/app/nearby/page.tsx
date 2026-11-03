'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Map from '@/components/map'
import { MonumentArt } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { distanceKm, monuments } from '@/lib/catalog'

// Connaught Place, used until (or unless) the visitor shares their location.
const DELHI = { lat: 28.6315, lng: 77.2167 }

export default function Page() {
  const { lang, setLang } = useLang()
  const [origin, setOrigin] = useState(DELHI)
  const [located, setLocated] = useState(false)

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition((p) => {
      setOrigin({ lat: p.coords.latitude, lng: p.coords.longitude })
      setLocated(true)
    }, () => {})
  }, [])

  const nearest = monuments.map((m) => ({ m, d: distanceKm(origin, m) })).sort((a, b) => a.d - b.d).slice(0, 8)
  const title = lang === 'hi' ? 'आस-पास के स्मारक' : 'Nearby monuments'
  const hint = located ? (lang === 'hi' ? 'आपके स्थान से दूरी' : 'Distance from you') : (lang === 'hi' ? 'मध्य दिल्ली से दूरी' : 'Distance from central Delhi')
  return (
    <main className="shell relative h-svh overflow-hidden pb-16 lg:pb-0" lang={lang}>
      <div className="nearby-map absolute inset-0"><Map stops={nearest.map(({ m }) => m.id)} /></div>
      <div className="absolute left-4 right-4 top-4 z-10 flex items-center justify-between gap-3 safe-top">
        <Link href="/explore" className="flex min-h-12 items-center rounded-full border border-[#E8A317]/40 bg-[#FBF6EC] px-4 py-2 text-sm font-semibold text-[#1F1A14] shadow-lg">{title}</Link>
        <div className="rounded-full bg-[#FBF6EC] shadow-lg lg:hidden"><Toggle lang={lang} setLang={setLang} /></div>
      </div>
      <section className="absolute bottom-16 z-10 w-full rounded-t-3xl border-t border-[#E8A317]/30 bg-[#FBF6EC] p-4 shadow-[0_-12px_30px_rgba(31,26,20,.15)] lg:bottom-0" aria-labelledby="nearby-heading">
        <h1 className="fraunces text-2xl text-[#1F1A14]" id="nearby-heading">{title}</h1>
        <p className="text-xs text-[#5A4E3F]">{hint}</p>
        <div className="mt-3 flex snap-x gap-3 overflow-x-auto pb-2">
          {nearest.map(({ m, d }) => (
            <Link href={`/monument/${m.id}`} className="min-w-44 snap-start rounded-xl border border-[#E8A317]/35 bg-[#EADBC0]/45 p-2.5 text-[#1F1A14]" key={m.id}>
              <MonumentArt alt="" className="h-20 w-full rounded-lg" id={m.id} />
              <div className="mt-2 break-words text-sm font-semibold">{m.name[lang]}</div>
              <div className="text-xs text-[#5A4E3F]">{d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`}</div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  )
}
