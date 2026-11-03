'use client'

import Link from 'next/link'
import { ArrowRight, BookOpen, Clock, Compass, MapPin, MapPinned, Route, ShieldCheck, Sparkles } from 'lucide-react'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Toggle, useLang } from '@/components/raahein'
import { RaaheinLogo } from '@/components/RaaheinLogo'
import { ArchImage, HeritageSimulator, InlayFrame, VineDivider } from '@/components/heritage'
import { monuments } from '@/lib/mock'
import { transitions } from '@/lib/motion'

const homeCopy = {
  en: {
    heading: 'Stories in stone, found along the way.',
    body: 'Scan a monument, hear its story, and build a day around the places that stay with you.',
    begin: 'Begin exploring',
    browseAll: 'Browse all sites',
    how: 'How it works',
    howSub: 'A field companion designed for curiosity, grounded in archival truth.',
    scan: 'Scan',
    nearby: 'Nearby',
    plan: 'Plan a day',
    metrics: [
      { value: '6 Sites', label: 'Agra & Delhi circuits', desc: 'Curated UNESCO & ASI landmarks' },
      { value: '800+ Yrs', label: 'Layered history', desc: 'From 1199 Sultanate to Mughal zenith' },
      { value: 'Bilingual', label: 'Audio & text', desc: 'English & Hindi sourced narratives' },
      { value: '100% Sourced', label: 'Archival claims', desc: 'Verified against ASI publications' },
    ],
    circuitsHeading: 'Curated heritage corridors',
    circuitsSub: 'Explore India’s grandest architectural dialogues connected across time.',
    circuits: [
      {
        title: 'The Agra Imperial Triangle',
        city: 'Agra, Uttar Pradesh',
        era: '1565 – 1648 CE',
        desc: 'White marble inlay, monumental red sandstone fortresses, and Akbar’s utopian capital.',
        stops: ['Taj Mahal', 'Agra Fort', 'Fatehpur Sikri'],
        href: '/plan/route?hours=6&mode=auto',
      },
      {
        title: 'The Delhi Sultanate & Mughal Axis',
        city: 'Delhi NCR',
        era: '1199 – 1639 CE',
        desc: 'From the fluted 73-meter minaret to India’s first charbagh garden tomb and the Red Fort.',
        stops: ['Qutub Minar', 'Humayun’s Tomb', 'Red Fort'],
        href: '/plan/route?hours=6&mode=auto',
      },
    ],
    monumentsHeading: 'Explore the monuments',
    monumentsSub: 'Every monument holds a documented history and living legend.',
    readStory: 'Read manuscript',
    steps: [
      [
        'Scan a monument',
        'Point your camera at any facade, archway, or minaret for instant computer vision recognition.',
        'Computer Vision',
      ],
      [
        'Hear the story',
        'Immerse yourself in oral storytelling with clearly distinguished historical facts and legends.',
        'Oral Manuscript',
      ],
      [
        'Build your day',
        'Solve an optimal multi-stop itinerary with calibrated travel times and offline routing.',
        'Smart Transit',
      ],
    ],
  },
  hi: {
    heading: 'पत्थरों की कहानियां, आपकी राहों के साथ।',
    body: 'स्मारक को स्कैन करें, उसकी कहानी सुनें और याद रहने वाली जगहों के साथ अपना दिन बनाएं।',
    begin: 'खोजना शुरू करें',
    browseAll: 'सभी स्मारक देखें',
    how: 'यह कैसे काम करता है',
    howSub: 'जिज्ञासा के लिए बना और ऐतिहासिक प्रमाणों पर आधारित साथी।',
    scan: 'स्कैन',
    nearby: 'आस-पास',
    plan: 'दिन बनाएं',
    metrics: [
      { value: '६ धरोहरें', label: 'आगरा व दिल्ली', desc: 'यूनेस्को और एएसआई संरक्षित स्थल' },
      { value: '८००+ वर्ष', label: 'इतिहास की परतें', desc: '११९९ सल्तनत से मुगल काल तक' },
      { value: 'द्विभाषी', label: 'ऑडियो व लिपि', desc: 'हिंदी और अंग्रेजी में प्रमाणित कथाएं' },
      { value: '१००% प्रमाणित', label: 'ऐतिहासिक स्रोत', desc: 'एएसआई दस्तावेजों से सत्यापित' },
    ],
    circuitsHeading: 'विशेष ऐतिहासिक मार्ग',
    circuitsSub: 'समय की धारा में जुड़े भारत के भव्य वास्तुकला संवाद को जानें।',
    circuits: [
      {
        title: 'आगरा शाही त्रिकोण',
        city: 'आगरा, उत्तर प्रदेश',
        era: '१५६५ – १६४८ ईस्वी',
        desc: 'सफेद संगमरमर की पच्चीकारी, लाल बलुआ पत्थर के दुर्ग और अकबर की राजधानी।',
        stops: ['ताजमहल', 'आगरा किला', 'फतेहपुर सीकरी'],
        href: '/plan/route?hours=6&mode=auto',
      },
      {
        title: 'दिल्ली सल्तनत व मुगल अक्ष',
        city: 'दिल्ली',
        era: '११९९ – १६३९ ईस्वी',
        desc: '७३ मीटर ऊंची मीनार से लेकर पहले चारबाग मकबरे और लाल किले तक का सफर।',
        stops: ['क़ुतुब मीनार', 'हुमायूँ का मकबरा', 'लाल किला'],
        href: '/plan/route?hours=6&mode=auto',
      },
    ],
    monumentsHeading: 'स्मारकों की खोज करें',
    monumentsSub: 'हर इमारत में दर्ज इतिहास और लोक कथाएं मौजूद हैं।',
    readStory: 'पांडुलिपि पढ़ें',
    steps: [
      [
        'स्मारक स्कैन करें',
        'गुम्बद, मेहराब या मीनार की ओर कैमरा करें और त्वरित दृश्य पहचान पाएं।',
        'कंप्यूटर विजन',
      ],
      [
        'कहानी सुनें',
        'तथ्य और लोकश्रुति के स्पष्ट अंतर के साथ प्रामाणिक मौखिक कथा सुनें।',
        'मौखिक पांडुलिपि',
      ],
      [
        'अपना दिन बनाएं',
        'सटीक यात्रा समय और बिना हड़बड़ाहट के अपना दिन व्यवस्थित करें।',
        'सुगम मार्ग',
      ],
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
      <main className="shell min-h-svh overflow-hidden pb-24 lg:mx-auto lg:max-w-7xl lg:px-8" lang={lang}>
        {/* Mobile Header */}
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-[#E8A317]/20 bg-[#EADBC0]/95 px-5 py-2.5 backdrop-blur lg:hidden safe-top">
          <Link className="flex min-h-12 items-center" href="/" aria-label={lang === 'hi' ? 'राहें' : 'Raahein'}>
            <RaaheinLogo className="h-9 w-24" />
          </Link>
          <Toggle lang={lang} setLang={setLang} />
        </header>

        {/* Hero Section */}
        <section className="relative px-5 pb-14 pt-8 lg:grid lg:grid-cols-12 lg:items-center lg:gap-12 lg:px-0 lg:pb-20 lg:pt-16">
          <div className="lg:col-span-5">
            <span className="inline-flex items-center gap-2 rounded-full border border-[#E8A317] bg-[#FBF6EC]/90 px-4 py-1.5 text-xs font-semibold text-[#8F3221] shadow-sm backdrop-blur">
              <Sparkles size={14} className="text-[#E8A317] animate-pulse" aria-hidden="true" />
              {lang === 'hi' ? 'भारतीय सांस्कृतिक धरोहर यात्रा' : 'Indian Cultural Heritage Tour'}
            </span>
            <h1 className="fraunces mt-4 max-w-[360px] text-5xl leading-[.98] sm:text-6xl lg:max-w-none lg:text-7xl">
              {copy.heading}
            </h1>
            <p className="mt-6 max-w-[34rem] text-base leading-7 text-[#5A4E3F] lg:text-lg">
              {copy.body}
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                href="/identify"
                className="link-inverse inline-flex min-h-14 items-center gap-3 rounded-full bg-[#B5452B] px-7 font-semibold shadow-[0_10px_24px_rgba(143,50,33,.28)] transition-transform hover:-translate-y-0.5"
              >
                {copy.begin} <ArrowRight aria-hidden="true" size={18} />
              </Link>
              <Link
                href="/explore"
                className="inline-flex min-h-14 items-center gap-2 rounded-full border border-[#B5452B]/35 bg-[#FBF6EC]/90 px-6 text-sm font-semibold text-[#1F1A14] backdrop-blur transition-colors hover:border-[#B5452B]"
              >
                {copy.browseAll}
              </Link>
            </div>
          </div>

          <div className="relative mt-14 flex min-h-[460px] items-center justify-center lg:col-span-7 lg:mt-0 lg:min-h-[580px]">
            {/* Animated Indian Cultural Mandala Aura */}
            <div className="pointer-events-none absolute -inset-6 sm:-inset-10 flex items-center justify-center overflow-visible" aria-hidden="true">
              <m.div
                animate={{ rotate: 360 }}
                transition={{ duration: 140, repeat: Infinity, ease: 'linear' }}
                className="absolute size-[350px] sm:size-[440px] lg:size-[560px] rounded-full border-2 border-dashed border-[#E8A317]/55 opacity-75"
              />
              <m.div
                animate={{ rotate: -360 }}
                transition={{ duration: 200, repeat: Infinity, ease: 'linear' }}
                className="absolute size-[410px] sm:size-[500px] lg:size-[640px] rounded-full border border-[#B5452B]/35 opacity-60"
              />
              <div className="absolute size-[300px] sm:size-[380px] rounded-full bg-radial from-[#E8A317]/25 via-[#E8A317]/10 to-transparent blur-2xl" />
            </div>

            <m.div
              animate={{ opacity: 1 }}
              className="relative h-[430px] w-[290px] lg:h-[560px] lg:w-[390px]"
              initial={false}
              transition={transitions.slow}
            >
              <ArchImage src={monument.image} alt={monument.name[lang]} className="h-full w-full shadow-2xl" />
              <div className="absolute inset-x-0 bottom-7 px-4 text-center text-[#FBF6EC] drop-shadow-lg">
                <p className="fraunces text-3xl">{monument.name[lang]}</p>
                <p className="text-sm text-[#FBF6EC]/90">{monument.city} · {monument.yearBuilt} CE · {monument.builder}</p>
              </div>
            </m.div>
            {shortcuts.map(({ href, label, position }) => (
              <Link
                key={href}
                href={href}
                className={`absolute ${position} float-chip flex min-h-12 items-center gap-1.5 rounded-full border border-[#E8A317] bg-[#FBF6EC]/95 px-4 text-sm font-medium shadow-lg backdrop-blur`}
              >
                {label}
              </Link>
            ))}
          </div>
        </section>

        {/* Heritage Metrics Ribbon */}
        <section aria-label={lang === 'hi' ? 'धरोहर सांख्यिकी' : 'Heritage Metrics'} className="px-5 py-6 lg:px-0 lg:py-10">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-5">
            {copy.metrics.map((item, index) => (
              <InlayFrame key={index} className="h-full">
                <div className="flex h-full flex-col justify-between rounded-[10px] bg-[#FBF6EC] p-4 lg:p-5">
                  <div className="fraunces text-2xl text-[#B5452B] lg:text-3xl">{item.value}</div>
                  <div className="mt-2">
                    <div className="text-sm font-semibold text-[#1F1A14]">{item.label}</div>
                    <div className="mt-0.5 text-xs text-[#5A4E3F]">{item.desc}</div>
                  </div>
                </div>
              </InlayFrame>
            ))}
          </div>
        </section>

        {/* Interactive Architectural & Solar Simulator */}
        <HeritageSimulator lang={lang} />

        {/* Curated Corridors */}
        <section aria-labelledby="corridors-heading" className="px-5 py-8 lg:px-0 lg:py-14">
          <div className="mb-8 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <h2 id="corridors-heading" className="fraunces text-3xl lg:text-4xl">{copy.circuitsHeading}</h2>
              <p className="mt-2 text-sm text-[#5A4E3F] lg:text-base">{copy.circuitsSub}</p>
            </div>
            <Link href="/plan" className="inline-flex min-h-10 items-center text-sm font-semibold text-[#B5452B] hover:underline">
              {copy.plan} <ArrowRight size={16} className="ml-1" aria-hidden="true" />
            </Link>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {copy.circuits.map((circuit, index) => (
              <InlayFrame key={index} className="h-full">
                <div className="flex h-full flex-col justify-between rounded-[10px] bg-[#FBF6EC] p-6">
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-[#B5452B]">
                        <MapPin size={13} aria-hidden="true" /> {circuit.city}
                      </span>
                      <span className="rounded-full bg-[#EADBC0]/70 px-2.5 py-0.5 text-xs text-[#5A4E3F]">
                        {circuit.era}
                      </span>
                    </div>
                    <h3 className="fraunces mt-3 text-2xl text-[#1F1A14]">{circuit.title}</h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-[#5A4E3F]">{circuit.desc}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {circuit.stops.map((stop) => (
                        <span key={stop} className="rounded-lg border border-[#E8A317]/40 bg-[#EADBC0]/40 px-2.5 py-1 text-xs font-medium text-[#1F1A14]">
                          {stop}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-6 pt-4 border-t border-[#E8A317]/20 flex items-center justify-between">
                    <span className="text-xs text-[#5A4E3F] flex items-center gap-1.5">
                      <Clock size={14} aria-hidden="true" /> ~6 hours curated tour
                    </span>
                    <Link
                      href={circuit.href}
                      className="inline-flex min-h-10 items-center text-xs font-semibold text-[#B5452B] hover:text-[#8F3221]"
                    >
                      {lang === 'hi' ? 'मार्ग देखें' : 'View itinerary'} <ArrowRight size={14} className="ml-1" aria-hidden="true" />
                    </Link>
                  </div>
                </div>
              </InlayFrame>
            ))}
          </div>
        </section>

        {/* How It Works */}
        <section aria-labelledby="how-heading" className="px-5 py-8 lg:px-0 lg:py-16">
          <div className="mb-8 flex items-end justify-between">
            <h2 id="how-heading" className="fraunces text-3xl lg:text-4xl">{copy.how}</h2>
            <VineDivider className="hidden max-w-xs lg:block" />
          </div>
          <ol className="grid gap-4 lg:grid-cols-3 lg:gap-20">
            {copy.steps.map(([title, body, tag], index) => (
              <li className="relative flex min-w-0 items-stretch" key={title}>
                <InlayFrame className="h-full w-full">
                  <div className="flex h-full min-h-44 flex-col justify-between rounded-[10px] bg-[#FBF6EC] p-5">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="fraunces text-3xl text-[#B5452B]">0{index + 1}</span>
                        <span className="rounded-full border border-[#E8A317]/40 bg-[#EADBC0]/50 px-2.5 py-0.5 text-[11px] font-semibold text-[#8F3221]">
                          {tag}
                        </span>
                      </div>
                      <h3 className="fraunces mt-3 text-2xl text-[#1F1A14]">{title}</h3>
                      <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">{body}</p>
                    </div>
                  </div>
                </InlayFrame>
                {index < 2 && (
                  <div className="absolute left-full top-1/2 hidden w-20 -translate-y-1/2 px-3 lg:block">
                    <VineDivider />
                  </div>
                )}
              </li>
            ))}
          </ol>
        </section>

        {/* Monuments Showcase */}
        <section aria-labelledby="monuments-heading" className="px-5 py-8 lg:px-0 lg:py-14">
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h2 id="monuments-heading" className="fraunces text-3xl lg:text-4xl">{copy.monumentsHeading}</h2>
              <p className="mt-2 text-sm text-[#5A4E3F]">{copy.monumentsSub}</p>
            </div>
            <Link href="/explore" className="link-primary flex min-h-12 items-center text-sm font-semibold">
              {copy.browseAll} <ArrowRight size={16} className="ml-1" aria-hidden="true" />
            </Link>
          </div>

          <div className="flex snap-x gap-5 overflow-x-auto pb-4">
            {monuments.map((item) => (
              <Link
                href={`/monument/${item.id}`}
                key={item.id}
                className="w-72 shrink-0 snap-start rounded-2xl focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]"
              >
                <InlayFrame className="h-full">
                  <div className="flex h-full flex-col justify-between rounded-[10px] bg-[#FBF6EC] p-3">
                    <div>
                      <ArchImage src={item.image} alt={item.name[lang]} className="h-56 w-full" />
                      <div className="p-3">
                        <div className="flex items-center justify-between text-xs text-[#5A4E3F]">
                          <span className="font-semibold text-[#8F3221]">{item.city}</span>
                          <span>{item.yearBuilt} CE</span>
                        </div>
                        <h3 className="fraunces mt-1.5 text-xl text-[#1F1A14]">{item.name[lang]}</h3>
                        <p className="mt-1 text-xs text-[#5A4E3F]">
                          {lang === 'hi' ? `निर्माता: ${item.builder}` : `Commissioned by ${item.builder}`}
                        </p>
                        <p className="mt-2 line-clamp-2 text-xs leading-5 text-[#5A4E3F]">
                          {item.sections[0]?.text[lang]}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 border-t border-[#E8A317]/25 px-3 py-2 flex items-center justify-between text-[11px] font-semibold text-[#B5452B]">
                      <span className="flex items-center gap-1 text-[#5A4E3F]">
                        <ShieldCheck size={13} className="text-[#E8A317]" aria-hidden="true" />
                        {item.sources.length} {lang === 'hi' ? 'स्रोत' : 'sources'}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <BookOpen size={13} aria-hidden="true" />
                        {copy.readStory}
                      </span>
                    </div>
                  </div>
                </InlayFrame>
              </Link>
            ))}
          </div>
        </section>

        {/* Mobile quick actions */}
        <div className="grid grid-cols-3 gap-2 px-5 lg:hidden">
          {[
            { href: '/identify', icon: Compass, label: copy.scan },
            { href: '/nearby', icon: MapPinned, label: copy.nearby },
            { href: '/plan', icon: Route, label: copy.plan },
          ].map(({ href, icon: Icon, label }) => (
            <Link
              key={href}
              href={href}
              className="card flex min-h-24 flex-col items-center justify-center gap-2 border border-[#D4C3A6] text-center text-sm"
            >
              <Icon aria-hidden="true" className="text-[#B5452B]" size={21} />
              <span>{label}</span>
            </Link>
          ))}
        </div>
      </main>
    </LazyMotion>
  )
}
