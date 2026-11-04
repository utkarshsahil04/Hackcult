'use client'
import {AnimatePresence,MotionConfig,motion} from 'framer-motion'
import {usePathname} from 'next/navigation'
import {transitions,reducedMotion} from '@/lib/motion'
export default function Template({children}:{children:React.ReactNode}){const path=usePathname();return <MotionConfig reducedMotion="user"><AnimatePresence mode="wait"><motion.div className="page-enter" key={path} initial={false} animate={{opacity:1,transition:transitions.base}} exit={reducedMotion.exit}>{children}</motion.div></AnimatePresence></MotionConfig>}
