'use client'

import Link from 'next/link'
import { ArrowRight, ScrollText } from 'lucide-react'
import { useLang } from '@/components/raahein'
import { copy } from '@/lib/archive'

export function ArchiveCard({ className = '' }: { className?: string }) {
  const { lang } = useLang()
  const t = copy[lang]
  return (
    <Link className={`card flex min-h-12 items-center gap-4 border border-[#D4C3A6] p-4 ${className}`} href="/digitise">
      <ScrollText aria-hidden="true" className="shrink-0 text-[#B5452B]" size={28} />
      <span className="min-w-0 flex-1">
        <span className="fraunces block text-lg">{t.title}</span>
        <span className="block text-sm text-[#5A4E3F]">{t.cardBody}</span>
      </span>
      <ArrowRight aria-hidden="true" className="shrink-0" size={18} />
    </Link>
  )
}
