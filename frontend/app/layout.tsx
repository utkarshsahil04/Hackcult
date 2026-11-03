import type { Metadata, Viewport } from 'next'
import { Fraunces, Inter, Noto_Sans_Devanagari } from 'next/font/google'
import './globals.css'
import { AppShell } from '@/components/shell/AppShell'
import { Atmosphere } from '@/components/atmosphere/Atmosphere'
const fraunces = Fraunces({ subsets: ['latin'], variable: '--font-fraunces' })
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const devanagari = Noto_Sans_Devanagari({ subsets: ['devanagari'], variable: '--font-devanagari' })
export const metadata: Metadata = { title: 'Raahein — Stories in stone', description: 'Discover India’s monuments through sourced stories.' }
export const viewport: Viewport = { themeColor: '#EADBC0', colorScheme: 'light' }
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en"><body className={`${fraunces.variable} ${inter.variable} ${devanagari.variable}`}><Atmosphere /><AppShell>{children}</AppShell></body></html> }
