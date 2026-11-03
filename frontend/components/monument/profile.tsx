'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion'
import { ArrowLeft, Box, Camera, Check, ChevronDown, ExternalLink, Pause, Play, Plus, X } from 'lucide-react'
import { DropCap, InlayFrame, ManuscriptPanel, Monument3DViewer, MonumentArt, SectionHeading } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { findMonument, getMonument, imageCredits, nearestMonuments } from '@/lib/catalog'
import { durations, springs, transitions } from '@/lib/motion'
import { getNarration } from '@/lib/narration'
import { fetchStory, type ApiStory } from '@/lib/api'

type Props = { id: string }

export function MonumentProfile({ id }: Props) {
  const monument = getMonument(id)
  const { lang, setLang, t } = useLang()
  const [apiStory, setApiStory] = useState<ApiStory | null>(null)
  const [scrolled, setScrolled] = useState(false)
  const [scrollProgress, setScrollProgress] = useState(0)
  const [audioProgress, setAudioProgress] = useState(0)
  const [audioError, setAudioError] = useState('')
  const [playing, setPlaying] = useState(false)
  const [source, setSource] = useState<number | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [added, setAdded] = useState(false)
  const [viewMode, setViewMode] = useState<'photo' | '3d'>('photo')
  const reduced = useReducedMotion()
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const returnFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 110)
      const max = document.documentElement.scrollHeight - window.innerHeight
      setScrollProgress(max > 0 ? Math.min(100, Math.round((window.scrollY / max) * 100)) : 0)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Story-pending sites have nothing to fetch, and asking for them is always a 404.
  useEffect(() => {
    if (monument.verified) fetchStory(id, lang).then(setApiStory).catch(() => {})
  }, [id, lang, monument.verified])

  useEffect(() => {
    if (!source) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeSource()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [source])

  useEffect(() => () => {
    audioRef.current?.pause()
    window.speechSynthesis?.cancel()
  }, [])

  function openSource(index: number) {
    returnFocus.current = document.activeElement as HTMLElement | null
    setSource(index)
  }

  function closeSource() {
    setSource(null)
    queueMicrotask(() => returnFocus.current?.focus())
  }

  async function toggleAudio() {
    setAudioError('')
    const narration = await getNarration(lang)
    if (narration.type === 'speech') {
      if (playing) {
        speechSynthesis.cancel()
        setPlaying(false)
        return
      }
      const utterance = new SpeechSynthesisUtterance(apiStory?.body ?? monument.sections.map((section) => section.text[lang]).join(' '))
      utterance.voice = narration.voice
      utterance.onend = () => setPlaying(false)
      utterance.onerror = () => { setPlaying(false); setAudioError(lang === 'hi' ? 'आवाज़ उपलब्ध नहीं है।' : 'Narration is unavailable right now.') }
      speechSynthesis.speak(utterance)
      setPlaying(true)
      return
    }
    if (!narration.url) {
      setAudioError(lang === 'hi' ? 'आवाज़ उपलब्ध नहीं है।' : 'Narration is unavailable right now.')
      return
    }
    if (!audioRef.current) {
      const audio = new Audio(narration.url)
      audio.ontimeupdate = () => setAudioProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0)
      audio.onended = () => { setPlaying(false); setAudioProgress(0) }
      audio.onerror = () => { setPlaying(false); setAudioError(lang === 'hi' ? 'ऑडियो लोड नहीं हुआ।' : 'The audio could not be loaded.') }
      audioRef.current = audio
    }
    if (audioRef.current.paused) {
      try {
        await audioRef.current.play()
        setPlaying(true)
      } catch {
        setAudioError(lang === 'hi' ? 'ऑडियो शुरू नहीं हुआ।' : 'The audio could not be started.')
      }
    } else {
      audioRef.current.pause()
      setPlaying(false)
    }
  }

  const credit = imageCredits[monument.id]
  // Sites with no sourced connections yet show their closest neighbours instead of an empty section.
  const connected = [...new Set(monument.related)].filter((slug) => findMonument(slug))
  const relatedCards = connected.length
    ? connected.map((slug) => ({ id: slug, detail: t.nearby }))
    : nearestMonuments(monument, 3).map(({ monument: near, km }) => ({ id: near.id, detail: `${km.toFixed(1)} km` }))
  const viewTab = (mode: 'photo' | '3d') => `flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-all ${viewMode === mode ? 'bg-[#B5452B] text-[#FBF6EC] shadow-xs' : 'text-[#5A4E3F] hover:text-[#1F1A14]'}`

  function toggleTour() {
    const next = !added
    setAdded(next)
    window.dispatchEvent(new CustomEvent('raahein-tour', { detail: next ? { add: { id: monument.id, name: monument.name[lang] } } : { remove: monument.id } }))
  }

  return (
    <LazyMotion features={domAnimation}>
      <div className="profile-progress" aria-hidden="true"><span style={{ width: `${scrollProgress}%` }} /></div>
      <main className="shell pb-28 lg:grid lg:max-w-7xl lg:grid-cols-12 lg:items-start lg:gap-x-12 lg:px-8 lg:pb-16 lg:mx-auto" lang={lang}>
        <m.header animate={{ opacity: 1 }} className={`fixed left-0 right-0 top-0 z-40 flex items-center justify-between px-5 py-4 transition-colors safe-top lg:hidden ${scrolled ? 'border-b border-[#E8A317]/25 bg-[#EADBC0]/95 backdrop-blur' : 'bg-gradient-to-b from-[#1F1A14]/45 to-transparent'}`} initial={false} transition={transitions.fast}>
          <Link href="/explore" aria-label={t.back} className="grid size-12 place-items-center rounded-full bg-[#FBF6EC]/90 text-[#1F1A14]"><ArrowLeft aria-hidden="true" size={20} /></Link>
          <div className={`${scrolled ? 'fraunces text-lg text-[#1F1A14]' : 'text-transparent'} max-w-[11rem] break-words text-center`}>{scrolled ? monument.name[lang] : ''}</div>
          <Toggle lang={lang} setLang={setLang} />
        </m.header>

        {/* Fixed Left Canvas: Clean aspect ratio, unblurred image, sticky on desktop */}
        <aside className="relative flex flex-col gap-3 px-5 pt-20 lg:sticky lg:top-24 lg:col-span-5 lg:gap-4 lg:self-start lg:px-0 lg:pt-0">
          {/* Visual Mode Selector: Photo vs 3D Architecture */}
          <div className="flex items-center gap-1.5 rounded-full border border-[#E8A317]/40 bg-[#FBF6EC] p-1 shadow-xs">
            <button aria-pressed={viewMode === 'photo'} className={viewTab('photo')} onClick={() => setViewMode('photo')} type="button">
              <Camera aria-hidden="true" size={15} />
              {lang === 'hi' ? 'तस्वीर' : 'Photo'}
            </button>
            <button aria-pressed={viewMode === '3d'} className={viewTab('3d')} onClick={() => setViewMode('3d')} type="button">
              <Box aria-hidden="true" size={15} />
              {lang === 'hi' ? '3D वास्तुकला' : '3D Architecture'}
            </button>
          </div>

          {viewMode === '3d' ? (
            <>
              <h1 className="fraunces text-3xl leading-tight text-[#1F1A14]">{monument.name[lang]}</h1>
              <Monument3DViewer monumentId={monument.id} name={monument.name[lang]} lang={lang} />
            </>
          ) : (
            <m.section animate={{ opacity: 1, y: 0 }} className="relative h-[44vh] min-h-80 w-full overflow-hidden rounded-2xl border border-[#E8A317]/50 shadow-xl sm:h-[400px] lg:h-[480px]" initial={false} transition={transitions.slow}>
              <div className="absolute inset-0"><MonumentArt alt={monument.name[lang]} className="size-full" id={monument.id} priority /></div>
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#1F1A14]/85 via-[#1F1A14]/40 to-transparent px-5 pb-5 pt-16">
                <h1 className="fraunces text-3xl leading-tight text-[#FBF6EC] drop-shadow sm:text-4xl">{monument.name[lang]}</h1>
                <p className="mt-1 text-xs text-[#FBF6EC]/85 sm:text-sm">{monument.city} · {monument.era}</p>
              </div>
            </m.section>
          )}

          {/* Desktop Tour Action: Cleanly docked beneath the fixed image, never overlaying */}
          <div className="hidden lg:block">
            <button
              aria-pressed={added}
              onClick={toggleTour}
              className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full bg-[#B5452B] font-semibold text-[#FBF6EC] shadow-md transition-transform hover:-translate-y-0.5 active:scale-95"
              type="button"
            >
              {added ? <><Check aria-hidden="true" size={20} />{t.added}</> : <><Plus aria-hidden="true" size={20} />{t.addTour}</>}
            </button>
          </div>
        </aside>

        <div className="mx-auto max-w-md space-y-6 px-5 pt-5 lg:col-span-7 lg:max-w-none lg:px-0 lg:pt-0">
          <Link className="link-primary hidden min-h-12 items-center gap-2 lg:inline-flex" href="/explore"><ArrowLeft aria-hidden="true" size={18} />{t.back}</Link>
          <div className="flex flex-wrap gap-2">
            {[
              monument.city,
              monument.era,
              monument.style,
              ...(monument.verified ? [`${monument.sources.length} ${lang === 'hi' ? 'प्रमाणित स्रोत' : 'Verified Sources'}`] : []),
            ].map((chip, index) => <m.span animate={{ opacity: 1, y: 0 }} className="rounded-full border border-[#B5452B]/25 bg-[#FBF6EC] px-3 py-1.5 text-xs font-semibold text-[#5A4E3F]" initial={false} key={chip} transition={{ ...transitions.base, delay: index * .06 }}>{chip}</m.span>)}
          </div>
          {monument.verified && (
          <InlayFrame>
            <div className="rounded-[11px] bg-[#FBF6EC] p-4">
              <div className="flex items-center gap-3">
                <button onClick={toggleAudio} aria-label={playing ? (lang === 'hi' ? 'रोकें' : 'Pause') : (lang === 'hi' ? 'चलाएं' : 'Play')} className="grid size-12 shrink-0 place-items-center rounded-full bg-[#B5452B] text-[#FBF6EC]" type="button">{playing ? <Pause aria-hidden="true" size={18} /> : <Play aria-hidden="true" fill="currentColor" size={18} />}</button>
                <div className="min-w-0 flex-1">
                  <p className="fraunces text-lg">{t.listen}</p>
                  <div aria-label={lang === 'hi' ? 'ऑडियो प्रगति' : 'Audio progress'} className="mt-2 h-1 rounded-full bg-[#EADBC0]" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(audioProgress)}><div className="h-full rounded-full bg-[#E8A317] transition-[width]" style={{ width: `${audioProgress}%` }} /></div>
                </div>
                <span className="text-xs text-[#5A4E3F]">{lang === 'hi' ? 'हिं आवाज़' : 'EN voice'}</span>
              </div>
              <div aria-hidden="true" className="mt-3 flex h-5 items-end gap-1 opacity-80">{Array.from({ length: 24 }, (_, index) => <m.i animate={playing && !reduced ? { height: [5, 8 + ((index * 7) % 13), 5] } : { height: 5 }} className="w-[3px] rounded-full bg-[#B5452B]" key={index} transition={playing && !reduced ? { duration: durations.slow, repeat: Infinity, delay: index * .02 } : transitions.fast} />)}</div>
              {audioError && <p className="mt-3 text-sm text-[#8F3221]" role="alert">{audioError}</p>}
            </div>
          </InlayFrame>
          )}
          <ManuscriptPanel>
            {apiStory?.body ? (
              <m.section className="mb-8 last:mb-0" initial={false} transition={transitions.base}>
                <p className="text-[16px] leading-[1.75]">
                  <DropCap hindi={lang === 'hi'}>{apiStory.body}</DropCap>
                </p>
              </m.section>
            ) : !monument.verified ? (
              <div data-testid="story-pending">
                <p className="text-[16px] leading-[1.75]">{lang === 'hi' ? 'इस स्थान की कहानी अभी तैयार नहीं है। हम केवल दो स्वतंत्र स्रोतों से जाँचे गए तथ्य ही प्रकाशित करते हैं।' : 'This story is not ready yet. We only publish facts checked against two independent sources.'}</p>
                <button className="mt-4 inline-flex min-h-12 items-center gap-2 rounded-full border border-[#B5452B]/40 px-5 text-sm font-semibold text-[#8F3221] transition-colors hover:border-[#B5452B] hover:bg-[#EADBC0]/50" onClick={() => { setViewMode('3d'); window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' }) }} type="button"><Box aria-hidden="true" size={16} />{lang === 'hi' ? 'इस इमारत को 3D में देखें' : 'Explore the building in 3D'}</button>
              </div>
            ) : (
              monument.sections.map((section, index) => (
                <m.section className="mb-8 last:mb-0" initial={false} key={index} transition={{ ...transitions.base, delay: index * .06 }} viewport={{ once: true, amount: .25 }} whileInView={{ opacity: 1, y: 0 }}>
                  <SectionHeading>{section.heading?.[lang]}</SectionHeading>
                  {section.isLegend && <div className="mb-3 inline-block rounded-full border border-[#E8A317] px-3 py-1 text-xs font-semibold text-[#8F3221]">{t.legend}</div>}
                  <p className="text-[16px] leading-[1.75]">{index === 0 ? <DropCap hindi={lang === 'hi'}>{section.text[lang]}</DropCap> : section.text[lang]} {section.source && <button onClick={() => openSource(section.source!)} aria-label={`${t.source} ${section.source}`} className="-my-3 ml-1 inline-flex size-12 items-center justify-center align-middle" type="button"><span className="grid size-6 place-items-center rounded-full bg-[#E8A317] text-xs font-bold text-[#1F1A14]">{section.source}</span></button>}</p>
                </m.section>
              ))
            )}
          </ManuscriptPanel>
          {monument.sources.length > 0 && (
          <div>
            <button aria-controls="profile-sources" aria-expanded={sourcesOpen} onClick={() => setSourcesOpen((open) => !open)} className="fraunces flex min-h-12 w-full items-center justify-between border-b border-[#B5452B]/20 py-3 text-left text-xl" type="button"><span>{t.sources}</span><ChevronDown aria-hidden="true" className={sourcesOpen ? 'rotate-180 transition-transform' : 'transition-transform'} /></button>
            <m.div animate={{ height: sourcesOpen ? 'auto' : 0, opacity: sourcesOpen ? 1 : 0 }} aria-hidden={!sourcesOpen} className="overflow-hidden" id="profile-sources" initial={false}>
              {monument.sources.map((item, index) => <div id={`source-${index + 1}`} key={item.url ?? index} className={`flex flex-wrap items-center justify-between gap-2 border-b border-[#B5452B]/10 py-3 text-sm ${source === index + 1 ? 'rounded-lg bg-[#E8A317]/20 px-2' : ''}`}><a className="link-primary inline-flex min-h-12 items-center gap-1 underline-offset-2 hover:underline" href={item.url} rel="noreferrer" tabIndex={sourcesOpen ? undefined : -1} target="_blank">{index + 1}. {item.title[lang]}<ExternalLink aria-hidden="true" className="shrink-0" size={12} /></a><span className="text-[#5A4E3F]">{item.publisher[lang]}</span></div>)}
            </m.div>
          </div>
          )}
          <section>
            <div className="mb-3 flex items-center justify-between gap-3"><h2 className="fraunces text-2xl">{connected.length ? t.related : lang === 'hi' ? 'पास के स्मारक' : 'Nearby monuments'}</h2><Link className="link-primary flex min-h-12 items-center text-sm font-semibold" href={`/monument/${monument.id}/related`}>{lang === 'hi' ? 'सभी देखें' : 'View all'}</Link></div>
            <div className="grid grid-cols-1 gap-3 pb-2 sm:grid-cols-2 lg:grid-cols-3">
              {relatedCards.map((card) => { const related = getMonument(card.id); return <Link href={`/monument/${related.id}`} key={related.id} className="monument-card group rounded-2xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]"><InlayFrame className="h-full"><div className="h-full rounded-[10px] bg-[#FBF6EC]"><MonumentArt alt="" className="h-28 w-full rounded-t-[10px]" id={related.id} /><p className="fraunces p-2 pb-0 text-base leading-snug">{related.name[lang]}</p><p className="px-2 pb-2 pt-0.5 text-xs text-[#5A4E3F]">{related.city} · {card.detail}</p></div></InlayFrame></Link>})}
            </div>
          </section>
          {credit && <p className="pt-2 text-xs leading-5 text-[#5A4E3F]">{lang === 'hi' ? 'तस्वीर' : 'Photo'}: <a className="underline underline-offset-2 hover:text-[#1F1A14]" href={credit.page} rel="noreferrer" target="_blank">{credit.artist}</a>, {credit.licence}, Wikimedia Commons</p>}
        </div>
        {/* Mobile Fixed Action Bar: Isolated at bottom with safe padding, hidden on desktop */}
        <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-[#E8A317]/30 bg-[#EADBC0]/95 p-3.5 backdrop-blur safe-bottom lg:hidden">
          <button
            aria-pressed={added}
            onClick={toggleTour}
            className="mx-auto flex min-h-12 w-full max-w-md items-center justify-center gap-2 rounded-full bg-[#B5452B] font-semibold text-[#FBF6EC] shadow-lg active:scale-95 text-sm"
            type="button"
          >
            {added ? <><Check aria-hidden="true" size={18} />{t.added}</> : <><Plus aria-hidden="true" size={18} />{t.addTour}</>}
          </button>
        </div>
        {source && (
          <div className="fixed inset-0 z-50 bg-[#1F1A14]/35" onClick={closeSource}>
            <m.div aria-labelledby="source-dialog-title" aria-modal="true" className="absolute inset-x-0 bottom-0 rounded-t-[24px] bg-[#FBF6EC] p-6" initial={{ y: '100%' }} animate={{ y: 0 }} onClick={(event) => event.stopPropagation()} role="dialog" transition={springs.soft}>
              <button aria-label={lang === 'hi' ? 'बंद करें' : 'Close'} autoFocus className="absolute right-4 top-4 grid size-12 place-items-center rounded-full" onClick={closeSource} type="button"><X aria-hidden="true" /></button>
              <p className="text-sm text-[#B5452B]">{t.source} {source}</p>
              <h2 className="mt-2 pr-14 fraunces text-2xl" id="source-dialog-title">{monument.sources[source - 1]?.title[lang]}</h2>
              <p className="mt-1 text-[#5A4E3F]">{monument.sources[source - 1]?.publisher[lang]}</p>
            </m.div>
          </div>
        )}
      </main>
    </LazyMotion>
  )
}
