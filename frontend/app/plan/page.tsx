'use client'

import { useState } from 'react'
import Link from 'next/link'
import { CarFront, Check, Footprints, TrainFront } from 'lucide-react'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import Map from '@/components/map'
import { Toggle, useLang } from '@/components/raahein'
import { springs, transitions } from '@/lib/motion'

const interests = [
  { id: 'mughal', en: 'Mughal', hi: 'मुगल' },
  { id: 'rajput', en: 'Rajput', hi: 'राजपूत' },
  { id: 'architecture', en: 'Architecture', hi: 'वास्तुकला' },
  { id: 'stories', en: 'Stories and legends', hi: 'कहानियां और किंवदंतियां' },
  { id: 'gardens', en: 'Gardens', hi: 'बगीचे' },
] as const

export default function Page() {
  const { lang, setLang, t } = useLang()
  const [hours, setHours] = useState(6)
  const [selected, setSelected] = useState<string[]>([])
  const [mode, setMode] = useState('walk')
  const modes = [
    { id: 'walk', label: t.walk, icon: Footprints },
    { id: 'auto', label: t.auto, icon: CarFront },
    { id: 'metro', label: t.metro, icon: TrainFront },
  ]
  const routeHref = { pathname: '/plan/route', query: { hours, mode, interests: selected.join(',') } }

  return (
    <LazyMotion features={domAnimation}>
      <main className="shell pb-24 lg:grid lg:max-w-none lg:grid-cols-[420px_minmax(0,1fr)] lg:gap-0 lg:px-0 lg:pb-0" lang={lang}>
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-[#E8A317]/20 bg-[#EADBC0]/95 px-5 py-2.5 backdrop-blur lg:hidden safe-top">
          <h1 className="font-[var(--font-fraunces)] text-4xl">{t.plan}</h1>
          <Toggle lang={lang} setLang={setLang} />
        </header>
        <div className="space-y-8 px-5 pt-8 lg:col-start-1 lg:row-start-1 lg:max-h-[calc(100svh-4.5rem)] lg:overflow-y-auto lg:pb-12 lg:pt-10">
          <h1 className="hidden font-[var(--font-fraunces)] text-4xl lg:block">{t.plan}</h1>
          <section>
            <div className="mb-5 flex items-end justify-between gap-3">
              <label className="font-semibold" htmlFor="available-hours">{t.timeAvailable}</label>
              <m.output animate={{ opacity: 1, y: 0 }} className="font-[var(--font-fraunces)] text-2xl text-[#B5452B]" htmlFor="available-hours" initial={false} key={hours} transition={transitions.fast}>{hours} {t.hours}</m.output>
            </div>
            <input id="available-hours" type="range" min="2" max="10" value={hours} onChange={(event) => setHours(Number(event.target.value))} className="min-h-12 w-full accent-[#B5452B]" />
            <div className="mt-1 flex justify-between text-xs text-[#5A4E3F]"><span>{t.twoHours}</span><span>{t.tenHours}</span></div>
          </section>
          <section>
            <h2 className="mb-3 font-semibold">{t.interests}</h2>
            <div className="flex flex-wrap gap-2">
              {interests.map((item) => {
                const on = selected.includes(item.id)
                return <m.button animate={{ scale: on ? 1.03 : 1 }} aria-pressed={on} className={`min-h-12 rounded-full border px-3 py-2 text-sm ${on ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#C8B594] bg-[#FBF6EC]'}`} key={item.id} onClick={() => setSelected((current) => on ? current.filter((value) => value !== item.id) : [...current, item.id])} transition={springs.snappy} type="button">{on && <Check aria-hidden="true" className="mr-1 inline" size={14} />}{item[lang]}</m.button>
              })}
            </div>
          </section>
          <section>
            <h2 className="mb-3 font-semibold">{t.travelMode}</h2>
            <div className="flex gap-2">
              {modes.map(({ id, label, icon: Icon }) => <m.button animate={{ y: mode === id ? -3 : 0 }} aria-pressed={mode === id} className={`card flex min-h-20 flex-1 flex-col items-center justify-center gap-1 border ${mode === id ? 'border-[#B5452B] bg-[#F3E5CF] text-[#B5452B]' : 'border-[#D4C3A6]'}`} key={id} onClick={() => setMode(id)} transition={springs.snappy} type="button"><Icon aria-hidden="true" size={21} /><span className="text-xs">{label}</span></m.button>)}
            </div>
          </section>
          <p className="border-t border-[#D4C3A6] pt-5 text-[#5A4E3F]">{t.about} <strong className="text-[#1F1A14]">{hours} {t.hours}</strong></p>
          <Link href={routeHref} className="link-inverse flex min-h-14 items-center justify-center rounded-full bg-[#B5452B] px-6 text-center font-semibold shadow-[0_10px_24px_rgba(143,50,33,.28)]">{t.build}</Link>
        </div>
        <div className="hidden lg:sticky lg:top-0 lg:col-start-2 lg:row-start-1 lg:block lg:h-[calc(100svh-4.5rem)]"><Map /></div>
      </main>
    </LazyMotion>
  )
}
