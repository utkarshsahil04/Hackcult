import type { Metadata } from 'next'
import { imageCredits, type Monument } from './catalog'

const host = process.env.NEXT_PUBLIC_SITE_URL ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : 'http://localhost:3000')

export const SITE_URL = host.replace(/\/$/, '')
export const SITE_NAME = 'Raahein'
export const SITE_DESCRIPTION = 'Raahein is a guide to India’s monuments. Identify a monument from a photo, read sourced stories in English and Hindi, explore 3D models and plan a day in Delhi and Agra.'

/** Pages that are private or depend on query parameters, and so should stay out of search results. */
export const noIndex: Metadata = { robots: { index: false, follow: true } }

export const pageMetadata = (title: string, description: string, path: string): Metadata => ({
  title,
  description,
  alternates: { canonical: path },
  openGraph: { title: `${title} | ${SITE_NAME}`, description, url: path },
})

export function monumentDescription(monument: Monument) {
  const text = monument.summary.en || `${monument.name.en} in ${monument.city}. Explore the building in a 3D model, see the monuments near it and add it to a day plan.`
  return text.length <= 155 ? text : `${text.slice(0, text.lastIndexOf(' ', 152))}…`
}

export function monumentMetadata(monument: Monument): Metadata {
  const title = `${monument.name.en}, ${monument.city}: story, 3D model and visit`
  const description = monumentDescription(monument)
  const path = `/monument/${monument.id}`
  const image = imageCredits[monument.id]?.url
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { type: 'article', title, description, url: path, images: image ? [{ url: image, alt: monument.name.en }] : undefined },
    twitter: { card: 'summary_large_image', title, description, images: image ? [image] : undefined },
  }
}

export function monumentSchema(monument: Monument) {
  const url = `${SITE_URL}/monument/${monument.id}`
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': ['TouristAttraction', 'LandmarksOrHistoricalBuildings'],
        '@id': `${url}#monument`,
        name: monument.name.en,
        alternateName: monument.name.hi,
        description: monumentDescription(monument),
        url,
        image: imageCredits[monument.id]?.url,
        geo: { '@type': 'GeoCoordinates', latitude: monument.lat, longitude: monument.lng },
        address: { '@type': 'PostalAddress', addressLocality: monument.city, addressCountry: 'IN' },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Monuments', item: `${SITE_URL}/explore` },
          { '@type': 'ListItem', position: 2, name: monument.name.en, item: url },
        ],
      },
    ],
  }
}

export const siteSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: SITE_NAME,
  alternateName: 'राहें',
  url: SITE_URL,
  description: SITE_DESCRIPTION,
  inLanguage: ['en', 'hi'],
}

/** Safe to place inside a script tag: stops text in the data from closing the tag. */
export const jsonLd = (data: unknown) => JSON.stringify(data).replace(/</g, '\\u003c')
