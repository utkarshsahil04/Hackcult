import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { RelatedMonuments } from '@/components/monument/related'
import { findMonument, monuments } from '@/lib/catalog'
import { pageMetadata } from '@/lib/seo'

type Props = { params: Promise<{ id: string }> }

export const dynamicParams = false
export function generateStaticParams() { return monuments.map((monument) => ({ id: monument.id })) }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params
  const monument = findMonument(id)
  return monument ? pageMetadata(`Monuments connected to ${monument.name.en}`, `See the monuments linked to or close to ${monument.name.en} in ${monument.city}, and add them to your day.`, `/monument/${id}/related`) : { title: 'Monument not found' }
}

export default async function Page({ params }: Props) { const { id } = await params; if (!findMonument(id)) notFound(); return <RelatedMonuments id={id} /> }
