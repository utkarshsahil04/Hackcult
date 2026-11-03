import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { MonumentProfile } from '@/components/monument/profile'
import { findMonument, monuments } from '@/lib/mock'

type Props = { params: Promise<{ id: string }> }

export const dynamicParams = false
export function generateStaticParams() { return monuments.map((monument) => ({ id: monument.id })) }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const monument = findMonument((await params).id)
  return monument ? { title: `${monument.name.en} | Raahein`, description: `Read the sourced story of ${monument.name.en} in ${monument.city}.` } : { title: 'Monument not found | Raahein' }
}

export default async function Page({ params }: Props) { const { id } = await params; if (!findMonument(id)) notFound(); return <MonumentProfile id={id} /> }
