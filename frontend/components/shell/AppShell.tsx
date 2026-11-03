'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, m } from 'framer-motion'
import { CalendarDays, Compass, ScanLine, X } from 'lucide-react'
import { Tabs, Toggle, useLang } from '@/components/raahein'
import { RaaheinLogo } from '@/components/RaaheinLogo'
import { ScrollProgress } from '@/components/heritage'
import { transitions } from '@/lib/motion'

type TourStop = { id: string; name: string }
type TourEvent = { add?: TourStop; remove?: string }

const navItems = [
  { href: '/identify', id: 'scan', icon: ScanLine },
  { href: '/explore', id: 'explore', icon: Compass },
  { href: '/plan', id: 'plan', icon: CalendarDays },
] as const

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { lang, setLang, t } = useLang()
  const [stops, setStops] = useState<TourStop[]>([])
  const [tourOpen, setTourOpen] = useState(false)
  const labels = { scan: t.scan, explore: t.explore, plan: t.plan }
  const mobileTab = pathname.startsWith('/identify')
    ? 'scan'
    : pathname === '/plan'
      ? 'plan'
      : pathname.startsWith('/explore') || pathname.startsWith('/nearby')
        ? 'explore'
        : null

  useEffect(() => {
    const onTour = (event: Event) => {
      const detail = (event as CustomEvent<TourEvent>).detail
      setStops((current) => {
        if (detail.remove) return current.filter((stop) => stop.id !== detail.remove)
        if (!detail.add || current.some((stop) => stop.id === detail.add?.id)) return current
        return [...current, detail.add]
      })
    }
    const onRipple = (event: PointerEvent) => {
      const target = (event.target as HTMLElement).closest('button,[data-ripple]') as HTMLElement | null
      if (!target || window.matchMedia('(min-width:1024px)').matches) return
      const ripple = document.createElement('span')
      const rect = target.getBoundingClientRect()
      ripple.className = 'tap-ripple'
      ripple.style.left = `${event.clientX - rect.left}px`
      ripple.style.top = `${event.clientY - rect.top}px`
      target.appendChild(ripple)
      window.setTimeout(() => ripple.remove(), 500)
    }
    window.addEventListener('raahein-tour', onTour)
    window.addEventListener('pointerdown', onRipple)
    return () => {
      window.removeEventListener('raahein-tour', onTour)
      window.removeEventListener('pointerdown', onRipple)
    }
  }, [])

  function removeStop(stop: TourStop) {
    window.dispatchEvent(new CustomEvent<TourEvent>('raahein-tour', { detail: { remove: stop.id } }))
  }

  return (
    <div className="app-shell">
      <ScrollProgress />
      <header className="desktop-nav">
        <Link href="/" className="flex min-h-12 items-center" aria-label={t.app}>
          <RaaheinLogo className="h-11 w-28" />
        </Link>
        <nav aria-label={lang === 'hi' ? 'मुख्य नेविगेशन' : 'Primary navigation'} className="flex items-center gap-8 text-sm font-semibold">
          {navItems.map(({ href, id, icon: Icon }) => {
            const current = pathname === href || (id === 'explore' && pathname === '/nearby')
            return (
              <Link aria-current={current ? 'page' : undefined} className={`inline-flex min-h-12 min-w-12 items-center ${current ? 'link-primary' : ''}`} href={href} key={id}>
                <Icon aria-hidden="true" size={16} /> {labels[id]}
              </Link>
            )
          })}
        </nav>
        <div className="relative flex items-center gap-3">
          <button aria-expanded={tourOpen} aria-haspopup="dialog" className="primary-action min-h-12 rounded-full border border-[#E8A317] px-4" onClick={() => setTourOpen((open) => !open)} type="button">
            {lang === 'hi' ? 'टूर' : 'Tour'} · {stops.length}
          </button>
          <Toggle lang={lang} setLang={setLang} />
          <AnimatePresence>
            {tourOpen && (
              <m.div animate={{ opacity: 1, y: 0, scale: 1 }} aria-label={lang === 'hi' ? 'आपका टूर' : 'Your tour'} className="absolute right-0 top-14 z-50 w-72 rounded-2xl border border-[#E8A317] bg-[#FBF6EC] p-4 shadow-2xl" exit={{ opacity: 0, y: -8, scale: .98 }} initial={{ opacity: 0, y: -8, scale: .98 }} role="dialog" transition={transitions.fast}>
                <h2 className="fraunces text-xl">{lang === 'hi' ? 'आपका टूर' : 'Your tour'}</h2>
                {stops.length ? (
                  <ul className="mt-3 space-y-2">
                    {stops.map((stop) => (
                      <li className="flex min-h-12 items-center justify-between gap-3 rounded-xl bg-[#EADBC0] px-3 py-2 text-sm" key={stop.id}>
                        <span className="min-w-0 break-words">{stop.name}</span>
                        <button aria-label={`${lang === 'hi' ? 'हटाएं' : 'Remove'} ${stop.name}`} className="grid size-12 shrink-0 place-items-center rounded-full" onClick={() => removeStop(stop)} type="button">
                          <X aria-hidden="true" size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-[#5A4E3F]">{lang === 'hi' ? 'आपका टूर खाली है।' : 'Your tour is empty.'}</p>
                )}
              </m.div>
            )}
          </AnimatePresence>
        </div>
      </header>
      {children}
      {mobileTab && <Tabs active={mobileTab} />}
    </div>
  )
}
