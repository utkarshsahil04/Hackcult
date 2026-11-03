import { notFound } from 'next/navigation'
import { RelatedMonuments } from '@/components/monument/related'
import { findMonument, monuments } from '@/lib/catalog'

export const dynamicParams = false
export function generateStaticParams() { return monuments.map((monument) => ({ id: monument.id })) }

export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; if (!findMonument(id)) notFound(); return <RelatedMonuments id={id} /> }
