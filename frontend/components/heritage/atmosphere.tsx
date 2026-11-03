'use client'
import { LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion'
import { transitions } from '@/lib/motion'
export function Atmosphere({ mood='day' }: { mood?: 'day'|'dusk' }) { const reduced=useReducedMotion(); return <LazyMotion features={domAnimation}><m.div aria-hidden="true" className={`pointer-events-none fixed inset-0 z-0 ${mood==='dusk'?'bg-[radial-gradient(circle_at_70%_0%,rgba(232,163,23,.18),transparent_38%),linear-gradient(180deg,rgba(64,53,44,.18),transparent_55%)]':'bg-[radial-gradient(circle_at_10%_0%,rgba(232,163,23,.12),transparent_32%)]'}`} initial={{opacity:0}} animate={{opacity:1}} transition={reduced?transitions.fast:transitions.slow}/></LazyMotion> }
