'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Map from '@/components/map'
import { MonumentArt } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { fetchNearby, type ApiPlace } from '@/lib/api'
import { monuments } from '@/lib/mock'

export default function Page() {
  const { lang, setLang } = useLang()
  const [places, setPlaces] = useState<ApiPlace[]>([])

  useEffect(() => {
    fetchNearby('taj-mahal').then(setPlaces).catch(() => {})
  }, [])

  const title = lang === 'hi' ? 'आस-पास के स्मारक' : 'Nearby monuments'
  return (
    <main className="shell relative h-svh overflow-hidden pb-16 lg:pb-0" lang={lang}>
      <div className="nearby-map absolute inset-0"><Map /></div>
      <div className="absolute left-4 right-4 top-4 z-10 flex items-center justify-between gap-3 safe-top">
        <Link href="/explore" className="flex min-h-12 items-center rounded-full border border-[#E8A317]/40 bg-[#FBF6EC] px-4 py-2 text-sm font-semibold text-[#1F1A14] shadow-lg">{title}</Link>
        <div className="rounded-full bg-[#FBF6EC] shadow-lg lg:hidden"><Toggle lang={lang} setLang={setLang} /></div>
      </div>
      <section className="absolute bottom-16 z-10 w-full rounded-t-3xl border-t border-[#E8A317]/30 bg-[#FBF6EC] p-4 shadow-[0_-12px_30px_rgba(31,26,20,.15)] lg:bottom-0" aria-labelledby="nearby-heading">
        <h1 className="font-[var(--font-fraunces)] text-2xl text-[#1F1A14]" id="nearby-heading">{title}</h1>
        <div className="mt-3 flex snap-x gap-3 overflow-x-auto pb-2">
          {places.length > 0 ? (
            places.map((place, index) => {
              const targetSlug = place.associated_monument || 'taj-mahal'
              return (
                <Link href={`/monument/${targetSlug}`} className="min-w-40 snap-start rounded-xl border border-[#E8A317]/35 bg-[#EADBC0]/45 p-2 text-[#1F1A14]" key={`${place.name}-${index}`}>
                  <MonumentArt alt="" className="h-20 w-full rounded-lg" id={targetSlug} />
                  <div className="mt-2 break-words text-sm font-semibold">{place.name}</div>
                  <div className="text-xs text-[#5A4E3F]">{place.category}{place.distance_m ? ` · ${Math.round(place.distance_m)}m` : ''}</div>
                </Link>
              )
            })
          ) : (
            monuments.slice(0, 4).map((monument) => (
              <Link href={`/monument/${monument.id}`} className="min-w-40 snap-start rounded-xl border border-[#E8A317]/35 bg-[#EADBC0]/45 p-2 text-[#1F1A14]" key={monument.id}>
                <MonumentArt alt="" className="h-20 w-full rounded-lg" id={monument.id} />
                <div className="mt-2 break-words text-sm font-semibold">{monument.name[lang]}</div>
                <div className="text-xs text-[#5A4E3F]">{monument.city}</div>
              </Link>
            ))
          )}
        </div>
      </section>
    </main>
  )
}
