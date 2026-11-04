'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowRight, CarFront, Check, Footprints, Search, X } from 'lucide-react'
import Map from '@/components/map'
import { Toggle, useLang } from '@/components/raahein'
import { monuments } from '@/lib/catalog'
import { MAX_STOPS, regionOf, useTour } from '@/lib/journey'

const interests = [
  { id: 'mughal', en: 'Mughal', hi: 'मुगल' },
  { id: 'architecture', en: 'Architecture', hi: 'वास्तुकला' },
  { id: 'legend', en: 'Stories and legends', hi: 'कहानियां और किंवदंतियां' },
  { id: 'garden', en: 'Gardens', hi: 'बगीचे' },
] as const

const paces = [
  { id: 'relaxed', en: 'Relaxed', hi: 'आराम से', noteEn: 'Longer visits, short trips', noteHi: 'लंबे पड़ाव, छोटी यात्रा', stops: 3 },
  { id: 'standard', en: 'Standard', hi: 'सामान्य', noteEn: 'A balanced day', noteHi: 'संतुलित दिन', stops: 4 },
  { id: 'quick', en: 'Quick', hi: 'तेज़', noteEn: 'Shorter visits, more places', noteHi: 'छोटे पड़ाव, ज़्यादा स्थान', stops: 5 },
] as const

const cities = [{ id: 'Delhi', en: 'Delhi', hi: 'दिल्ली' }, { id: 'Agra', en: 'Agra', hi: 'आगरा' }] as const
const STOP_CHOICES = Array.from({ length: MAX_STOPS }, (_, index) => index + 1)

const copy = {
  en: { city: 'City', stops: 'Stops in your day', stopsHint: (n: number) => `Up to ${n}. We only plan what fits your time.`, pace: 'Pace of the day', must: 'Places you must see', mustHint: (left: number) => left ? `Optional. Choose up to ${left} more, or let us choose.` : 'All your stops are chosen.', search: 'Search monuments', noMatch: 'No monuments match that search.', remove: 'Remove', summary: (n: number, h: number, c: string) => `Up to ${n} ${n === 1 ? 'stop' : 'stops'} in ${c}, in ${h} hours`, chooseOnMap: 'Tap a monument on the map to add it.' },
  hi: { city: 'शहर', stops: 'दिन के पड़ाव', stopsHint: (n: number) => `अधिकतम ${n}। हम उतना ही बनाते हैं जितना आपके समय में हो सके।`, pace: 'दिन की गति', must: 'जो स्थान ज़रूर देखने हैं', mustHint: (left: number) => left ? `वैकल्पिक। ${left} और चुनें, या हम पर छोड़ दें।` : 'आपके सभी पड़ाव चुन लिए गए।', search: 'स्मारक खोजें', noMatch: 'इस खोज से कोई स्मारक नहीं मिला।', remove: 'हटाएं', summary: (n: number, h: number, c: string) => `${c} में ${h} घंटे में अधिकतम ${n} पड़ाव`, chooseOnMap: 'जोड़ने के लिए मानचित्र पर स्मारक चुनें।' },
}

const chip = (on: boolean) => `min-h-12 rounded-full border px-4 py-2 text-sm transition-colors ${on ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#C8B594] bg-[#FBF6EC] hover:border-[#B5452B]'}`

export default function Page() {
  const { lang, setLang, t } = useLang()
  const text = copy[lang]
  const tour = useTour()
  const [hours, setHours] = useState(8)
  const [selected, setSelected] = useState<string[]>([])
  const [mode, setMode] = useState('auto')
  const [preset, setPreset] = useState('standard')
  const [stops, setStops] = useState(4)
  const [city, setCity] = useState('Delhi')
  const [query, setQuery] = useState('')
  // Null means the visitor hasn't changed anything, so their saved tour is the starting point.
  const [chosen, setChosen] = useState<string[] | null>(null)
  const inCity = monuments.filter((m) => regionOf(m) === city)
  const must = (chosen ?? tour).filter((id) => inCity.some((m) => m.id === id)).slice(0, stops)
  const matches = inCity.filter((m) => !must.includes(m.id) && m.name[lang].toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))
  const left = stops - must.length
  const cityName = cities.find((item) => item.id === city)![lang]
  const modes = [{ id: 'walk', label: t.walk, icon: Footprints }, { id: 'auto', label: t.auto, icon: CarFront }]
  const routeHref = { pathname: '/plan/route', query: { hours, mode, preset, city, stops, must: must.join(','), interests: selected.join(',') } }

  const toggleMust = (id: string) => {
    if (must.includes(id)) setChosen(must.filter((item) => item !== id))
    else if (must.length < stops) setChosen([...must, id])
  }

  function choosePace(item: (typeof paces)[number]) {
    setPreset(item.id)
    setStops(Math.max(item.stops, must.length))
  }

  return (
    <main className="shell plan-layout pb-24 lg:grid lg:grid-cols-[460px_minmax(0,1fr)] lg:gap-0 lg:pb-0" lang={lang}>
      <header className="site-header sticky top-0 z-40 flex items-center justify-between border-b border-[#E8A317]/20 bg-[#EADBC0]/95 px-5 py-2.5 backdrop-blur lg:hidden safe-top">
        <h1 className="fraunces text-3xl">{t.plan}</h1>
        <Toggle lang={lang} setLang={setLang} />
      </header>

      <div className="space-y-7 px-5 pt-8 lg:col-start-1 lg:row-start-1 lg:max-h-[calc(100svh-4.5rem)] lg:overflow-y-auto lg:pb-6 lg:pt-8">
        <h1 className="fraunces hidden text-4xl lg:block">{t.plan}</h1>

        <section>
          <div className="mb-3 flex items-end justify-between gap-3">
            <label className="font-semibold" htmlFor="available-hours">{t.timeAvailable}</label>
            <output className="fraunces text-2xl tabular-nums text-[#B5452B]" htmlFor="available-hours">{hours} {t.hours}</output>
          </div>
          <input className="min-h-12 w-full accent-[#B5452B]" id="available-hours" max="10" min="2" onChange={(event) => setHours(Number(event.target.value))} type="range" value={hours} />
          <div className="flex justify-between text-xs text-[#5A4E3F]"><span>{t.twoHours}</span><span>{t.tenHours}</span></div>
        </section>

        <section>
          <h2 className="mb-3 font-semibold">{text.city}</h2>
          <div className="flex flex-wrap gap-2">
            {cities.map((item) => <button aria-pressed={city === item.id} className={chip(city === item.id)} key={item.id} onClick={() => { setCity(item.id); setChosen([]) }} type="button">{item[lang]}</button>)}
          </div>
        </section>

        <section>
          <h2 className="font-semibold" id="stops-label">{text.stops}</h2>
          <p className="mb-3 mt-0.5 text-sm text-[#5A4E3F]">{text.stopsHint(MAX_STOPS)}</p>
          <div aria-labelledby="stops-label" className="grid grid-cols-5 gap-1 rounded-full border border-[#C8B594] bg-[#FBF6EC] p-1" role="group">
            {STOP_CHOICES.map((n) => (
              <button aria-pressed={stops === n} className={`min-h-12 rounded-full text-base font-semibold tabular-nums transition-colors ${stops === n ? 'bg-[#B5452B] text-white' : 'hover:bg-[#EADBC0] disabled:opacity-40 disabled:hover:bg-transparent'}`} disabled={n < must.length} key={n} onClick={() => setStops(n)} type="button">{n}</button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-3 font-semibold">{text.pace}</h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {paces.map((item) => (
              <button aria-pressed={preset === item.id} className={`min-h-12 rounded-2xl border px-3 py-2 text-left transition-colors ${preset === item.id ? 'border-[#B5452B] bg-[#F3E5CF]' : 'border-[#C8B594] bg-[#FBF6EC] hover:border-[#B5452B]'}`} key={item.id} onClick={() => choosePace(item)} type="button">
                <span className={`block text-sm font-semibold ${preset === item.id ? 'text-[#8F3221]' : ''}`}>{item[lang]}</span>
                <span className="block text-xs leading-snug text-[#5A4E3F]">{lang === 'hi' ? item.noteHi : item.noteEn}</span>
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="font-semibold">{text.must}</h2>
          <p className="mb-3 mt-0.5 text-sm text-[#5A4E3F]">{text.mustHint(left)}</p>
          {must.length > 0 && (
            <ol className="mb-3 flex flex-wrap gap-2" data-testid="must-see">
              {must.map((id, index) => {
                const monument = inCity.find((m) => m.id === id)!
                return (
                  <li key={id}>
                    <button aria-label={`${text.remove} ${monument.name[lang]}`} className="inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] py-1 pl-1.5 pr-3 text-sm text-white transition-colors hover:bg-[#8F3221]" onClick={() => toggleMust(id)} type="button">
                      <span aria-hidden="true" className="grid size-7 place-items-center rounded-full bg-[#FBF6EC] text-xs font-bold text-[#8F3221]">{index + 1}</span>
                      {monument.name[lang]}
                      <X aria-hidden="true" size={14} />
                    </button>
                  </li>
                )
              })}
            </ol>
          )}
          {left > 0 && (
            <>
              <div className="card flex items-center gap-2 px-3">
                <Search aria-hidden="true" size={16} />
                <label className="sr-only" htmlFor="must-search">{text.search}</label>
                <input className="min-h-12 w-full bg-transparent outline-none placeholder:text-[#61402F]" id="must-search" onChange={(event) => setQuery(event.target.value)} placeholder={text.search} value={query} />
              </div>
              <ul className="mt-2 max-h-52 overflow-y-auto rounded-2xl border border-[#D4C3A6] bg-[#FBF6EC]">
                {matches.map((monument) => (
                  <li className="border-b border-[#EADBC0] last:border-0" key={monument.id}>
                    <button className="flex min-h-12 w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm transition-colors hover:bg-[#EADBC0]/60" onClick={() => toggleMust(monument.id)} type="button">
                      {monument.name[lang]}<Check aria-hidden="true" className="shrink-0 text-[#C8B594]" size={15} />
                    </button>
                  </li>
                ))}
                {matches.length === 0 && <li className="px-4 py-3 text-sm text-[#5A4E3F]" role="status">{text.noMatch}</li>}
              </ul>
            </>
          )}
        </section>

        <section>
          <h2 className="mb-3 font-semibold">{t.interests}</h2>
          <div className="flex flex-wrap gap-2">
            {interests.map((item) => {
              const on = selected.includes(item.id)
              return <button aria-pressed={on} className={chip(on)} key={item.id} onClick={() => setSelected((current) => on ? current.filter((value) => value !== item.id) : [...current, item.id])} type="button">{on && <Check aria-hidden="true" className="mr-1 inline" size={14} />}{item[lang]}</button>
            })}
          </div>
        </section>

        <section>
          <h2 className="mb-3 font-semibold">{t.travelMode}</h2>
          <div className="flex gap-2">
            {modes.map(({ id, label, icon: Icon }) => <button aria-pressed={mode === id} className={`card flex min-h-20 flex-1 flex-col items-center justify-center gap-1 border transition-colors ${mode === id ? 'border-[#B5452B] bg-[#F3E5CF] text-[#B5452B]' : 'border-[#D4C3A6]'}`} key={id} onClick={() => setMode(id)} type="button"><Icon aria-hidden="true" size={21} /><span className="text-xs">{label}</span></button>)}
          </div>
        </section>

        <div className="sticky bottom-20 z-10 -mx-5 border-t border-[#D4C3A6] bg-[#EADBC0]/95 px-5 py-2 backdrop-blur lg:bottom-0 lg:py-3">
          <p className="mb-1.5 text-center text-sm text-[#5A4E3F]" data-testid="plan-brief">{text.summary(stops, hours, cityName)}</p>
          <Link className="link-inverse primary-action flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#B5452B] px-6 text-center font-semibold shadow-[0_10px_24px_rgba(143,50,33,.28)] lg:min-h-14" href={routeHref}>{t.build}<ArrowRight aria-hidden="true" size={18} /></Link>
        </div>
      </div>

      <div className="relative hidden lg:sticky lg:top-[4.5rem] lg:col-start-2 lg:row-start-1 lg:block lg:h-[calc(100svh-4.5rem)]">
        <Map background={inCity.map((m) => m.id)} onPick={toggleMust} stops={must} />
        <p className="pointer-events-none absolute left-1/2 top-5 z-[500] -translate-x-1/2 rounded-full bg-[#FBF6EC]/95 px-4 py-2 text-sm shadow">{text.chooseOnMap}</p>
      </div>
    </main>
  )
}
