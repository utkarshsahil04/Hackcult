'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { LazyMotion, domAnimation, m } from 'framer-motion'
import { ArrowLeft, Check, Plus } from 'lucide-react'
import { InlayFrame, MonumentArt } from '@/components/heritage'
import { Toggle, useLang } from '@/components/raahein'
import { fetchRelated, type ApiRelated } from '@/lib/api'
import { findMonument, getMonument, nearestMonuments } from '@/lib/catalog'
import { transitions } from '@/lib/motion'

const GRAPH_NODES = 6

export function RelatedMonuments({ id }: { id: string }) {
  const monument = getMonument(id)
  const { lang, setLang, t } = useLang()
  const [added, setAdded] = useState<string[]>([])
  const [apiRelated, setApiRelated] = useState<ApiRelated | null>(null)

  // Only sourced monuments have recorded connections; asking for the others is always a 404.
  useEffect(() => {
    if (monument.verified) fetchRelated(id).then(setApiRelated).catch(() => {})
  }, [id, monument.verified])

  // One monument can be linked several ways, so group the records by monument.
  const notes = new Map<string, string>()
  for (const item of apiRelated?.related ?? []) if (!notes.has(item.monument.slug)) notes.set(item.monument.slug, item.note ?? '')
  const connected = [...new Set(notes.size ? notes.keys() : monument.related)].filter((slug) => findMonument(slug))
  const nearby = connected.length ? [] : nearestMonuments(monument, GRAPH_NODES)
  const items = connected.length
    ? connected.map((slug) => ({ id: slug, detail: lang === 'en' && notes.get(slug) ? notes.get(slug)! : t.relatedBody }))
    : nearby.map(({ monument: near, km }) => ({ id: near.id, detail: `${km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`} ${lang === 'hi' ? 'दूर' : 'away'}` }))
  const nodes = items.slice(0, GRAPH_NODES).map((item, index, shown) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / shown.length
    return { ...item, x: 50 + 38 * Math.cos(angle), y: 50 + 38 * Math.sin(angle) }
  })

  function toggleTour(relatedId: string) {
    const name = getMonument(relatedId).name[lang]
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
        <h1 className="fraunces mt-3 break-words text-4xl">{connected.length ? `${t.connected} ${monument.name[lang]}` : `${lang === 'hi' ? `${monument.name.hi} के पास` : `Near ${monument.name.en}`}`}</h1>
        {!connected.length && <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">{lang === 'hi' ? 'इस स्मारक के प्रमाणित संबंध अभी दर्ज नहीं हैं, इसलिए सबसे नज़दीकी स्मारक दिखाए गए हैं।' : 'No sourced connections are recorded for this monument yet, so these are the closest monuments.'}</p>}
        <div className="relative mx-auto my-8 aspect-square w-full max-w-md" data-testid="connection-graph">
          <svg viewBox="0 0 100 100" className="absolute inset-0 size-full" aria-hidden="true">
            {nodes.map((node) => <m.line animate={{ pathLength: 1 }} initial={false} key={node.id} stroke="#E8A317" strokeDasharray="1.4 1.4" strokeWidth=".5" transition={transitions.slow} x1="50" x2={node.x} y1="50" y2={node.y} />)}
          </svg>
          <div className="absolute left-1/2 top-1/2 w-28 -translate-x-1/2 -translate-y-1/2 text-center">
            <MonumentArt alt="" className="mx-auto size-24 rounded-full border-4 border-[#B5452B] shadow-lg" id={monument.id} />
            <p className="fraunces mt-1 rounded-md bg-[#FBF6EC]/85 px-1 text-xs leading-tight text-[#1F1A14]">{monument.name[lang]}</p>
          </div>
          {nodes.map((node) => {
            const related = getMonument(node.id)
            return (
              <Link aria-label={related.name[lang]} className="absolute w-24 -translate-x-1/2 -translate-y-1/2 rounded-xl text-center transition-transform hover:scale-105" href={`/monument/${node.id}`} key={node.id} style={{ left: `${node.x}%`, top: `${node.y}%` }}>
                <MonumentArt alt="" className="mx-auto size-16 rounded-full border-2 border-[#E8A317] shadow-md" id={node.id} />
                <span className="mt-1 block rounded-md bg-[#FBF6EC]/85 px-1 text-[11px] leading-tight text-[#1F1A14]">{related.name[lang]}</span>
              </Link>
            )
          })}
        </div>
        <div className="space-y-3">
          {items.map((item) => {
            const related = getMonument(item.id)
            const isAdded = added.includes(item.id)
            return (
              <InlayFrame key={item.id}>
                <article className="flex items-center gap-3 rounded-[10px] bg-[#FBF6EC] p-3">
                  <Link aria-label={related.name[lang]} className="shrink-0 rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E8A317]" href={`/monument/${item.id}`}>
                    <MonumentArt alt="" className="size-16 rounded-lg" id={item.id} />
                  </Link>
                  <Link className="min-w-0 flex-1 py-2" href={`/monument/${item.id}`}>
                    <h2 className="fraunces break-words text-lg">{related.name[lang]}</h2>
                    <p className="text-sm text-[#5A4E3F]">{item.detail}</p>
                  </Link>
                  <button aria-label={`${isAdded ? (lang === 'hi' ? 'हटाएं' : 'Remove') : (lang === 'hi' ? 'टूर में जोड़ें' : 'Add to tour')} ${related.name[lang]}`} aria-pressed={isAdded} className="grid size-12 shrink-0 place-items-center rounded-full text-[#B5452B]" onClick={() => toggleTour(item.id)} type="button">
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
