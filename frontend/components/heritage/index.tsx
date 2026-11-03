'use client'

import { forwardRef, useId, useImperativeHandle, useRef, useState } from 'react'
import Image from 'next/image'
import { LazyMotion, domAnimation, m, useReducedMotion, useScroll, useSpring } from 'framer-motion'
import { durations, springs, transitions } from '@/lib/motion'
import { monumentImages } from '@/lib/catalog'
export { Atmosphere } from './atmosphere'
export { HeritageSimulator } from './HeritageSimulator'
import dynamic from 'next/dynamic'
export const Monument3DViewer = dynamic(() => import('./Monument3DViewer').then((mod) => mod.Monument3DViewer), {
  ssr: false,
  loading: () => <div className="h-[380px] w-full rounded-2xl border border-[#E8A317]/50 bg-[#EADBC0] animate-pulse" />,
})

const KitMotion = ({ children }: { children: React.ReactNode }) => <LazyMotion features={domAnimation}>{children}</LazyMotion>

function IllustratedMonument({ id, alt, className }: { id: string; alt: string; className: string }) { return <div className={`relative overflow-hidden bg-gradient-to-b from-[#D9C4A1] to-[#B98961] ${className}`} aria-label={alt} role="img"><svg viewBox="0 0 240 180" className="absolute inset-0 h-full w-full text-[#7F4B34]" aria-hidden="true"><path d={id === 'qutb-complex' ? 'M112 160 124 28l12 132Zm-8-90h40l-4 10h-34Zm-4 27h48l-4 10h-40Z' : id === 'red-fort' ? 'M28 150V78h184v72M28 78l18-24 20 24 54-28 54 28 20-24 18 24M102 150v-38h36v38' : id === 'humayuns-tomb' ? 'M48 150V88h144v62M78 88q42-70 84 0v62H78Z' : id === 'fatehpur-sikri' ? 'M30 150V72h180v78M30 72l18-24 18 24 54-38 54 38 18-24 18 24M104 150v-38h32v38' : id === 'agra-fort' ? 'M28 150V76h184v74M28 76q20-24 40 0m104 0q20-24 40 0M103 150v-48h34v48' : 'M64 150V84h112v66M82 84q38-74 76 0M53 150V92l10-18 10 18v58M167 150V92l10-18 10 18v58'} fill="currentColor" opacity=".82"/><path d="M100 150v-38h40v38" fill="#EADBC0"/></svg></div> }

export function MonumentArt({ id = 'taj-mahal', alt = 'Monument', className = '' }: { id?: string; alt?: string; className?: string }) { const src = monumentImages[id]; const [failedSrc, setFailedSrc] = useState(''); return !src || failedSrc === src ? <IllustratedMonument alt={alt} className={className} id={id} /> : <div className={`relative overflow-hidden bg-[#D9C4A1] ${className}`}><Image src={src} alt={alt} fill sizes="(max-width: 640px) 50vw, (max-width: 1280px) 25vw, 320px" className="object-cover" onError={() => setFailedSrc(src)} /></div> }

export function ArchImage({ src, alt, className = '', layoutId }: { src: string; alt: string; className?: string; layoutId?: string }) { const [failedSrc, setFailedSrc] = useState(''); const uniqueId = useId().replaceAll(':', ''); const id = Object.entries(monumentImages).find(([, image]) => image === src)?.[0] ?? src.split('/').pop()?.replace(/\.[^.]+$/, '') ?? 'taj-mahal'; const clipId = `arch-${uniqueId}`; const illustrated = src.startsWith('/monuments/'); const failed = failedSrc === src; return <div className={`relative overflow-hidden rounded-t-[48%] rounded-b-[16px] border border-[#E8A317]/70 bg-[#EADBC0] ${className}`}><svg className="absolute h-0 w-0" aria-hidden="true"><defs><clipPath id={clipId} clipPathUnits="objectBoundingBox"><path d="M0 1V.42C0 .14 .22 0 .5 0s.5 .14 .5 .42V1Z" /></clipPath></defs></svg>{failed || illustrated ? <IllustratedMonument alt={alt} id={id} className="absolute inset-0 h-full w-full"/> : <div className="absolute inset-0" style={{ clipPath: `url(#${clipId})` }}>{layoutId ? <m.div layoutId={layoutId} className="absolute inset-0"><Image src={src} alt={alt} fill sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 960px" className="object-cover" loading="eager" onError={() => setFailedSrc(src)} /></m.div> : <Image src={src} alt={alt} fill sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 960px" className="object-cover" loading="eager" onError={() => setFailedSrc(src)} />}</div>}<div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#1F1A14]/55 to-transparent" /></div> }

export function InlayFrame({ children, variant = 'default', className = '' }: { children: React.ReactNode; variant?: 'default' | 'selected'; className?: string }) { return <KitMotion><m.div initial={false} whileInView={{ opacity: 1, clipPath: 'inset(0% 0% 0% 0% round 16px)' }} viewport={{ once: true, amount: .25 }} transition={transitions.slow} className={`relative rounded-[16px] border border-[#E8A317] p-[6px] ${variant === 'selected' ? 'shadow-[0_10px_28px_rgba(232,163,23,.25)]' : ''} ${className}`}><div className="pointer-events-none absolute inset-1 rounded-[12px] border border-[#E8A317]/35" />{children}</m.div></KitMotion> }

export function VineDivider({ className = '' }: { className?: string }) {
  const reduced = useReducedMotion()
  return <KitMotion><m.svg viewBox="0 0 240 24" className={`h-6 w-full text-[#E8A317] ${className}`} aria-hidden="true" initial={false} whileInView={{ pathLength: 1, opacity: 1 }} viewport={{ once: true, amount: .7 }} transition={reduced ? transitions.fast : transitions.slow}><path d="M4 12c38-12 54 12 88 0s50-12 70 0 34 12 74 0M55 9c-3-7-9-7-13-4 4 3 8 5 13 4Zm122 5c5-7 11-7 15-3-4 3-9 5-15 3Z" fill="none" stroke="currentColor" strokeWidth="1.2" /></m.svg></KitMotion>
}

export function KolamLoader({ size = 'md' }: { size?: 'sm' | 'md' }) { const s = size === 'sm' ? 34 : 52; return <KitMotion><m.svg width={s} height={s} viewBox="0 0 50 50" aria-label="Loading" role="status" className="text-[#B5452B]"><m.path d="M10 10h30v30H10zm0 15h30M25 10v30M14 14l22 22M36 14 14 36" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" animate={{ strokeDashoffset: [0, -32] }} transition={{ duration: durations.slow * 2, repeat: Infinity, ease: 'linear' }} /></m.svg></KitMotion> }

export type PetalBurstHandle = { trigger: () => void }
export const PetalBurst = forwardRef<PetalBurstHandle>(function PetalBurst(_, ref) { const control = useRef<(() => void) | null>(null); useImperativeHandle(ref, () => ({ trigger: () => control.current?.() })); return <KitMotion><m.div className="pointer-events-none fixed inset-0 z-50" animate={false} ref={(node) => { control.current = () => { if (node) node.dataset.burst = String(Date.now()) } }} aria-hidden="true" /></KitMotion> })

export function DropCap({ children, hindi = false }: { children: string; hindi?: boolean }) { return <span className={`dropcap ${hindi ? 'font-[var(--font-devanagari)]' : 'font-[var(--font-fraunces)]'}`}>{children}</span> }
export function SectionHeading({ children }: { eyebrow?: string; children: React.ReactNode }) { return <KitMotion><m.div className="mb-3"><div className="title-mask"><m.h2 initial={false} whileInView={{ y: 0 }} viewport={{ once: true }} transition={transitions.slow} className="page-title font-[var(--font-fraunces)] text-2xl text-[#1F1A14]">{children}</m.h2></div><VineDivider /></m.div></KitMotion> }
export function ManuscriptPanel({ children, className = '' }: { children: React.ReactNode; className?: string }) { return <InlayFrame className={`bg-[#FBF6EC] ${className}`}><div className="rounded-[10px] bg-[#FBF6EC] p-5 text-[#5A4E3F] shadow-inner">{children}</div></InlayFrame> }

export function Dock({ children }: { children: React.ReactNode }) { return <nav className="fixed bottom-4 left-1/2 z-30 flex min-h-14 -translate-x-1/2 items-center gap-1 rounded-full border border-[#E8A317]/45 bg-[#FBF6EC]/95 p-1.5 shadow-[0_10px_30px_rgba(31,26,20,.14)] backdrop-blur">{children}</nav> }

export function CaravanRoute({ points }: { points: Array<[number, number]> }) { const d = points.map(([x, y], i) => `${i ? 'L' : 'M'} ${x} ${y}`).join(' '); return <KitMotion><m.svg viewBox="0 0 320 180" className="h-full w-full" aria-label="Tour route"><m.path d={d} fill="none" stroke="#B5452B" strokeWidth="3" strokeDasharray="7 8" animate={{ strokeDashoffset: [0, -60] }} transition={{ duration: durations.intro * 4, repeat: Infinity, ease: 'linear' }} /><path d={d} fill="none" stroke="#B5452B" strokeWidth="8" opacity=".1" />{points.map(([x, y], i) => <m.circle key={`${x}-${y}`} cx={x} cy={y} r="6" fill="#E8A317" initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ ...springs.soft, delay: i * durations.fast }} />)}</m.svg></KitMotion> }

export function Reveal({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) { const reduce = useReducedMotion(); return <KitMotion><m.div className={className} initial={{ opacity: 0, y: reduce ? 0 : 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-60px' }} transition={{ ...transitions.slow, delay }}>{children}</m.div></KitMotion> }

export function ScrollProgress() { const { scrollYProgress } = useScroll(); const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 26 }); return <KitMotion><m.div aria-hidden="true" className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-[#E8A317]" style={{ scaleX }} /></KitMotion> }
