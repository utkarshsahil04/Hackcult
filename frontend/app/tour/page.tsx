'use client'

import { use, useState } from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { useLang } from '@/components/raahein'
import { MonumentArt } from '@/components/heritage'
import { getMonument } from '@/lib/catalog'
import { parseSharedTour, setTour, tourPlanHref, useTour } from '@/lib/journey'

const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value) ?? null

export default function SharedTourPage({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const query = use(searchParams)
  const { stops, name } = parseSharedTour(first(query.stops), first(query.name))
  const { lang } = useLang()
  const tour = useTour()
  const [confirming, setConfirming] = useState(false)
  const [status, setStatus] = useState('')
  const hi = lang === 'hi'

  const save = () => {
    setTour(stops)
    setConfirming(false)
    setStatus(hi ? 'आपके टूर में सहेजा गया' : 'Saved to your tour')
  }
  const onSave = () => (tour.length && tour.join(',') !== stops.join(',') ? setConfirming(true) : save())

  if (!stops.length) return (
    <main className="mx-auto min-h-svh max-w-2xl px-5 py-10 pb-24 text-[#1F1A14]" lang={lang}>
      <h1 className="fraunces text-4xl">{hi ? 'यह टूर खाली है' : 'This tour has no stops'}</h1>
      <p className="mt-3 text-[#5A4E3F]">{hi ? 'लिंक में कोई मान्य स्मारक नहीं मिला।' : 'We could not find any monuments in this link.'}</p>
      <Link className="link-inverse mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-5 font-semibold" href="/explore">{hi ? 'स्मारक देखें' : 'Explore monuments'}<ArrowRight aria-hidden="true" size={16} /></Link>
    </main>
  )

  return (
    <main className="mx-auto min-h-svh max-w-2xl px-5 py-10 pb-24 text-[#1F1A14]" lang={lang}>
      <p className="text-sm font-semibold uppercase tracking-wide text-[#8F3221]">{hi ? 'साझा किया गया टूर' : 'A shared tour'}</p>
      <h1 className="fraunces mt-1 break-words text-4xl">{name || (hi ? 'किसी ने आपके साथ एक टूर साझा किया' : 'Someone shared a tour with you')}</h1>
      <ol className="mt-6 space-y-3">
        {stops.map(getMonument).map((stop) => (
          <li data-testid="tour-stop" key={stop.id}>
            <Link className="flex min-h-12 items-center gap-4 rounded-2xl border border-[#EADBC0] bg-[#FBF6EC] p-3" href={`/monument/${stop.id}`}>
              <MonumentArt alt="" className="size-16 shrink-0 rounded-xl" id={stop.id} />
              <span className="min-w-0">
                <span className="fraunces block text-lg">{stop.name[lang]}</span>
                <span className="block text-sm text-[#5A4E3F]">{stop.city}</span>
              </span>
            </Link>
          </li>
        ))}
      </ol>
      {confirming ? (
        <div className="mt-6 rounded-2xl border border-[#E8A317] bg-[#FBF6EC] p-4">
          <p>{hi ? `इससे आपके टूर के ${tour.length} पड़ाव बदल जाएंगे।` : `This replaces the ${tour.length} stops in your tour.`}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="link-inverse min-h-12 rounded-full bg-[#B5452B] px-5 font-semibold" onClick={save} type="button">{hi ? 'हाँ, बदलें' : 'Replace my tour'}</button>
            <button className="min-h-12 rounded-full border border-[#5A4E3F] px-5 font-semibold" onClick={() => setConfirming(false)} type="button">{hi ? 'रद्द करें' : 'Keep my tour'}</button>
          </div>
        </div>
      ) : (
        <div className="mt-6 flex flex-wrap gap-2">
          <button className="min-h-12 rounded-full border border-[#B5452B] px-5 font-semibold text-[#8F3221]" onClick={onSave} type="button">{hi ? 'मेरे टूर में सहेजें' : 'Save to my tour'}</button>
          <Link className="link-inverse inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-5 font-semibold" href={tourPlanHref(stops)}>{hi ? 'यह दिन प्लान करें' : 'Plan this day'}<ArrowRight aria-hidden="true" size={16} /></Link>
        </div>
      )}
      <p aria-live="polite" className="mt-3 text-sm text-[#5A4E3F]" role="status">{status}</p>
    </main>
  )
}
