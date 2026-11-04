import type { Metadata, Viewport } from 'next'
import { Fraunces, Inter, Noto_Sans_Devanagari } from 'next/font/google'
import './globals.css'
import { AppShell } from '@/components/shell/AppShell'
import { Atmosphere } from '@/components/atmosphere/Atmosphere'
import { imageCredits } from '@/lib/catalog'
import { jsonLd, SITE_DESCRIPTION, SITE_NAME, SITE_URL, siteSchema } from '@/lib/seo'
const fraunces = Fraunces({ subsets: ['latin'], variable: '--font-fraunces' })
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const devanagari = Noto_Sans_Devanagari({ subsets: ['devanagari'], variable: '--font-devanagari' })
const HOME_TITLE = 'Raahein: stories, 3D models and day plans for India’s monuments'
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: HOME_TITLE, template: `%s | ${SITE_NAME}` },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  alternates: { canonical: '/' },
  openGraph: { type: 'website', siteName: SITE_NAME, title: HOME_TITLE, description: SITE_DESCRIPTION, url: '/', locale: 'en_IN', alternateLocale: 'hi_IN', images: [{ url: imageCredits['taj-mahal'].url, alt: 'Taj Mahal, Agra' }] },
  twitter: { card: 'summary_large_image', title: HOME_TITLE, description: SITE_DESCRIPTION, images: [imageCredits['taj-mahal'].url] },
}
export const viewport: Viewport = { themeColor: '#EADBC0', colorScheme: 'light' }
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body className={`${fraunces.variable} ${inter.variable} ${devanagari.variable}`}><script dangerouslySetInnerHTML={{ __html: jsonLd(siteSchema) }} type="application/ld+json" /><Atmosphere /><AppShell>{children}</AppShell></body></html> }
