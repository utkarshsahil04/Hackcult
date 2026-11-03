'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Scale } from 'lucide-react'
import Map from '@/components/map'
import { KolamLoader, VineDivider } from '@/components/heritage'
import { useLang } from '@/components/raahein'
import { planTour, type TourPlanResponse } from '@/lib/api'
import { getMonument } from '@/lib/mock'
import { transitions } from '@/lib/motion'

const routeStops = [
  { id: 'taj-mahal', time: '09:00', duration: 60 },
  { id: 'agra-fort', time: '11:15', duration: 75 },
  { id: 'fatehpur-sikri', time: '14:00', duration: 90 },
] as const

function RouteContent() {
  const { lang, t } = useLang()
  const params = useSearchParams()
  const requestedHours = Number(params.get('hours')) || 6
  const hours = Math.min(10, Math.max(2, requestedHours))
  const forcedStops = Number(params.get('stops'))
  const defaultStopCount = forcedStops ? Math.min(routeStops.length, Math.max(1, forcedStops)) : hours < 4 ? 1 : hours < 6 ? 2 : 3
  const defaultStops = routeStops.slice(0, defaultStopCount)
  const defaultDistance = defaultStopCount === 1 ? 2 : defaultStopCount === 2 ? 5 : 42
  const mode = params.get('mode')
  const modeLabel = mode === 'metro' ? t.metro : mode === 'auto' ? t.auto : t.walk
  const [planData, setPlanData] = useState<TourPlanResponse | null>(null)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const profile = mode === 'auto' ? 'driving-car' : 'foot-walking'
    planTour({
      start_monument: 'taj-mahal',
      time_budget_minutes: hours * 60,
      profile,
    }).then(setPlanData).catch(() => {})
  }, [hours, mode])

  const impossible = params.get('mock') === 'impossible' || (planData !== null && !planData.is_feasible)
  const stops = (planData?.is_feasible && planData.itinerary?.stops?.length)
    ? planData.itinerary.stops.map((s) => ({
        id: s.monument_slug,
        time: `${String(Math.floor(s.arrival_time_min / 60) + 9).padStart(2, '0')}:${String(s.arrival_time_min % 60).padStart(2, '0')}`,
        duration: s.visit_duration_min,
      }))
    : defaultStops
  const distance = planData?.itinerary?.total_travel_distance_m
    ? Math.round(planData.itinerary.total_travel_distance_m / 1000)
    : defaultDistance

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
              <h1 className="font-[var(--font-fraunces)] text-3xl">{t.impossible}</h1>
              <p className="my-5 rounded-2xl border border-[#E8A317]/40 bg-[#EADBC0]/50 p-4 text-[#5A4E3F]">{t.impossibleBody}</p>
              <div className="space-y-2">
                <Link href="/plan/route?hours=9" className="link-inverse flex min-h-12 w-full items-center justify-center rounded-full bg-[#B5452B] px-5 text-center">{t.addTime}</Link>
                <Link href="/plan/route?hours=6&stops=2" className="flex min-h-12 w-full items-center justify-center rounded-full border border-[#B5452B] px-5 text-center">{t.removeStop}</Link>
                <Link href="/plan/route?hours=6&best=1" className="link-primary flex min-h-12 w-full items-center justify-center px-5 text-center">{t.bestRoute}</Link>
              </div>
            </m.div>
          ) : (
            <>
              <h1 className="font-[var(--font-fraunces)] text-3xl text-[#1F1A14]">{t.routeTitle}</h1>
              <div className="mt-4">
                {stops.map(({ id, time, duration }, index) => {
                  const monument = getMonument(id)
                  return (
                    <m.div animate={{ opacity: 1, x: 0 }} initial={false} key={id} transition={{ ...transitions.base, delay: index * .06 }}>
                      <div className="flex gap-4 border-l-2 border-[#B5452B] py-3 pl-4">
                        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[#B5452B] text-sm text-white">{index + 1}</span>
                        <div><div className="font-semibold">{monument.name[lang]}</div><div className="text-sm text-[#5A4E3F]">{time} · {duration} min</div></div>
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
      </main>
    </LazyMotion>
  )
}

export default function Page() {
  return <Suspense fallback={<main className="shell grid min-h-svh place-items-center"><div className="text-center"><KolamLoader /><p className="mt-3 text-sm text-[#5A4E3F]">Building your path…</p></div></main>}><RouteContent /></Suspense>
}
