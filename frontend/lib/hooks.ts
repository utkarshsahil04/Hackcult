'use client'
import { useEffect, useState } from 'react'
export function useMediaQuery(query: string) { const [matches, setMatches] = useState(false); useEffect(() => { const media = window.matchMedia(query); const update = () => setMatches(media.matches); update(); media.addEventListener('change', update); return () => media.removeEventListener('change', update) }, [query]); return matches }

/** True once `active` has lasted `ms`. The hosted API sleeps when idle, so slow first requests need explaining. */
export function useAfter(active: boolean, ms: number) {
  const [elapsed, setElapsed] = useState(false)
  useEffect(() => {
    if (!active) return
    const timer = setTimeout(() => setElapsed(true), ms)
    return () => {
      clearTimeout(timer)
      setElapsed(false)
    }
  }, [active, ms])
  return active && elapsed
}

export const WAKING_MESSAGE = {
  en: 'Waking the server. After a quiet spell this can take up to a minute.',
  hi: 'सर्वर चालू हो रहा है। कुछ समय बाद पहली बार इसमें एक मिनट तक लग सकता है।',
}
