'use client'
import { useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { getMood, type Mood } from '@/lib/mood'

const skyline = <><path d="M0 100V72h9V60h7v12h8V48h7v52h8V70h12v-8h6v8h8v-19h8v49h10V58h6v-8h8v50h8V64h11v-7h7v43h10V73h8v-8h7v35h10V60h8v-9h9v49h11V72h10v-8h7v36h12V55h8v45h12V68h7v-8h9v40h12V72h11v28H0Z"/><path d="M244 100V54h6v-7h4v7h5v-27h8v73h12V70h12v-8h7v38h11V54h8v46h11V74h12v-9h7v35h10V59h8v41h12V68h8v-8h9v40h11V50h7v50h10V70h8v-10h8v40h12V62h8v38h12V70h8v30h14V100Z"/></>
const monumentSilhouettes = <><path d="M48 100V54h11l3-19h6l3 19h11v46h-34Zm16-45 1-24h5l2 24Zm-8 9h20v3H56Zm-3 12h26v3H53Z"/><path d="M104 100V63h7v-7h7v7h16v-7h7v7h7v37Zm0-38 7-10 5 6 8-12 8 12 7-6 7 10Z"/><path d="M183 100V62h9q8-24 16 0h10q8-24 16 0h9v38Zm9-38q8-14 16 0m10 0q8-14 16 0" fill="none" stroke="currentColor" strokeWidth="5"/><path d="M286 100V65h7v-8h9v8h7v35Zm-3-35 10-17 10 17"/></>

function Sky({ mood, lite }: { mood: Mood; lite: boolean }) { return <div className={`atmosphere-sky atmosphere-${mood} ${lite ? 'atmosphere-lite' : ''}`} aria-hidden="true"><div className="atmosphere-sun"><span className="sun-rays" /></div><svg className="atmosphere-skyline atmosphere-skyline-back" viewBox="0 0 512 100" preserveAspectRatio="none"><g>{skyline}</g></svg>{!lite && <><svg className="atmosphere-skyline atmosphere-skyline-mid" viewBox="0 0 512 100" preserveAspectRatio="none"><g>{monumentSilhouettes}</g></svg><svg className="atmosphere-skyline atmosphere-skyline-front" viewBox="0 0 512 100" preserveAspectRatio="none"><g>{skyline}{monumentSilhouettes}</g></svg><div className="atmosphere-jali" /><div className="atmosphere-kites"><span className="kite kite-one" /><span className="kite kite-two" /><span className="kite kite-three" /></div><div className="atmosphere-birds"><i /><i /><i /><i /><i /></div><div className="atmosphere-petals">{Array.from({ length: 14 }, (_, i) => <b key={i} />)}</div></>}<div className="atmosphere-mandala" /><div className="atmosphere-buta">❧</div></div> }

export function Atmosphere() {
  const pathname = usePathname()
  const root = useRef<HTMLDivElement>(null)
  const [lite, setLite] = useState(false)
  const [hidden, setHidden] = useState(false)
  const [identifyState, setIdentifyState] = useState('scan')
  const mood = getMood(pathname, identifyState)
  const camera = pathname === '/identify'

  useEffect(() => {
    const readIdentifyState = () => setIdentifyState(document.documentElement.dataset.identifyState || 'scan')
    const observer = new MutationObserver(readIdentifyState)
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updateLite = () => setLite(motionPreference.matches || (navigator.hardwareConcurrency || 8) <= 4)
    const onVisibility = () => setHidden(document.hidden)
    const onPointer = (event: PointerEvent) => {
      if (window.innerWidth < 1024 || !root.current) return
      root.current.style.setProperty('--parallax-x', `${(event.clientX / window.innerWidth - .5) * 20}px`)
      root.current.style.setProperty('--parallax-y', `${(event.clientY / window.innerHeight - .5) * 12}px`)
    }
    observer.observe(document.documentElement, { attributes: true })
    queueMicrotask(readIdentifyState)
    queueMicrotask(updateLite)
    motionPreference.addEventListener('change', updateLite)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pointermove', onPointer, { passive: true })
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pointermove', onPointer)
      motionPreference.removeEventListener('change', updateLite)
      observer.disconnect()
    }
  }, [])

  return <div ref={root} className={`atmosphere atmosphere-${mood} ${hidden ? 'atmosphere-paused' : ''} ${camera ? 'atmosphere-camera' : ''}`} onPointerDown={(event) => { if (event.target === event.currentTarget) event.currentTarget.classList.add('atmosphere-burst') }}><Sky mood={mood} lite={lite} /></div>
}
