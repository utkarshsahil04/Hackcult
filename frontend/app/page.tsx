'use client'

import Link from 'next/link'
import { ArrowRight, Compass, MapPinned, Route } from 'lucide-react'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Toggle, useLang } from '@/components/raahein'
import { ArchImage, InlayFrame, VineDivider } from '@/components/heritage'
import { monuments } from '@/lib/mock'
import { transitions } from '@/lib/motion'

const homeCopy = {
  en: {
    heading: 'Stories in stone, found along the way.',
    body: 'Scan a monument, hear its story, and build a day around the places that stay with you.',
    begin: 'Begin exploring',
    how: 'How it works',
    scan: 'Scan',
    nearby: 'Nearby',
    plan: 'Plan a day',
    steps: [
      ['Scan a monument', 'Point your camera at the stonework.'],
      ['Hear the story', 'Follow a sourced story in your language.'],
      ['Build your day', 'Shape a route around what moved you.'],
    ],
  },
  hi: {
    heading: 'पत्थरों की कहानियां, आपकी राहों के साथ।',
    body: 'स्मारक को स्कैन करें, उसकी कहानी सुनें और याद रहने वाली जगहों के साथ अपना दिन बनाएं।',
    begin: 'खोजना शुरू करें',
    how: 'यह कैसे काम करता है',
    scan: 'स्कैन',
    nearby: 'आस-पास',
    plan: 'दिन बनाएं',
    steps: [
      ['स्मारक स्कैन करें', 'कैमरा पत्थर की बनावट की ओर करें।'],
      ['कहानी सुनें', 'अपनी भाषा में स्रोतों वाली कहानी सुनें।'],
      ['अपना दिन बनाएं', 'पसंद आई जगहों के साथ अपनी राह बनाएं।'],
    ],
  },
} as const

export default function Page() {
  const { lang, setLang } = useLang()
  const copy = homeCopy[lang]
  const monument = monuments[0]
  const shortcuts = [
    { href: '/identify', label: copy.scan, position: 'left-2 top-16' },
    { href: '/nearby', label: copy.nearby, position: 'right-0 top-40' },
    { href: '/plan', label: copy.plan, position: 'left-0 bottom-28' },
  ]

  return (
    <LazyMotion features={domAnimation}>
      <main className="shell min-h-svh overflow-hidden pb-20 lg:mx-auto lg:max-w-7xl lg:px-8" lang={lang}>
        <header className="flex items-center justify-between px-5 py-4 lg:hidden">
          <Link className="fraunces flex min-h-12 items-center text-2xl" href="/">Raahein</Link>
          <Toggle lang={lang} setLang={setLang} />
        </header>
        <section className="relative px-5 pb-14 pt-10 lg:grid lg:grid-cols-12 lg:items-center lg:gap-12 lg:px-0 lg:pb-24 lg:pt-20">
          <div className="lg:col-span-5">
            <h1 className="fraunces max-w-[360px] text-5xl leading-[.98] sm:text-6xl lg:max-w-none lg:text-7xl">{copy.heading}</h1>
            <p className="mt-6 max-w-[34rem] text-base leading-7 text-[#5A4E3F] lg:text-lg">{copy.body}</p>
            <Link href="/identify" className="link-inverse mt-9 inline-flex min-h-14 items-center gap-3 rounded-full bg-[#B5452B] px-7 font-semibold shadow-[0_10px_24px_rgba(143,50,33,.28)] transition-transform hover:-translate-y-0.5">
              {copy.begin} <ArrowRight aria-hidden="true" size={18} />
            </Link>
          </div>
          <div className="relative mt-14 flex min-h-[480px] items-center justify-center lg:col-span-7 lg:mt-0 lg:min-h-[620px]">
            <m.div animate={{ opacity: 1 }} className="relative h-[440px] w-[300px] lg:h-[600px] lg:w-[410px]" initial={false} transition={transitions.slow}>
              <ArchImage src={monument.image} alt={monument.name[lang]} className="h-full w-full" />
              <div className="absolute inset-x-0 bottom-7 text-center text-[#FBF6EC] drop-shadow-lg">
                <p className="fraunces text-3xl">{monument.name[lang]}</p>
                <p className="text-sm">{monument.city}</p>
              </div>
            </m.div>
            {shortcuts.map(({ href, label, position }) => (
              <Link key={href} href={href} className={`absolute ${position} float-chip flex min-h-12 items-center rounded-full border border-[#E8A317] bg-[#FBF6EC]/95 px-4 text-sm shadow-lg`}>
                {label}
              </Link>
            ))}
          </div>
        </section>
        <section className="px-5 lg:px-0 lg:py-16">
          <div className="mb-8 flex items-end justify-between">
            <h2 className="fraunces text-4xl">{copy.how}</h2>
            <VineDivider className="hidden max-w-xs lg:block" />
          </div>
          <ol className="grid gap-4 lg:grid-cols-3">
            {copy.steps.map(([title, body], index) => (
              <li className="flex items-stretch gap-3" key={title}>
                <InlayFrame className="flex-1">
                  <div className="min-h-40 bg-[#FBF6EC] p-5">
                    <span className="text-3xl text-[#B5452B]">{index + 1}</span>
                    <h3 className="fraunces mt-3 text-2xl">{title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">{body}</p>
                  </div>
                </InlayFrame>
                {index < 2 && <VineDivider className="hidden w-12 self-center lg:block" />}
              </li>
            ))}
          </ol>
        </section>
        <section aria-label={lang === 'hi' ? 'स्मारक' : 'Monuments'} className="mt-10 px-5 pb-10 lg:mt-16 lg:px-0">
          <div className="flex snap-x gap-4 overflow-x-auto pb-4">
            {monuments.map((item) => (
              <Link href={`/monument/${item.id}`} key={item.id} className="w-56 shrink-0 snap-start rounded-2xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]">
                <InlayFrame>
                  <ArchImage src={item.image} alt={item.name[lang]} className="h-60 w-full" />
                  <p className="bg-[#FBF6EC] p-3 font-semibold">{item.name[lang]}</p>
                </InlayFrame>
              </Link>
            ))}
          </div>
        </section>
        <div className="grid grid-cols-3 gap-2 px-5 lg:hidden">
          {[
            { href: '/identify', icon: Compass, label: copy.scan },
            { href: '/nearby', icon: MapPinned, label: copy.nearby },
            { href: '/plan', icon: Route, label: copy.plan },
          ].map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href} className="card flex min-h-24 flex-col items-center justify-center gap-2 border border-[#D4C3A6] text-center text-sm">
              <Icon aria-hidden="true" className="text-[#B5452B]" size={21} />
              <span>{label}</span>
            </Link>
          ))}
        </div>
      </main>
    </LazyMotion>
  )
}
