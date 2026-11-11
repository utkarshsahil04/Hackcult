import type { MetadataRoute } from 'next'
import { monuments } from '@/lib/catalog'
import { SITE_URL } from '@/lib/seo'

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ['/', '/explore', '/identify', '/plan', '/nearby', '/connections', '/digitise', ...monuments.flatMap((m) => [`/monument/${m.id}`, `/monument/${m.id}/related`])]
  return paths.map((path) => ({ url: `${SITE_URL}${path === '/' ? '' : path}` }))
}
