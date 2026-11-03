import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Raahein',
    short_name: 'Raahein',
    description: 'Discover the stories behind India’s monuments.',
    start_url: '/identify',
    display: 'standalone',
    background_color: '#EADBC0',
    theme_color: '#EADBC0',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }],
  }
}
