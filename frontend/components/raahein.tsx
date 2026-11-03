'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { CalendarDays, Compass, Map, ScanLine, Search } from 'lucide-react'
import { motion } from 'framer-motion'
import { MonumentArt } from '@/components/heritage'
import { strings } from '@/lib/i18n/strings'
import { monuments, type Lang } from '@/lib/mock'
import { transitions } from '@/lib/motion'

const LANGUAGE_KEY = 'raahein-language'
const LANGUAGE_EVENT = 'raahein-language'

function isLang(value: unknown): value is Lang {
  return value === 'en' || value === 'hi'
}

function applyDocumentLanguage(lang: Lang) {
  document.documentElement.lang = lang
}

export function useLang() {
  const [lang, setLangState] = useState<Lang>('en')

  useEffect(() => {
    const onLanguage = (event: Event) => {
      const next = (event as CustomEvent<Lang>).detail
      if (!isLang(next)) return
      applyDocumentLanguage(next)
      setLangState(next)
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key === LANGUAGE_KEY && isLang(event.newValue)) {
        window.dispatchEvent(new CustomEvent<Lang>(LANGUAGE_EVENT, { detail: event.newValue }))
      }
    }
    window.addEventListener(LANGUAGE_EVENT, onLanguage)
    window.addEventListener('storage', onStorage)
    let stored: string | null = null
    try {
      stored = localStorage.getItem(LANGUAGE_KEY)
    } catch {
      stored = null
    }
    const initial = isLang(stored) ? stored : 'en'
    queueMicrotask(() => window.dispatchEvent(new CustomEvent<Lang>(LANGUAGE_EVENT, { detail: initial })))
    return () => {
      window.removeEventListener(LANGUAGE_EVENT, onLanguage)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  const setLang = useCallback((next: Lang) => {
    try {
      localStorage.setItem(LANGUAGE_KEY, next)
    } catch {
      // Language still changes for this session when storage is unavailable.
    }
    applyDocumentLanguage(next)
    window.dispatchEvent(new CustomEvent<Lang>(LANGUAGE_EVENT, { detail: next }))
  }, [])

  return { lang, setLang, t: strings[lang] }
}

export function Toggle({ lang, setLang }: { lang: Lang; setLang: (next: Lang) => void }) {
  const next = lang === 'en' ? 'hi' : 'en'
  return (
    <button
      aria-label={next === 'hi' ? 'Switch to Hindi' : 'Switch to English'}
      className="lang-toggle min-h-12 rounded-full px-3 text-sm font-medium"
      onClick={() => setLang(next)}
      type="button"
    >
      <span className={lang === 'en' ? 'font-bold text-[#B5452B]' : ''} lang="en">EN</span>
      <span aria-hidden="true" className="mx-1 text-[#B5452B]">|</span>
      <span className={lang === 'hi' ? 'font-bold text-[#B5452B]' : ''} lang="hi">हिं</span>
    </button>
  )
}

const tabs = [
  { id: 'scan', href: '/identify', icon: ScanLine },
  { id: 'explore', href: '/explore', icon: Compass },
  { id: 'plan', href: '/plan', icon: CalendarDays },
] as const

export function Tabs({ active }: { active: 'scan' | 'explore' | 'plan' }) {
  const { lang, t } = useLang()
  const labels = { scan: t.scan, explore: t.explore, plan: t.plan }
  return (
    <nav
      aria-label={lang === 'hi' ? 'मुख्य नेविगेशन' : 'Primary navigation'}
      className="fixed bottom-0 left-1/2 z-50 flex w-full max-w-[430px] -translate-x-1/2 justify-around border-t border-[#D4C3A6] bg-[#FBF6EC] px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] lg:hidden"
    >
      {tabs.map(({ id, href, icon: Icon }) => {
        const current = active === id
        return (
          <Link
            aria-current={current ? 'page' : undefined}
            className={`flex min-h-12 min-w-20 flex-col items-center justify-center gap-1 rounded-xl text-xs ${current ? 'link-primary' : 'text-[#5A4E3F]'}`}
            href={href}
            key={id}
          >
            <Icon aria-hidden="true" size={20} />
            {labels[id]}
          </Link>
        )
      })}
    </nav>
  )
}

function Header({ lang, setLang }: { lang: Lang; setLang: (next: Lang) => void }) {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between border-b border-[#E8A317]/20 bg-[#EADBC0]/95 px-5 py-2.5 backdrop-blur lg:hidden safe-top">
      <Link className="fraunces flex min-h-12 items-center text-2xl" href="/">Raahein</Link>
      <Toggle lang={lang} setLang={setLang} />
    </header>
  )
}

const cityOptions = ['All', 'Delhi', 'Agra'] as const
const eraOptions = ['All', 'Sultanate', 'Mughal'] as const

export function Explore() {
  const { lang, setLang, t } = useLang()
  const [query, setQuery] = useState('')
  const [city, setCity] = useState<(typeof cityOptions)[number]>('All')
  const [era, setEra] = useState<(typeof eraOptions)[number]>('All')
  const [legendsOnly, setLegendsOnly] = useState(false)
  const copy = lang === 'hi'
    ? { search: 'खोज', city: 'शहर', era: 'काल', refine: 'स्मारक छांटें', legendOnly: 'केवल किंवदंती वाली कहानियां', empty: 'इन विकल्पों से कोई स्मारक नहीं मिला।', sultanate: 'सल्तनत', mughal: 'मुगल' }
    : { search: 'Search', city: 'City', era: 'Era', refine: 'Refine monuments', legendOnly: 'Legend stories only', empty: 'No monuments match these filters.', sultanate: 'Sultanate', mughal: 'Mughal' }
  const cityLabel = (value: (typeof cityOptions)[number]) => value === 'All' ? t.all : value === 'Delhi' ? t.delhi : t.agra
  const eraLabel = (value: (typeof eraOptions)[number]) => value === 'All' ? t.all : value === 'Sultanate' ? copy.sultanate : copy.mughal
  const data = monuments.filter((monument) => {
    const monumentEra = monument.id === 'qutub-minar' ? 'Sultanate' : 'Mughal'
    return (city === 'All' || monument.city === city)
      && (era === 'All' || monumentEra === era)
      && (!legendsOnly || monument.sections.some((section) => section.isLegend))
      && monument.name[lang].toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
  })

  const filters = (id: string) => (
    <>
      <div>
        <label className="text-sm font-semibold" htmlFor={`monument-search-${id}`}>{copy.search}</label>
        <div className="card mt-2 flex items-center gap-2 px-3">
          <Search aria-hidden="true" size={16} />
          <input id={`monument-search-${id}`} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t.search} className="min-h-12 w-full bg-transparent py-3 outline-none placeholder:text-[#61402F]" />
        </div>
      </div>
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">{copy.city}</legend>
        <div className="flex flex-wrap gap-2">
          {cityOptions.map((value) => (
            <button aria-pressed={city === value} className={`min-h-12 rounded-full border px-4 text-sm ${city === value ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#C8B594] bg-[#FBF6EC]'}`} key={value} onClick={() => setCity(value)} type="button">
              {cityLabel(value)}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">{copy.era}</legend>
        <div className="flex flex-wrap gap-2">
          {eraOptions.map((value) => (
            <button aria-pressed={era === value} className={`min-h-12 rounded-full border px-4 text-sm ${era === value ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#C8B594] bg-[#FBF6EC]'}`} key={value} onClick={() => setEra(value)} type="button">
              {eraLabel(value)}
            </button>
          ))}
        </div>
      </fieldset>
      <label className="flex min-h-12 items-center gap-3 text-sm">
        <input checked={legendsOnly} className="size-5 accent-[#B5452B]" onChange={(event) => setLegendsOnly(event.target.checked)} type="checkbox" />
        {copy.legendOnly}
      </label>
    </>
  )

  return (
    <main className="shell pb-24 lg:max-w-7xl lg:px-8 lg:pb-12">
      <Header lang={lang} setLang={setLang} />
      <div className="px-5 lg:grid lg:grid-cols-[260px_minmax(0,1fr)] lg:gap-10 lg:px-0 lg:pt-10">
        <aside className="hidden lg:sticky lg:top-24 lg:block lg:h-fit">
          <div className="card space-y-5 p-5">
            <h2 className="fraunces text-2xl">{copy.refine}</h2>
            {filters('desktop')}
          </div>
        </aside>
        <div>
          <div className="flex items-center justify-between">
            <h1 className="fraunces mb-4 text-4xl">{t.explore}</h1>
            <Link href="/nearby" className="grid size-12 place-items-center rounded-full border border-[#C8B594]" aria-label={t.map}>
              <Map aria-hidden="true" size={18} />
            </Link>
          </div>
          <div className="card space-y-4 p-4 lg:hidden">{filters('mobile')}</div>
          {data.length ? (
            <motion.div layout className="mt-5 grid grid-cols-2 items-stretch gap-3 lg:mt-0 lg:grid-cols-3 xl:grid-cols-4">
              {data.map((monument) => (
                <motion.div className="h-full" key={monument.id} layout transition={transitions.fast} whileHover={{ y: -3 }}>
                  <Link href={`/monument/${monument.id}`} className="card flex h-full min-h-48 flex-col overflow-hidden focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]">
                    <MonumentArt alt={monument.name[lang]} className="h-36 w-full" id={monument.id} />
                    <div className="flex flex-1 flex-col p-3">
                      <div className="flex items-center justify-between text-xs text-[#5A4E3F]">
                        <span className="font-semibold text-[#8F3221]">{monument.city}</span>
                        <span>{monument.yearBuilt} CE</span>
                      </div>
                      <div className="mt-1 font-semibold text-[#1F1A14]">{monument.name[lang]}</div>
                      <div className="mt-0.5 text-xs text-[#5A4E3F] line-clamp-1">{monument.builder}</div>
                      <div className="mt-2 line-clamp-2 text-xs leading-5 text-[#5A4E3F]">{monument.sections[0]?.text[lang]}</div>
                      <div className="mt-auto flex items-center justify-between pt-3 text-[11px] text-[#5A4E3F]">
                        <span className="font-medium text-[#765500]">{monument.sources.length} {lang === 'hi' ? 'स्रोत' : 'sources'}</span>
                        {monument.sections.some((section) => section.isLegend) && (
                          <span className="inline-block rounded-full border border-[#E8A317] px-2 py-0.5 text-[10px] text-[#765500]">{t.legend}</span>
                        )}
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </motion.div>
          ) : (
            <div className="card mt-5 p-8 text-center text-[#5A4E3F]" role="status">{copy.empty}</div>
          )}
        </div>
      </div>
    </main>
  )
}
