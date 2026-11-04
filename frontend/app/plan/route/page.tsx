'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Box, Scale, X } from 'lucide-react'
import Map from '@/components/map'
import { KolamLoader, Monument3DViewer, VineDivider } from '@/components/heritage'
import { useLang } from '@/components/raahein'
import { planTour, type TourPlanResponse } from '@/lib/api'
import { findMonument, getMonument } from '@/lib/catalog'
import { transitions } from '@/lib/motion'

function RouteContent() {
  const { lang, t } = useLang()
  const params = useSearchParams()
  const requestedHours = Number(params.get('hours')) || 6
  const hours = Math.min(10, Math.max(2, requestedHours))
  const maxStops = Number(params.get('stops')) || undefined
  const mode = params.get('mode')
  const preset = params.get('preset') || undefined
  const city = params.get('city') || 'Delhi'
  const interests = params.get('interests') || ''
  const must = params.get('must') || ''
  const modeLabel = mode === 'auto' ? t.auto : t.walk
  const [planData, setPlanData] = useState<TourPlanResponse | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [started, setStarted] = useState(false)
  const [viewing3D, setViewing3D] = useState<string | null>(null)

  useEffect(() => {
    if (!viewing3D) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setViewing3D(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [viewing3D])

  useEffect(() => {
    let live = true
    planTour({
      time_budget_minutes: hours * 60,
      profile: mode === 'auto' ? 'driving-car' : 'foot-walking',
      preset,
      max_stops: maxStops,
      interests: interests ? interests.split(',') : [],
      must_visit: must ? must.split(',') : [],
      preferences: { city },
    }).then((plan) => {
      if (!live) return
      setPlanData(plan)
      setStatus(plan ? 'ready' : 'error')
    })
    return () => { live = false }
  }, [hours, mode, preset, maxStops, interests, city, must])

  const impossible = planData !== null && !planData.is_feasible
  const stops = (planData?.is_feasible ? planData.itinerary.stops : []).filter((s) => findMonument(s.monument_slug)).map((s) => {
    const start = 9 * 60 + Math.round(s.arrival_time_min)
    return { id: s.monument_slug, time: `${String(Math.floor(start / 60)).padStart(2, '0')}:${String(start % 60).padStart(2, '0')}`, duration: Math.round(s.visit_duration_min) }
  })
  const distance = Math.round((planData?.itinerary?.total_travel_distance_m ?? 0) / 1000)
  const withParams = (changes: Record<string, string>) => `/plan/route?${new URLSearchParams({ ...Object.fromEntries(params), ...changes })}`
  const hm = (min: number) => { const m = Math.round(min); return `${Math.floor(m / 60)}h ${m % 60}m` }

  if (status === 'loading') return <main className="shell grid min-h-svh place-items-center" role="status"><div className="text-center"><KolamLoader /><p className="mt-3 text-sm text-[#5A4E3F]">{lang === 'hi' ? 'आपका रास्ता बन रहा है…' : 'Building your path…'}</p></div></main>
  if (status === 'error') return (
    <main className="shell grid min-h-[70svh] place-items-center px-5" lang={lang}>
      <div className="card max-w-md p-8 text-center" role="alert">
        <h1 className="fraunces text-3xl">{lang === 'hi' ? 'योजना अभी नहीं बन सकी' : 'We could not build your plan'}</h1>
        <p className="mt-3 text-[#5A4E3F]">{lang === 'hi' ? 'योजना सेवा से संपर्क नहीं हो पाया। कृपया फिर कोशिश करें।' : 'The planning service could not be reached. Please try again.'}</p>
        <Link href="/plan" className="link-inverse mt-6 flex min-h-12 items-center justify-center rounded-full bg-[#B5452B] px-5 font-semibold">{t.change}</Link>
      </div>
    </main>
  )

  return (
    <LazyMotion features={domAnimation}>
      <main className="shell min-h-svh bg-[#EADBC0] lg:grid lg:max-w-none lg:grid-cols-[420px_minmax(0,1fr)] lg:p-0" lang={lang}>
        <div className="relative h-[48svh] lg:sticky lg:top-0 lg:col-start-2 lg:row-start-1 lg:h-svh">
          <Map route stops={stops.map((stop) => stop.id)} />
          <div className="absolute left-4 right-4 top-4 z-10 flex flex-wrap gap-2 safe-top">
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm shadow">{hours} {t.hours}</span>
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm shadow">{distance} km</span>
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm shadow">{modeLabel}</span>
          </div>
        </div>
        <div className="min-h-[52svh] rounded-t-3xl bg-[#FBF6EC] p-5 lg:col-start-1 lg:row-start-1 lg:overflow-y-auto lg:rounded-none lg:p-8">
          {impossible ? (
            <m.div animate={{ opacity: 1, y: 0 }} initial={false} transition={transitions.base}>
              <m.div animate={{ rotate: [0, 8, 0] }} className="mb-3 text-[#B5452B]" transition={transitions.base}><Scale aria-hidden="true" /></m.div>
              <h1 className="fraunces text-3xl">{t.impossible}</h1>
              <p className="my-5 rounded-2xl border border-[#E8A317]/40 bg-[#EADBC0]/50 p-4 text-[#5A4E3F]">{lang === 'hi' ? `${hours} घंटे में इन विकल्पों के साथ कोई रास्ता नहीं बन पाया।` : `No route fits ${hours} hours with these choices.`}</p>
              <div className="space-y-2">
                <Link href={withParams({ hours: '9' })} className="link-inverse flex min-h-12 w-full items-center justify-center rounded-full bg-[#B5452B] px-5 text-center">{t.addTime}</Link>
                <Link href={withParams({ stops: '2' })} className="flex min-h-12 w-full items-center justify-center rounded-full border border-[#B5452B] px-5 text-center">{t.removeStop}</Link>
                <Link href={withParams({ hours: '6', preset: 'quick' })} className="link-primary flex min-h-12 w-full items-center justify-center px-5 text-center">{t.bestRoute}</Link>
              </div>
            </m.div>
          ) : (
            <>
              <h1 className="fraunces text-3xl text-[#1F1A14]">{t.routeTitle}</h1>
              {planData && <p className="mt-2 text-sm text-[#5A4E3F]" data-testid="plan-summary">{lang === 'hi' ? `${hours} घंटे में से ${hm(planData.itinerary.total_time_min)} की योजना, ${hm(planData.itinerary.total_travel_time_min)} यात्रा` : `Plans ${hm(planData.itinerary.total_time_min)} of your ${hours} hours, with ${hm(planData.itinerary.total_travel_time_min)} of travel`}</p>}
              <div className="mt-4">
                {stops.map(({ id, time, duration }, index) => {
                  const monument = findMonument(id)!
                  return (
                    <m.div animate={{ opacity: 1, x: 0 }} initial={false} key={id} transition={{ ...transitions.base, delay: index * .06 }}>
                      <div className="flex gap-4 border-l-2 border-[#B5452B] py-3 pl-4">
                        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[#B5452B] text-sm text-white">{index + 1}</span>
                        <div>
                          <Link className="font-semibold underline-offset-4 hover:underline" href={`/monument/${id}`}>{monument.name[lang]}</Link>
                          <div className="text-sm text-[#5A4E3F]">{time} · {duration} {lang === 'hi' ? 'मिनट का पड़ाव' : 'min visit'}</div>
                          <div className="mt-0.5 text-xs text-[#8F3221]">{monument.era}{monument.verified ? '' : lang === 'hi' ? ' · कहानी शीघ्र' : ' · Story pending'}</div>
                          <button
                            type="button"
                            onClick={() => setViewing3D(id)}
                            className="mt-2 inline-flex min-h-12 items-center gap-1.5 rounded-full border border-[#E8A317]/50 bg-[#EADBC0]/60 px-4 text-xs font-semibold text-[#8F3221] shadow-2xs transition-colors hover:bg-[#E8A317]/30"
                          >
                            <Box size={13} className="text-[#E8A317]" />
                            {lang === 'hi' ? '3D वास्तुकला' : '3D Architecture'}
                          </button>
                        </div>
                      </div>
                      {index < stops.length - 1 && <VineDivider />}
                    </m.div>
                  )
                })}
              </div>
              <div className="mt-5 flex gap-2">
                <button aria-pressed={started} onClick={() => setStarted((value) => !value)} className="min-h-12 flex-1 rounded-full bg-[#B5452B] px-4 text-white" type="button">{started ? t.tourStarted : t.start}</button>
                <Link href="/plan" className="flex min-h-12 flex-1 items-center justify-center rounded-full border border-[#B5452B] px-4 text-center">{t.change}</Link>
              </div>
            </>
          )}
        </div>

        {/* 3D Architecture Viewer Modal */}
        {viewing3D && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F1A14]/75 p-4 backdrop-blur-xs" onClick={() => setViewing3D(null)}>
            <div aria-labelledby="route-3d-title" aria-modal="true" className="relative max-h-full w-full max-w-lg overflow-y-auto rounded-2xl border border-[#E8A317]/50 bg-[#FBF6EC] p-4 shadow-2xl" onClick={(event) => event.stopPropagation()} role="dialog">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Box aria-hidden="true" size={18} className="text-[#B5452B]" />
                  <h3 className="fraunces text-lg text-[#1F1A14]" id="route-3d-title">
                    {getMonument(viewing3D).name[lang]}
                  </h3>
                </div>
                <button
                  onClick={() => setViewing3D(null)}
                  autoFocus
                  className="grid size-12 shrink-0 place-items-center rounded-full bg-[#EADBC0] text-[#1F1A14] transition-colors hover:bg-[#E8A317]/40"
                  type="button"
                  aria-label={lang === 'hi' ? 'बंद करें' : 'Close'}
                >
                  <X aria-hidden="true" size={16} />
                </button>
              </div>
              <Monument3DViewer monumentId={viewing3D} name={getMonument(viewing3D).name[lang]} lang={lang} />
            </div>
          </div>
        )}
      </main>
    </LazyMotion>
  )
}

export default function Page() {
  return <Suspense fallback={<main className="shell grid min-h-svh place-items-center"><div className="text-center"><KolamLoader /><p className="mt-3 text-sm text-[#5A4E3F]">Building your path…</p></div></main>}><RouteContent /></Suspense>
}
