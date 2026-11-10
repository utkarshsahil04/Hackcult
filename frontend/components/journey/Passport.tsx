'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Award, Share2 } from 'lucide-react'
import { useLang } from '@/components/raahein'
import type { Visit } from '@/lib/journey'
import { passportPages, stampDate, stampTilt } from '@/lib/passport'

const cityName = { Delhi: { en: 'Delhi', hi: 'दिल्ली' }, Agra: { en: 'Agra', hi: 'आगरा' } }

export function Passport({ visits }: { visits: Visit[] }) {
  const { lang } = useLang()
  const hi = lang === 'hi'
  const { pages, collected, total } = passportPages(visits)
  const [status, setStatus] = useState('')

  async function share() {
    const names = pages.flatMap((page) => page.stamps.filter((stamp) => stamp.date).map((stamp) => stamp.monument.name[lang]))
    const title = hi ? 'मेरा विरासत पासपोर्ट' : 'My heritage passport'
    const text = hi ? `मैंने राहें पर ${total} में से ${collected} मुहरें जमा की हैं: ${names.join(', ')}` : `I've collected ${collected} of ${total} stamps on Raahein: ${names.join(', ')}`
    try {
      if (navigator.share) await navigator.share({ title, text })
      else {
        await navigator.clipboard.writeText(text)
        setStatus(hi ? 'कॉपी हो गया' : 'Copied to clipboard')
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') setStatus(hi ? 'साझा नहीं हो सका' : 'Could not share')
    }
  }

  return (
    <section aria-labelledby="passport-title" className="rounded-3xl border border-[#E8A317]/50 bg-[#FBF6EC] p-4 sm:p-6" data-testid="passport">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="fraunces text-2xl" id="passport-title">{hi ? 'विरासत पासपोर्ट' : 'Heritage passport'}</h2>
          <p className="mt-1 text-sm text-[#5A4E3F]" data-testid="passport-count">{hi ? `${total} में से ${collected} मुहरें` : `${collected} of ${total} stamps`}</p>
        </div>
        {collected > 0 && (
          <button className="inline-flex min-h-12 items-center gap-2 rounded-full border border-[#B5452B] px-4 text-sm font-semibold text-[#8F3221] hover:bg-[#EADBC0]" onClick={share} type="button"><Share2 aria-hidden="true" size={16} />{hi ? 'मेरा पासपोर्ट साझा करें' : 'Share my passport'}</button>
        )}
      </div>
      <p aria-live="polite" className="text-xs text-[#5A4E3F]">{status}</p>
      {collected === 0 && <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">{hi ? 'हर स्मारक की एक मुहर है। किसी स्मारक के पृष्ठ पर “मैं यहां गया/गई हूं” चुनें और उसकी मुहर यहां लग जाएगी।' : 'Every monument has a stamp. Choose “I’ve been here” on a monument’s page and its stamp is inked here.'}</p>}

      <ul className="mt-3 flex flex-wrap gap-2">
        {pages.map((page) => (
          <li className={`inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-xs font-semibold ${page.complete ? 'bg-[#E8A317] text-[#1F1A14]' : 'border border-dashed border-[#5A4E3F]/40 text-[#5A4E3F]'}`} key={page.region}>
            <Award aria-hidden="true" size={14} />
            {page.complete
              ? (hi ? `${cityName[page.region].hi} पूरा` : `${cityName[page.region].en} complete`)
              : `${cityName[page.region][lang]}: ${hi ? `${page.stamps.length} में से ${page.collected}` : `${page.collected} of ${page.stamps.length}`}`}
          </li>
        ))}
      </ul>

      {pages.map((page) => (
        <div className="mt-5" key={page.region}>
          <h3 className="fraunces text-sm uppercase tracking-[.2em] text-[#8F3221]">{cityName[page.region][lang]}</h3>
          <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {page.stamps.map(({ monument, date }) => {
              const name = monument.name[lang]
              return (
                <li key={monument.id}>
                  <Link
                    aria-label={date ? `${name}, ${hi ? 'मुहर लगी' : 'collected'} ${stampDate(date, lang)}` : `${name}, ${hi ? 'अभी मुहर नहीं लगी' : 'not collected yet'}`}
                    className={`grid aspect-square min-h-12 place-items-center rounded-full p-1.5 text-center ${date ? 'border-4 border-double border-[#B5452B] bg-[#B5452B]/5 text-[#8F3221]' : 'border-2 border-dashed border-[#5A4E3F]/30 text-[#5A4E3F]'}`}
                    href={`/monument/${monument.id}`}
                    style={date ? { transform: `rotate(${stampTilt(monument.id)}deg)` } : undefined}
                  >
                    <span aria-hidden="true" className={`grid size-full content-center justify-items-center gap-1 rounded-full p-2 ${date ? 'border border-[#B5452B]/60' : ''}`}>
                      <span className="text-[10px] font-semibold uppercase tracking-[.15em]">{date ? (hi ? '✦ मुहर ✦' : '✦ Collected ✦') : (hi ? 'अभी नहीं' : 'Not yet')}</span>
                      <span className="fraunces line-clamp-3 break-words text-sm leading-tight">{name}</span>
                      {date && <span className="text-[11px] font-semibold">{stampDate(date, lang, 'short')}</span>}
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </section>
  )
}
