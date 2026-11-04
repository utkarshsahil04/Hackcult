'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Box, CarFront, Footprints, Scale, X } from 'lucide-react'
import Map from '@/components/map'
import { KolamLoader, Monument3DViewer, MonumentArt } from '@/components/heritage'
import { useLang } from '@/components/raahein'
import { fetchRouteLine, planTour, type RouteLineResponse, type TourPlanResponse } from '@/lib/api'
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
  const [routeLine, setRouteLine] = useState<RouteLineResponse | null>(null)
  const [activeLeg, setActiveLeg] = useState<number | null>(null)

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

  const profile = mode === 'auto' ? 'driving-car' : 'foot-walking'
  const planStops = planData?.is_feasible ? planData.itinerary.stops.map((s) => s.monument_slug).join(',') : ''

  // The plan shows at once with straight lines. Road shapes replace them when they arrive.
  useEffect(() => {
    if (!planStops.includes(',')) return
    let live = true
    fetchRouteLine(planStops.split(','), profile).then((line) => { if (live) setRouteLine(line) })
    return () => {
      live = false
      setRouteLine(null)
      setActiveLeg(null)
    }
  }, [planStops, profile])

  const impossible = planData !== null && !planData.is_feasible
  const stops = (planData?.is_feasible ? planData.itinerary.stops : []).filter((s) => findMonument(s.monument_slug)).map((s) => {
    const start = 9 * 60 + Math.round(s.arrival_time_min)
    return { id: s.monument_slug, time: `${String(Math.floor(start / 60)).padStart(2, '0')}:${String(start % 60).padStart(2, '0')}`, duration: Math.round(s.visit_duration_min), legMin: s.travel_time_to_next_min, legM: s.travel_distance_to_next_m }
  })
  const TravelIcon = mode === 'auto' ? CarFront : Footprints
  const fewerThanAsked = maxStops !== undefined && stops.length > 0 && stops.length < maxStops
  const distance = Math.round((planData?.itinerary?.total_travel_distance_m ?? 0) / 1000)
  const withParams = (changes: Record<string, string>) => `/plan/route?${new URLSearchParams({ ...Object.fromEntries(params), ...changes })}`
  const hm = (min: number) => { const m = Math.round(min); return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h ${m % 60}m` }

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
      <main className="shell plan-layout min-h-svh bg-[#EADBC0] lg:grid lg:grid-cols-[420px_minmax(0,1fr)]" lang={lang}>
        <div className="relative h-[48svh] lg:sticky lg:top-[4.5rem] lg:col-start-2 lg:row-start-1 lg:h-[calc(100svh-4.5rem)]">
          <Map activeLeg={activeLeg} line={routeLine?.legs} route stops={stops.map((stop) => stop.id)} />
          <div className="pointer-events-none absolute left-4 right-4 top-4 z-[500] flex flex-wrap gap-2 safe-top">
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm tabular-nums shadow">{stops.length} {lang === 'hi' ? 'पड़ाव' : stops.length === 1 ? 'stop' : 'stops'}</span>
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm shadow">{hours} {t.hours}</span>
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm tabular-nums shadow">{distance} km</span>
            <span className="rounded-full bg-[#FBF6EC] px-3 py-2 text-sm shadow">{modeLabel}</span>
          </div>
          {routeLine?.source === 'straight' && <p className="pointer-events-none absolute bottom-4 left-4 z-[500] max-w-[70%] rounded-full bg-[#FBF6EC] px-3 py-2 text-xs shadow" data-testid="straight-note">{lang === 'hi' ? 'सीधी रेखाएं दिखाई गई हैं; असली रास्ता अलग हो सकता है।' : 'Showing straight lines. The real road will differ.'}</p>}
        </div>
        <div className="min-h-[52svh] rounded-t-3xl bg-[#FBF6EC] p-5 lg:col-start-1 lg:row-start-1 lg:overflow-y-auto lg:rounded-none lg:p-8">
          {impossible ? (
            <m.div animate={{ opacity: 1, y: 0 }} initial={false} transition={transitions.base}>
              <m.div animate={{ rotate: [0, 8, 0] }} className="mb-3 text-[#B5452B]" transition={transitions.base}><Scale aria-hidden="true" /></m.div>
              <h1 className="fraunces text-3xl">{t.impossible}</h1>
              <p className="my-5 rounded-2xl border border-[#E8A317]/40 bg-[#EADBC0]/50 p-4 text-[#5A4E3F]">{lang === 'hi' ? `${hours} घंटे में इन विकल्पों के साथ कोई रास्ता नहीं बन पाया।` : `No route fits ${hours} hours with these choices.`}</p>
              <div className="space-y-2">
                <Link href={withParams({ hours: '9' })} className="link-inverse flex min-h-12 w-full items-center justify-center rounded-full bg-[#B5452B] px-5 text-center">{t.addTime}</Link>
                <Link href={withParams({ stops: String(Math.max(1, (maxStops ?? 3) - 1)) })} className="flex min-h-12 w-full items-center justify-center rounded-full border border-[#B5452B] px-5 text-center">{t.removeStop}</Link>
                <Link href={withParams({ hours: '6', preset: 'quick' })} className="link-primary flex min-h-12 w-full items-center justify-center px-5 text-center">{t.bestRoute}</Link>
              </div>
            </m.div>
          ) : (
            <>
              <h1 className="fraunces text-3xl text-[#1F1A14]">{t.routeTitle}</h1>
              {planData && <p className="mt-2 text-sm text-[#5A4E3F]" data-testid="plan-summary">{lang === 'hi' ? `${hours} घंटे में से ${hm(planData.itinerary.total_time_min)} की योजना, ${hm(planData.itinerary.total_travel_time_min)} यात्रा` : `Plans ${hm(planData.itinerary.total_time_min)} of your ${hours} hours, with ${hm(planData.itinerary.total_travel_time_min)} of travel`}</p>}
              {fewerThanAsked && <p className="mt-3 rounded-2xl border border-[#E8A317]/50 bg-[#EADBC0]/50 p-3 text-sm text-[#5A4E3F]" data-testid="fewer-stops">{lang === 'hi' ? `आपके समय और गति में ${maxStops} में से ${stops.length} पड़ाव आ पाए।` : `${stops.length} of your ${maxStops} stops fit this time and pace.`} {hours < 10 && <Link className="link-primary font-semibold underline underline-offset-2" href={withParams({ hours: String(Math.min(10, hours + 2)) })}>{lang === 'hi' ? '2 घंटे और जोड़ें' : 'Add 2 hours'}</Link>}</p>}
              <ol className="mt-5" data-testid="route-timeline">
                {stops.map(({ id, time, duration, legMin, legM }, index) => {
                  const monument = findMonument(id)!
                  const hasLeg = index < stops.length - 1
                  const isActive = activeLeg === index
                  return (
                    <li key={id}>
                      <div className="flex gap-3">
                        <div className="flex w-9 shrink-0 flex-col items-center">
                          <span aria-hidden="true" className="grid size-9 place-items-center rounded-full bg-[#B5452B] text-sm font-semibold text-white">{index + 1}</span>
                          {hasLeg && <span aria-hidden="true" className="w-0.5 flex-1 bg-[#B5452B]/30" />}
                        </div>
                        <div className="min-w-0 flex-1 pb-3">
                          <div className="flex gap-3">
                            <div className="min-w-0 flex-1">
                              <Link className="fraunces text-lg leading-snug underline-offset-4 hover:underline" href={`/monument/${id}`}>{monument.name[lang]}</Link>
                              <p className="text-sm tabular-nums text-[#5A4E3F]">{time} · {duration} {lang === 'hi' ? 'मिनट का पड़ाव' : 'min visit'}</p>
                              {!monument.verified && <p className="text-xs text-[#8F3221]">{lang === 'hi' ? 'कहानी शीघ्र' : 'Story pending'}</p>}
                            </div>
                            <MonumentArt alt="" className="size-16 shrink-0 rounded-xl" id={id} />
                          </div>
                          <button className="-ml-3 inline-flex min-h-12 items-center gap-1.5 rounded-full px-3 text-xs font-semibold text-[#8F3221] transition-colors hover:bg-[#EADBC0]/70" onClick={() => setViewing3D(id)} type="button"><Box aria-hidden="true" size={13} />{lang === 'hi' ? '3D वास्तुकला' : '3D Architecture'}</button>
                        </div>
                      </div>
                      {hasLeg && (
                        <div className="flex gap-3">
                          <div className="flex w-9 shrink-0 justify-center"><span aria-hidden="true" className="w-0.5 bg-[#B5452B]/30" /></div>
                          <button aria-pressed={isActive} className={`mb-3 inline-flex min-h-12 items-center gap-2 rounded-full border px-3 text-sm tabular-nums transition-colors ${isActive ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#D4C3A6] text-[#5A4E3F] hover:border-[#B5452B]'}`} onClick={() => setActiveLeg(isActive ? null : index)} type="button">
                            <TravelIcon aria-hidden="true" size={15} />
                            {Math.max(1, Math.round(legMin ?? 0))} {lang === 'hi' ? 'मिनट' : 'min'} · {((legM ?? 0) / 1000).toFixed(1)} km
                          </button>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ol>
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
