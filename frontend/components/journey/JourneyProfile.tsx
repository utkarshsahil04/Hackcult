'use client'

import Link from 'next/link'
import { ArrowRight, Compass, Footprints, Landmark, MapPinned, Route, Trash2, X } from 'lucide-react'
import Map from '@/components/map'
import { InlayFrame, LotusDivider, MonumentArt } from '@/components/heritage'
import { useLang } from '@/components/raahein'
import { getMonument, monuments } from '@/lib/catalog'
import { clearJourney, journeyStats, setJourneyName, setVisitDate, toggleTour, toggleVisit, tourPlanHref, today, useJourney, useTour } from '@/lib/journey'

const copy = {
  en: {
    title: 'My journey', name: 'Your name', device: 'Saved only on this device, with no account. Clearing your browser data removes it.',
    places: 'Monuments', of: 'of', cities: 'Cities', km: 'km between them', eras: 'Eras', map: 'Your path so far', visits: 'Where you have been', visited: 'Visited on', remove: 'Remove',
    emptyTitle: 'Your road starts here', empty: 'Open any monument and choose “I’ve been here”. Your path, places and distance will appear on this page.', browse: 'Browse monuments',
    next: 'Closest to your last stop', tour: 'Your tour', tourEmpty: 'Add monuments to your tour from their pages, then build a day around them.', planIt: 'Plan these stops', tourLimit: 'A day plan holds up to 3 stops, so the first 3 will be used.',
    clear: 'Clear my journey', confirm: 'Remove your name and all your visits from this device? This can’t be undone.',
  },
  hi: {
    title: 'मेरी यात्रा', name: 'आपका नाम', device: 'बिना खाते के, केवल इसी उपकरण पर सहेजा गया। ब्राउज़र डेटा हटाने पर यह भी हट जाएगा।',
    places: 'स्मारक', of: 'में से', cities: 'शहर', km: 'किमी की दूरी', eras: 'काल', map: 'अब तक की राह', visits: 'जहां आप गए', visited: 'जाने की तिथि', remove: 'हटाएं',
    emptyTitle: 'आपकी राह यहीं से शुरू होती है', empty: 'कोई भी स्मारक खोलें और “मैं यहां गया/गई हूं” चुनें। आपकी राह, स्थान और दूरी इस पृष्ठ पर दिखेंगे।', browse: 'स्मारक देखें',
    next: 'आपके पिछले पड़ाव के सबसे पास', tour: 'आपका टूर', tourEmpty: 'स्मारकों के पृष्ठों से उन्हें अपने टूर में जोड़ें, फिर उनके साथ अपना दिन बनाएं।', planIt: 'इन पड़ावों की योजना बनाएं', tourLimit: 'एक दिन की योजना में अधिकतम 3 पड़ाव होते हैं, इसलिए पहले 3 लिए जाएंगे।',
    clear: 'मेरी यात्रा मिटाएं', confirm: 'क्या इस उपकरण से आपका नाम और सभी यात्राएं हटा दें? इसे वापस नहीं लाया जा सकता।',
  },
}

export function JourneyProfile() {
  const { lang } = useLang()
  const journey = useJourney()
  const tour = useTour()
  const text = copy[lang]
  const stats = journeyStats(journey.visits)
  const initial = (journey.name.trim()[0] ?? (lang === 'hi' ? 'य' : 'Y')).toLocaleUpperCase()
  const statCards = [
    { icon: Landmark, value: `${stats.places}`, label: `${text.places} (${text.of} ${monuments.length})` },
    { icon: MapPinned, value: `${stats.cities}`, label: text.cities },
    { icon: Footprints, value: stats.km.toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN'), label: text.km },
    { icon: Compass, value: `${stats.eras}`, label: text.eras },
  ]

  return (
    <main className="shell mx-auto space-y-8 px-5 pb-16 pt-6 lg:max-w-5xl lg:pt-10" lang={lang}>
      <section className="jali-hero relative overflow-hidden rounded-3xl p-6 sm:flex sm:items-center sm:gap-6 sm:p-8">
        <div aria-hidden="true" className="fraunces arch-avatar grid h-24 w-20 shrink-0 place-items-center text-4xl text-[#FBF6EC]">{initial}</div>
        <div className="mt-4 min-w-0 flex-1 sm:mt-0">
          <h1 className="fraunces text-sm font-normal uppercase tracking-[.2em] text-[#8F3221]">{text.title}</h1>
          <label className="sr-only" htmlFor="journey-name">{text.name}</label>
          <input className="fraunces mt-1 min-h-12 w-full rounded-lg border-b border-dashed border-[#B5452B]/40 bg-transparent text-3xl outline-none placeholder:text-[#5A4E3F]/70 focus:border-solid focus:border-[#B5452B]" id="journey-name" maxLength={60} onChange={(event) => setJourneyName(event.target.value)} placeholder={text.name} style={{ fontSize: '1.875rem' }} value={journey.name} />
          <p className="mt-2 text-sm font-semibold text-[#8F3221]">{stats.level[lang]} · <span className="font-normal text-[#5A4E3F]">{lang === 'hi' ? stats.level.noteHi : stats.level.noteEn}</span></p>
          <p className="mt-2 text-xs leading-5 text-[#5A4E3F]">{text.device}</p>
        </div>
      </section>

      <section aria-label={text.title} className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {statCards.map(({ icon: Icon, value, label }, index) => (
          <div className="rise" key={label} style={{ animationDelay: `${index * 70}ms` }}>
            <InlayFrame className="h-full">
              <div className="h-full rounded-[10px] bg-[#FBF6EC] p-4">
                <Icon aria-hidden="true" className="text-[#E8A317]" size={18} />
                <p className="fraunces mt-2 text-3xl text-[#B5452B]">{value}</p>
                <p className="mt-0.5 text-xs text-[#5A4E3F]">{label}</p>
              </div>
            </InlayFrame>
          </div>
        ))}
      </section>

      {stats.places === 0 ? (
        <section className="card p-8 text-center" data-testid="journey-empty">
          <Route aria-hidden="true" className="mx-auto text-[#B5452B]" size={30} />
          <h2 className="fraunces mt-3 text-2xl">{text.emptyTitle}</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#5A4E3F]">{text.empty}</p>
          <Link className="link-inverse primary-action mt-5 inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-6 font-semibold" href="/explore">{text.browse}<ArrowRight aria-hidden="true" size={16} /></Link>
        </section>
      ) : (
        <>
          <section>
            <h2 className="fraunces mb-3 text-2xl">{text.map}</h2>
            <div className="h-72 overflow-hidden rounded-2xl border border-[#E8A317]/50 shadow-md"><Map route stops={stats.ordered.map((visit) => visit.id)} /></div>
          </section>
          <section>
            <h2 className="fraunces mb-3 text-2xl">{text.visits}</h2>
            <ol className="space-y-3">
              {stats.ordered.map((visit, index) => {
                const monument = getMonument(visit.id)
                return (
                  <li className="card flex items-center gap-3 p-3" key={visit.id}>
                    <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-full bg-[#B5452B] text-sm font-semibold text-white">{index + 1}</span>
                    <Link aria-label={monument.name[lang]} className="shrink-0" href={`/monument/${visit.id}`}><MonumentArt alt="" className="size-16 rounded-lg" id={visit.id} /></Link>
                    <div className="min-w-0 flex-1">
                      <Link className="fraunces block break-words text-lg leading-snug" href={`/monument/${visit.id}`}>{monument.name[lang]}</Link>
                      <label className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-[#5A4E3F]">{text.visited}
                        <input className="min-h-12 rounded bg-transparent" max={today()} onChange={(event) => setVisitDate(visit.id, event.target.value)} type="date" value={visit.date} />
                      </label>
                    </div>
                    <button aria-label={`${text.remove} ${monument.name[lang]}`} className="grid size-12 shrink-0 place-items-center rounded-full text-[#8F3221] transition-colors hover:bg-[#EADBC0]" onClick={() => toggleVisit(visit.id)} type="button"><X aria-hidden="true" size={18} /></button>
                  </li>
                )
              })}
            </ol>
          </section>
          {stats.next.length > 0 && (
            <section>
              <h2 className="fraunces mb-3 text-2xl">{text.next}</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                {stats.next.map((monument) => (
                  <Link className="monument-card card group flex flex-col overflow-hidden" href={`/monument/${monument.id}`} key={monument.id}>
                    <MonumentArt alt="" className="aspect-[4/3] w-full" id={monument.id} />
                    <span className="fraunces p-3 leading-snug">{monument.name[lang]}</span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <LotusDivider />

      <section>
        <h2 className="fraunces mb-3 text-2xl">{text.tour}</h2>
        {tour.length ? (
          <>
            <ul className="space-y-2">
              {tour.map((id) => (
                <li className="card flex min-h-12 items-center justify-between gap-3 px-4 py-1" key={id}>
                  <Link className="min-w-0 break-words" href={`/monument/${id}`}>{getMonument(id).name[lang]}</Link>
                  <button aria-label={`${text.remove} ${getMonument(id).name[lang]}`} className="grid size-12 shrink-0 place-items-center rounded-full" onClick={() => toggleTour(id)} type="button"><X aria-hidden="true" size={16} /></button>
                </li>
              ))}
            </ul>
            {tour.length > 3 && <p className="mt-2 text-xs text-[#5A4E3F]">{text.tourLimit}</p>}
            <Link className="link-inverse primary-action mt-4 inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-6 font-semibold" href={tourPlanHref(tour)}>{text.planIt}<ArrowRight aria-hidden="true" size={16} /></Link>
          </>
        ) : <p className="text-sm leading-6 text-[#5A4E3F]">{text.tourEmpty}</p>}
      </section>

      {(stats.places > 0 || journey.name) && (
        <button className="inline-flex min-h-12 items-center gap-2 rounded-full px-3 text-sm text-[#8F3221] underline-offset-4 hover:underline" onClick={() => { if (window.confirm(text.confirm)) clearJourney() }} type="button"><Trash2 aria-hidden="true" size={15} />{text.clear}</button>
      )}
    </main>
  )
}
