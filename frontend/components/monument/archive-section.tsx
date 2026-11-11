'use client'

import { useEffect, useState } from 'react'
import { copy, fetchMonumentArchive, imageSrc, type ArchiveItem } from '@/lib/archive'
import type { Lang } from '@/lib/catalog'

/** Reviewed archive documents. Styled apart from the two-publisher facts, and absent when there are none. */
export function ArchiveSection({ id, lang }: { id: string; lang: Lang }) {
  const [items, setItems] = useState<ArchiveItem[]>([])
  const t = copy[lang]
  useEffect(() => { void fetchMonumentArchive(id).then(setItems) }, [id])
  if (!items.length) return null
  return (
    <section data-testid="archive-section">
      <h2 className="fraunces text-2xl">{t.archive}</h2>
      <p className="mt-1 text-sm text-[#5A4E3F]">{t.archiveNote}</p>
      <ul className="mt-3 space-y-3">
        {items.map((item) => (
          <li className="rounded-xl border border-dashed border-[#E8A317] bg-[#EADBC0]/40 p-4" key={item.id}>
            {/* eslint-disable-next-line @next/next/no-img-element -- served by the API, not the Next.js optimizer */}
            <img alt="" className="mb-3 max-h-48 w-full rounded-lg object-contain" src={imageSrc(item)} />
            {item.transcription && <p className="mb-3 whitespace-pre-wrap text-base leading-7" dir="auto">{item.transcription}</p>}
            <ul className="space-y-2">
              {item.claims.map((c) => <li className="text-[15px] leading-[1.7]" key={c.id}>{c.text}</li>)}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  )
}
