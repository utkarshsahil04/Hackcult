'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, CalendarDays, Compass, ScanLine, UserRound, X } from 'lucide-react'
import { Tabs, Toggle, useLang } from '@/components/raahein'
import { RaaheinLogo } from '@/components/RaaheinLogo'
import { ScrollProgress } from '@/components/heritage'
import { SiteFooter } from '@/components/shell/SiteFooter'
import { getMonument } from '@/lib/catalog'
import { toggleTour, tourPlanHref, useTour } from '@/lib/journey'
import { transitions } from '@/lib/motion'

const navItems = [
  { href: '/identify', id: 'scan', icon: ScanLine },
  { href: '/explore', id: 'explore', icon: Compass },
  { href: '/plan', id: 'plan', icon: CalendarDays },
  { href: '/profile', id: 'profile', icon: UserRound },
] as const

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { lang, setLang, t } = useLang()
  const tour = useTour()
  const [scrolled, setScrolled] = useState(false)
  const [tourOpen, setTourOpen] = useState(false)
  const labels = { scan: t.scan, explore: t.explore, plan: t.plan, profile: lang === 'hi' ? 'मेरी यात्रा' : 'My journey' }
  const mobileTab = pathname.startsWith('/identify')
    ? 'scan'
    : pathname === '/plan'
      ? 'plan'
      : pathname.startsWith('/explore') || pathname.startsWith('/nearby')
        ? 'explore'
        : pathname === '/profile'
          ? 'profile'
          : null
  // Full-screen tools have no page end for a footer to sit at.
  const footer = !pathname.startsWith('/identify') && !pathname.startsWith('/nearby') && !pathname.startsWith('/kit')

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
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
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('pointerdown', onRipple)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('pointerdown', onRipple)
    }
  }, [])

  return (
    <div className="app-shell">
      <ScrollProgress />
      <header className={`desktop-nav site-header ${scrolled ? 'is-scrolled' : ''}`}>
        <Link href="/" className="flex min-h-12 items-center" aria-label={t.app}>
          <RaaheinLogo className="h-11 w-28" />
        </Link>
        <nav aria-label={lang === 'hi' ? 'मुख्य नेविगेशन' : 'Primary navigation'} className="flex items-center gap-1 text-sm font-semibold">
          {navItems.map(({ href, id, icon: Icon }) => {
            const current = pathname === href || (id === 'explore' && pathname === '/nearby')
            return (
              <Link aria-current={current ? 'page' : undefined} className={`nav-link inline-flex min-h-12 min-w-12 items-center ${current ? 'link-primary' : ''}`} href={href} key={id}>
                {current && <motion.span aria-hidden="true" className="nav-mark" layoutId="nav-mark" transition={transitions.base} />}
                <Icon aria-hidden="true" className="relative" size={16} /> <span className="relative">{labels[id]}</span>
              </Link>
            )
          })}
        </nav>
        <div className="relative flex items-center gap-3">
          <button aria-expanded={tourOpen} aria-haspopup="dialog" className="primary-action min-h-12 rounded-full border border-[#E8A317] bg-[#FBF6EC]/70 px-4 transition-colors hover:bg-[#FBF6EC]" onClick={() => setTourOpen((open) => !open)} type="button">
            {lang === 'hi' ? 'टूर' : 'Tour'} · {tour.length}
          </button>
          <Toggle lang={lang} setLang={setLang} />
          <AnimatePresence>
            {tourOpen && (
              <motion.div animate={{ opacity: 1, y: 0, scale: 1 }} aria-label={lang === 'hi' ? 'आपका टूर' : 'Your tour'} className="absolute right-0 top-14 z-50 w-72 rounded-2xl border border-[#E8A317] bg-[#FBF6EC] p-4 shadow-2xl" exit={{ opacity: 0, y: -8, scale: .98 }} initial={{ opacity: 0, y: -8, scale: .98 }} role="dialog" transition={transitions.fast}>
                <h2 className="fraunces text-xl">{lang === 'hi' ? 'आपका टूर' : 'Your tour'}</h2>
                {tour.length ? (
                  <>
                  <ul className="mt-3 space-y-2">
                    {tour.map((id) => getMonument(id)).map((stop) => (
                      <li className="flex min-h-12 items-center justify-between gap-3 rounded-xl bg-[#EADBC0] px-3 py-2 text-sm" key={stop.id}>
                        <span className="min-w-0 break-words">{stop.name[lang]}</span>
                        <button aria-label={`${lang === 'hi' ? 'हटाएं' : 'Remove'} ${stop.name[lang]}`} className="grid size-12 shrink-0 place-items-center rounded-full" onClick={() => toggleTour(stop.id)} type="button">
                          <X aria-hidden="true" size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <Link className="link-inverse primary-action mt-3 flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#B5452B] px-4 text-sm font-semibold" href={tourPlanHref(tour)} onClick={() => setTourOpen(false)}>{lang === 'hi' ? 'इन पड़ावों की योजना बनाएं' : 'Plan these stops'}<ArrowRight aria-hidden="true" size={15} /></Link>
                  </>
                ) : (
                  <p className="mt-3 text-sm text-[#5A4E3F]">{lang === 'hi' ? 'आपका टूर खाली है।' : 'Your tour is empty.'}</p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </header>
      {children}
      {footer && <SiteFooter />}
      {mobileTab && <Tabs active={mobileTab} />}
    </div>
  )
}
