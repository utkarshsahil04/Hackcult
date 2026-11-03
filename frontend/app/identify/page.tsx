'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion'
import { Camera, CameraOff, ImagePlus } from 'lucide-react'
import { DesktopIdentify } from '@/components/identify/DesktopIdentify'
import { KolamLoader, MonumentArt } from '@/components/heritage'
import { RaaheinLogo } from '@/components/RaaheinLogo'
import { Toggle, useLang } from '@/components/raahein'
import { identify, type IdentifyResult } from '@/lib/api'
import { monuments, findMonument } from '@/lib/catalog'
import { delays, durations, transitions } from '@/lib/motion'

type IdentifyState = 'scan' | 'match' | 'uncertain' | 'error'
type CameraState = 'starting' | 'ready' | 'unavailable'

function CapturedPhoto({ src, className }: { src: string; className: string }) {
  if (!src) return <MonumentArt alt="Captured monument preview" className={className} id="taj-mahal" />
  // Blob URLs are local previews and cannot use the Next.js image optimizer.
  return <m.img layoutId="scan-photo" src={src} alt="Captured monument" className={className} />
}

export default function Identify() {
  const { lang, setLang, t } = useLang()
  const router = useRouter()
  const reduced = useReducedMotion()
  const video = useRef<HTMLVideoElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const [state, setState] = useState<IdentifyState>('scan')
  const [cameraState, setCameraState] = useState<CameraState>('starting')
  const [photo, setPhoto] = useState('')
  const [busy, setBusy] = useState(false)
  const [hint, setHint] = useState(0)
  const [selected, setSelected] = useState('')
  const [fileError, setFileError] = useState('')
  const [matchedMonument, setMatchedMonument] = useState(monuments[0])
  const [candidates, setCandidates] = useState(monuments.slice(0, 3))

  useEffect(() => {
    if (reduced) return
    const timer = window.setInterval(() => setHint((value) => (value + 1) % 2), 4000)
    return () => window.clearInterval(timer)
  }, [reduced])

  useEffect(() => {
    document.documentElement.dataset.identifyState = state
    return () => { delete document.documentElement.dataset.identifyState }
  }, [state])

  useEffect(() => {
    if (window.matchMedia('(min-width:1024px)').matches) return
    let active = true
    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (active) setCameraState('unavailable')
        return
      }
      try {
        const media = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        if (!active) {
          media.getTracks().forEach((track) => track.stop())
          return
        }
        stream.current = media
        if (video.current) video.current.srcObject = media
        setCameraState('ready')
      } catch {
        if (active) setCameraState('unavailable')
      }
    }
    void startCamera()
    return () => {
      active = false
      stream.current?.getTracks().forEach((track) => track.stop())
      stream.current = null
    }
  }, [])

  useEffect(() => () => {
    if (photo.startsWith('blob:')) URL.revokeObjectURL(photo)
  }, [photo])

  function reset() {
    setState('scan')
    setSelected('')
    setFileError('')
    setPhoto('')
    if (input.current) input.current.value = ''
  }

  async function run(file: File) {
    if (busy) return
    if (!file.type.startsWith('image/')) {
      setFileError(lang === 'hi' ? 'JPEG, PNG, GIF या WebP तस्वीर चुनें।' : 'Choose a JPEG, PNG, GIF, or WebP image.')
      return
    }
    if (file.size > 6 * 1024 * 1024) {
      setFileError(lang === 'hi' ? 'तस्वीर 6 MB से छोटी होनी चाहिए।' : 'Choose an image smaller than 6 MB.')
      return
    }
    setFileError('')
    setBusy(true)
    const preview = URL.createObjectURL(file)
    setPhoto(preview)
    try {
      const result = await identify(file) as IdentifyResult
      if (result.status === 'match') {
        setMatchedMonument(result.monument)
        setState('match')
      } else if (result.status === 'uncertain') {
        const slugs = result.candidates.map((c) => c.slug)
        setCandidates(slugs.map((s) => findMonument(s)).filter(Boolean) as typeof monuments)
        setState('uncertain')
      } else {
        setState('error')
      }
    } catch {
      setState('error')
    } finally {
      setBusy(false)
    }
  }

  function capture() {
    const source = video.current
    if (!source?.videoWidth || !source.videoHeight) {
      setCameraState('unavailable')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = source.videoWidth
    canvas.height = source.videoHeight
    canvas.getContext('2d')?.drawImage(source, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob) {
        setState('error')
        return
      }
      void run(new File([blob], 'monument.jpg', { type: 'image/jpeg' }))
    }, 'image/jpeg', .9)
  }

  return (
    <LazyMotion features={domAnimation}>
      <DesktopIdentify lang={lang} state={state} onUpload={run} />
      {state === 'error' ? (
        <main aria-live="polite" className="shell flex min-h-svh flex-col p-6 pb-24 lg:max-w-7xl lg:mx-auto" lang={lang}>
          <div className="flex justify-end lg:hidden"><Toggle lang={lang} setLang={setLang} /></div>
          <div className="flex flex-1 flex-col items-center justify-center text-center">
            <m.svg aria-label={lang === 'hi' ? 'टूटी हुई जाली' : 'Broken lattice window'} animate={{ opacity: 1, scale: 1 }} className="mb-8 size-44 text-[#B5452B]" initial={false} role="img" transition={transitions.base} viewBox="0 0 176 176">
              <path d="M28 148V76c0-58 120-58 120 0v72M52 148V82c0-30 72-30 72 0v66M28 106h120M52 82l72 66M124 82l-72 66" fill="none" stroke="currentColor" strokeWidth="3" />
              <path d="m78 70 14 18-11 15 17 22" fill="none" stroke="#E8A317" strokeWidth="5" />
            </m.svg>
            <h1 className="fraunces text-3xl">{t.errorHeading}</h1>
            <p className="mt-3 max-w-xs text-[#5A4E3F]">{t.errorBody}</p>
            <button onClick={reset} className="mt-8 min-h-14 w-full max-w-sm rounded-full bg-[#B5452B] px-6 font-semibold text-[#FBF6EC]" type="button">{t.tryAgain}</button>
            <Link href="/explore" className="link-primary mt-4 flex min-h-12 items-center">{t.browseInstead}</Link>
          </div>
        </main>
      ) : state === 'match' ? (
        <main aria-live="polite" className="shell min-h-svh pb-24 lg:max-w-7xl lg:mx-auto" lang={lang}>
          <CapturedPhoto src={photo} className="h-[45svh] w-full object-cover" />
          <m.div animate={{ y: 0, opacity: 1 }} className="card -mt-8 min-h-[55svh] rounded-t-3xl p-6" initial={false} transition={transitions.base}>
            <m.div animate={{ opacity: 1 }} className="text-sm text-[#5A4E3F]" initial={false} transition={{ ...transitions.fast, delay: delays.matchLabel }}>{t.likely}</m.div>
            <m.h1 animate={{ opacity: 1 }} className="fraunces mt-2 text-4xl" initial={false} transition={{ ...transitions.base, delay: delays.matchTitle }}>{matchedMonument.name[lang]}</m.h1>
            <div className="mt-3 h-px w-20 bg-[#E8A317]" />
            <p className="mt-3 text-[#5A4E3F]">{matchedMonument.city} · {t.similar}</p>
            <Link href={`/monument/${matchedMonument.id}`} className="link-inverse mt-10 flex min-h-14 items-center justify-center rounded-full bg-[#B5452B] px-6 text-center font-semibold">{t.read}</Link>
            <button onClick={reset} className="mt-3 min-h-12 w-full text-[#B5452B]" type="button">{t.notSure}</button>
          </m.div>
        </main>
      ) : state === 'uncertain' ? (
        <main aria-live="polite" className="shell min-h-svh p-5 pb-24 lg:max-w-7xl lg:mx-auto" lang={lang}>
          <div className="flex justify-end lg:hidden"><Toggle lang={lang} setLang={setLang} /></div>
          <CapturedPhoto src={photo} className="mt-3 h-40 w-full rounded-3xl object-cover" />
          <h1 className="fraunces mt-7 text-3xl">{t.notSureHeading}</h1>
          <p className="mt-2 text-[#5A4E3F]">{t.isOne}</p>
          <div className="my-6 space-y-3">
            {candidates.slice(0, 3).map((monument, index) => (
              <m.button
                animate={{ y: 0, rotate: 0, opacity: selected && selected !== monument.id ? .55 : 1 }}
                aria-pressed={selected === monument.id}
                className={`card flex min-h-20 w-full items-center gap-3 p-3 text-left ${selected === monument.id ? 'border-2 border-[#E8A317]' : ''}`}
                initial={false}
                key={monument.id}
                onClick={() => setSelected(monument.id)}
                transition={{ ...transitions.base, delay: index * delays.candidate }}
                type="button"
              >
                <MonumentArt alt="" className="size-16 shrink-0 rounded-xl" id={monument.id} />
                <span><span className="block font-semibold">{monument.name[lang]}</span><span className="text-sm text-[#5A4E3F]">{monument.city}</span></span>
              </m.button>
            ))}
          </div>
          <button disabled={!selected} onClick={() => router.push(`/monument/${selected}`)} className="min-h-14 w-full rounded-full bg-[#B5452B] px-6 font-semibold text-[#FBF6EC] disabled:cursor-not-allowed disabled:opacity-40" type="button">{t.yes}</button>
          <button onClick={reset} className="mt-2 min-h-12 w-full text-[#B5452B]" type="button">{t.tryPhoto}</button>
          <Link href="/explore" className="flex min-h-12 items-center justify-center text-[#5A4E3F]">{t.browse}</Link>
        </main>
      ) : (
        <main className="shell min-h-svh pb-24 lg:hidden" lang={lang}>
          <h1 className="sr-only">{t.scan}</h1>
          <header className="sticky top-0 z-40 flex items-center justify-between border-b border-[#E8A317]/20 bg-[#EADBC0]/95 px-5 py-2.5 backdrop-blur safe-top">
            <Link className="flex min-h-12 items-center" href="/" aria-label={t.app}>
              <RaaheinLogo className="h-9 w-24" />
            </Link>
            <Toggle lang={lang} setLang={setLang} />
          </header>
          <div className="relative mx-5 mt-3 h-[54svh] overflow-hidden rounded-[2rem] bg-[#D9C4A1]">
            {cameraState === 'unavailable' ? (
              <div className="flex h-full flex-col items-center justify-center rounded-t-[48%] border-2 border-[#E8A317] bg-gradient-to-b from-[#D9C4A1] to-[#B98961] p-8 text-center">
                <CameraOff aria-hidden="true" className="mb-4 text-[#B5452B]" size={42} />
                <p className="font-[var(--font-fraunces)] text-xl">{lang === 'hi' ? 'कैमरा उपलब्ध नहीं है' : "Camera isn't available here"}</p>
                <button onClick={() => input.current?.click()} className="mt-5 min-h-12 rounded-full bg-[#B5452B] px-6 font-semibold text-[#FBF6EC]" type="button">{lang === 'hi' ? 'तस्वीर अपलोड करें' : 'Upload a photo'}</button>
              </div>
            ) : (
              <video ref={video} aria-label={lang === 'hi' ? 'कैमरा दृश्य' : 'Camera preview'} autoPlay muted playsInline className="h-full w-full object-cover" />
            )}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/20" />
            <m.div animate={reduced ? undefined : { scale: [1, 1.03, 1] }} transition={{ duration: durations.slow, repeat: reduced ? 0 : Infinity }} className="pointer-events-none absolute inset-8 rounded-[1.5rem] border-2 border-[#E8A317]/80 shadow-[0_12px_34px_rgba(232,163,23,.24)]" />
            <div className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-[#E8A317]/70" />
            {(busy || cameraState === 'starting') && <div className="absolute inset-0 grid place-items-center bg-[#1F1A14]/15"><KolamLoader size="sm" /></div>}
            <AnimatePresence mode="wait">
              <m.p animate={{ opacity: 1, y: 0 }} className="absolute bottom-7 left-0 right-0 mx-auto w-fit rounded-full bg-[#1F1A14]/80 px-4 py-2 text-center text-sm text-white" exit={{ opacity: 0, y: -5 }} initial={{ opacity: 0, y: 5 }} key={hint} transition={transitions.fast}>{hint ? t.pointTwo : t.pointOne}</m.p>
            </AnimatePresence>
          </div>
          {fileError && <p className="mx-5 mt-3 text-sm text-[#8F3221]" role="alert">{fileError}</p>}
          <div className="flex items-center justify-center gap-8 py-5">
            <button onClick={() => input.current?.click()} className="grid size-12 place-items-center rounded-full border border-[#C8B594]" aria-label={lang === 'hi' ? 'तस्वीर अपलोड करें' : 'Upload photo'} type="button"><ImagePlus aria-hidden="true" /></button>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/gif,image/webp" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void run(file) }} />
            <button aria-label={lang === 'hi' ? 'तस्वीर लें' : 'Capture'} disabled={busy || cameraState !== 'ready'} onClick={capture} className="grid size-20 place-items-center rounded-full border-[7px] border-[#D9C4A1] bg-[#B5452B] text-white shadow-lg disabled:opacity-45" type="button"><Camera aria-hidden="true" size={28} /></button>
            <Link href="/explore" className="flex min-h-12 items-center text-center text-sm font-medium text-[#B5452B]">{t.browse}</Link>
          </div>
        </main>
      )}
    </LazyMotion>
  )
}
