'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { ArrowLeft, Check, Plus } from 'lucide-react'
import { InlayFrame, MonumentArt } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { fetchRelated, type ApiRelated } from '@/lib/api'
import { getMonument } from '@/lib/mock'
import { transitions } from '@/lib/motion'

const nodes = [[160, 90], [70, 40], [250, 40], [70, 140], [250, 140]] as const

export function RelatedMonuments({ id }: { id: string }) {
  const monument = getMonument(id)
  const { lang, setLang, t } = useLang()
  const [added, setAdded] = useState<string[]>([])
  const [apiRelated, setApiRelated] = useState<ApiRelated | null>(null)

  useEffect(() => {
    fetchRelated(id).then(setApiRelated).catch(() => {})
  }, [id])

  const relatedIds = (apiRelated?.related && apiRelated.related.length > 0)
    ? apiRelated.related.map((r) => r.monument.slug)
    : monument.related

  function toggleTour(relatedId: string) {
    const related = getMonument(relatedId)
    const name = related ? related.name[lang] : relatedId
    const isAdded = added.includes(relatedId)
    setAdded((current) => isAdded ? current.filter((item) => item !== relatedId) : [...current, relatedId])
    window.dispatchEvent(new CustomEvent('raahein-tour', { detail: isAdded ? { remove: relatedId } : { add: { id: relatedId, name } } }))
  }

  return (
    <LazyMotion features={domAnimation}>
      <main className="shell mx-auto max-w-2xl px-5 pb-12 pt-4 lg:pt-10" lang={lang}>
        <header className="mb-5 flex items-center justify-between lg:hidden">
          <Link href={`/monument/${id}`} className="grid size-12 place-items-center rounded-full" aria-label={`${t.back} ${monument.name[lang]}`}><ArrowLeft aria-hidden="true" /></Link>
          <Toggle lang={lang} setLang={setLang} />
        </header>
        <Link href={`/monument/${id}`} className="link-primary hidden min-h-12 items-center gap-2 text-sm lg:inline-flex"><ArrowLeft aria-hidden="true" size={18} />{t.back} {monument.name[lang]}</Link>
        <h1 className="mt-3 break-words font-[var(--font-fraunces)] text-4xl">{t.connected} {monument.name[lang]}</h1>
        <svg viewBox="0 0 320 180" className="my-8 w-full overflow-visible" aria-label={lang === 'hi' ? 'संबंधित स्मारकों का आरेख' : 'Connected monuments diagram'} role="img">
          <m.path d="M160 90 70 40M160 90 250 40M160 90 70 140M160 90 250 140" stroke="#E8A317" strokeWidth="2" strokeDasharray="5 5" fill="none" initial={false} animate={{ pathLength: 1 }} transition={transitions.slow} />
          {nodes.map(([x, y], index) => <m.g key={`${x}-${y}`} initial={false} animate={{ scale: 1 }} transition={{ ...transitions.base, delay: index * .06 }}><path d={`M${x - 14} ${y + 12}V${y - 2}q0-14 14-14t14 14v14Z`} fill={index === 0 ? '#B5452B' : '#FBF6EC'} stroke="#E8A317" strokeWidth="2" /></m.g>)}
        </svg>
        <div className="space-y-3">
          {relatedIds.map((relatedId, index) => {
            const related = getMonument(relatedId) ?? { id: relatedId, name: { en: relatedId, hi: relatedId }, city: '' }
            const isAdded = added.includes(relatedId)
            return (
              <InlayFrame key={related.id}>
                <article className="flex items-center gap-3 rounded-[10px] bg-[#FBF6EC] p-3">
                  <Link aria-label={related.name[lang]} className="shrink-0 rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]" href={`/monument/${related.id}`}>
                    <MonumentArt alt="" className="size-16 rounded-lg" id={related.id} />
                  </Link>
                  <Link className="min-w-0 flex-1 py-2" href={`/monument/${related.id}`}>
                    <h2 className="break-words font-[var(--font-fraunces)] text-lg">{related.name[lang]}</h2>
                    <p className="text-sm text-[#5A4E3F]">{index ? t.relatedBody : lang === 'hi' ? 'शिल्प और स्थान से जुड़ा।' : 'Connected by craft and place.'}</p>
                  </Link>
                  <button aria-label={`${isAdded ? (lang === 'hi' ? 'हटाएं' : 'Remove') : (lang === 'hi' ? 'टूर में जोड़ें' : 'Add to tour')} ${related.name[lang]}`} aria-pressed={isAdded} className="grid size-12 shrink-0 place-items-center rounded-full text-[#B5452B]" onClick={() => toggleTour(relatedId)} type="button">
                    {isAdded ? <Check aria-hidden="true" /> : <Plus aria-hidden="true" />}
                  </button>
                </article>
              </InlayFrame>
            )
          })}
        </div>
      </main>
    </LazyMotion>
  )
}
