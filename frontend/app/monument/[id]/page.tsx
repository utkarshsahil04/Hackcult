import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { MonumentProfile } from '@/components/monument/profile'
import { findMonument, monuments } from '@/lib/catalog'
import { jsonLd, monumentMetadata, monumentSchema } from '@/lib/seo'

type Props = { params: Promise<{ id: string }> }

export const dynamicParams = false
export function generateStaticParams() { return monuments.map((monument) => ({ id: monument.id })) }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const monument = findMonument((await params).id)
  return monument ? monumentMetadata(monument) : { title: 'Monument not found' }
}

export default async function Page({ params }: Props) {
  const { id } = await params
  const monument = findMonument(id)
  if (!monument) notFound()
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: jsonLd(monumentSchema(monument)) }} type="application/ld+json" />
      <MonumentProfile id={id} />
    </>
  )
}
