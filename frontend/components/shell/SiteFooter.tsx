'use client'

import Link from 'next/link'
import { useLang } from '@/components/raahein'
import { monuments } from '@/lib/catalog'

const copy = {
  en: { tagline: 'Stories in stone, found along the way.', explore: 'Explore', delhi: 'Monuments in Delhi', agra: 'Monuments in Agra', scan: 'Identify a monument', all: 'All monuments', plan: 'Plan your day', nearby: 'Nearby monuments', journey: 'My journey', note: 'Every historical fact needs two independent sources. Photos are by Wikimedia Commons contributors and credited on each monument’s page.' },
  hi: { tagline: 'पत्थरों की कहानियां, आपकी राहों के साथ।', explore: 'खोजें', delhi: 'दिल्ली के स्मारक', agra: 'आगरा के स्मारक', scan: 'स्मारक पहचानें', all: 'सभी स्मारक', plan: 'अपना दिन बनाएं', nearby: 'आस-पास के स्मारक', journey: 'मेरी यात्रा', note: 'हर ऐतिहासिक तथ्य के लिए दो स्वतंत्र स्रोत ज़रूरी हैं। तस्वीरें विकिमीडिया कॉमन्स के योगदानकर्ताओं की हैं और हर स्मारक के पृष्ठ पर श्रेय दिया गया है।' },
}

const inAgra = (lat: number) => lat < 28

export function SiteFooter() {
  const { lang } = useLang()
  const text = copy[lang]
  const links = [['/identify', text.scan], ['/explore', text.all], ['/plan', text.plan], ['/nearby', text.nearby], ['/connections', lang === 'hi' ? 'स्मारकों का जाल' : 'Monument network'], ['/digitise', lang === 'hi' ? 'अभिलेख डिजिटल करें' : 'Digitise an archive'], ['/profile', text.journey]]
  const list = (title: string, agra: boolean) => (
    <div>
      <h2 className="fraunces text-lg text-[#E8A317]">{title}</h2>
      <ul className="mt-2 grid gap-x-4 sm:grid-cols-2">
        {monuments.filter((m) => inAgra(m.lat) === agra).map((m) => <li key={m.id}><Link className="footer-link" href={`/monument/${m.id}`}>{m.name[lang]}</Link></li>)}
      </ul>
    </div>
  )
  return (
    <footer className="site-footer jali-bg pb-28 lg:pb-8" lang={lang}>
      <div className="mx-auto grid max-w-7xl gap-8 px-5 pt-14 lg:grid-cols-[1fr_2fr_1fr] lg:px-8">
        <div>
          <p className="fraunces text-3xl text-[#FBF6EC]">{lang === 'hi' ? 'राहें' : 'Raahein'}</p>
          <p className="mt-2 text-sm leading-6 text-[#FBF6EC]/90">{text.tagline}</p>
          <h2 className="fraunces mt-6 text-lg text-[#E8A317]">{text.explore}</h2>
          <ul className="mt-2">{links.map(([href, label]) => <li key={href}><Link className="footer-link" href={href}>{label}</Link></li>)}</ul>
        </div>
        {list(text.delhi, false)}
        {list(text.agra, true)}
      </div>
      <p className="mx-auto mt-8 max-w-7xl border-t border-[#E8A317]/30 px-5 pt-4 text-xs leading-5 text-[#FBF6EC]/85 lg:px-8">{text.note}</p>
    </footer>
  )
}
