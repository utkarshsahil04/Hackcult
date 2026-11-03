'use client'

import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { m } from 'framer-motion'
import { ArchImage, InlayFrame } from '@/components/heritage'
import { monuments, type Lang } from '@/lib/catalog'
import { transitions } from '@/lib/motion'

const copy = {
  en: {
    heading: 'Point, snap, discover.',
    body: 'Bring a monument into focus. Raahein will open the path behind its walls.',
    drop: 'Drop a photo here',
    choice: 'or choose one from your device',
    upload: 'Upload a photo',
    phone: 'Open on your phone to scan live',
    steps: ['Point at the monument', 'Snap when the arch is clear', 'Hear the story in your language'],
  },
  hi: {
    heading: 'देखें, तस्वीर लें, जानें।',
    body: 'स्मारक को फ्रेम में लाएं। राहें आपको उसकी दीवारों के पीछे की कहानी तक ले जाएगा।',
    drop: 'तस्वीर यहां छोड़ें',
    choice: 'या अपने डिवाइस से चुनें',
    upload: 'तस्वीर अपलोड करें',
    phone: 'लाइव स्कैन के लिए फोन पर खोलें',
    steps: ['कैमरा स्मारक की ओर करें', 'मेहराब साफ दिखे तो तस्वीर लें', 'अपनी भाषा में कहानी सुनें'],
  },
} as const

export function DesktopIdentify({ state, lang, onUpload }: { state: string; lang: Lang; onUpload: (file: File) => void }) {
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const t = copy[lang]
  if (state !== 'scan') return null

  return (
    <main className="shell hidden min-h-[calc(100svh-72px)] gap-16 px-8 py-16 lg:grid lg:max-w-7xl lg:grid-cols-12 lg:mx-auto" lang={lang}>
      <section className="col-span-7 flex flex-col justify-center">
        <h1 className="fraunces max-w-2xl text-7xl leading-[.94]">{t.heading}</h1>
        <p className="mt-6 max-w-xl text-lg leading-8 text-[#5A4E3F]">{t.body}</p>
        <div
          className={`relative mt-10 flex min-h-[340px] max-w-2xl items-center justify-center overflow-hidden rounded-t-[48%] border-2 border-dashed transition-shadow ${dragging ? 'border-[#B5452B] shadow-[0_12px_36px_rgba(232,163,23,.28)]' : 'border-[#E8A317]'}`}
          onDragLeave={() => setDragging(false)}
          onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            const file = event.dataTransfer.files[0]
            if (file) onUpload(file)
          }}
        >
          <div className="absolute inset-0 opacity-35"><ArchImage src={monuments[0].image} alt="" className="h-full w-full" /></div>
          <div className="relative z-10 text-center">
            <Upload aria-hidden="true" className="mx-auto mb-3 text-[#B5452B]" size={32} />
            <p className="font-[var(--font-fraunces)] text-2xl">{t.drop}</p>
            <p className="mt-2 text-sm text-[#5A4E3F]">{t.choice}</p>
            <button className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-5 font-semibold text-[#FBF6EC] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]" onClick={() => input.current?.click()} type="button">
              <Upload aria-hidden="true" size={17} /> {t.upload}
            </button>
            <input ref={input} type="file" accept="image/*" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) onUpload(file) }} />
          </div>
        </div>
      </section>
      <aside className="col-span-5 flex items-center">
        <InlayFrame className="w-full">
          <div className="bg-[#FBF6EC] p-10 text-center">
            <h2 className="fraunces text-3xl">{t.phone}</h2>
            <div className="mx-auto my-8 flex size-56 items-center justify-center rounded-2xl bg-white p-4">
              <QRCodeSVG value="https://raahein.app/identify" size={184} includeMargin />
            </div>
            <ol className="space-y-4 text-left">
              {t.steps.map((step, index) => (
                <m.li animate={{ opacity: 1, x: 0 }} className="flex items-center gap-3" initial={false} key={step} transition={{ ...transitions.base, delay: index * .08 }}>
                  <span className="grid size-8 place-items-center rounded-full bg-[#E8A317] text-sm font-bold">{index + 1}</span>
                  <span>{step}</span>
                </m.li>
              ))}
            </ol>
          </div>
        </InlayFrame>
      </aside>
    </main>
  )
}
