import data from './catalog.json'

export type Lang = 'en' | 'hi'
type Text = { en: string; hi: string }
export type StoryParagraph = { heading?: Text; text: Text; isLegend?: boolean; source?: number | null }
export type Source = { title: Text; publisher: Text; url?: string }
export type Monument = { id: string; name: Text; city: string; era: string; style: string; location: string; verified: boolean; summary: Text; image: string; sections: StoryParagraph[]; sources: Source[]; related: string[]; lat: number; lng: number }

export const monumentImages: Record<string, string> = {
  'taj-mahal': 'https://whc.unesco.org/uploads/thumbs/site_0252_0008-1200-630-20250108121530-q70.webp',
  'agra-fort': 'https://whc.unesco.org/uploads/thumbs/site_0251_0010-1200-630-20240807180746-q70.webp',
  'red-fort': 'https://whc.unesco.org/uploads/thumbs/site_0231_0001-1200-630-20110920200330-q70.webp',
  'humayuns-tomb': 'https://whc.unesco.org/uploads/thumbs/site_0232_0005-1200-630-20210425155601-q70.webp',
  'qutb-complex': 'https://whc.unesco.org/uploads/thumbs/site_0233_0001-1200-630-20151104153142-q70.webp',
  'fatehpur-sikri': 'https://whc.unesco.org/uploads/thumbs/site_0255_0001-1200-630-20110920200713-q70.webp',
}

const rank = (id: string) => { const i = Object.keys(monumentImages).indexOf(id); return i < 0 ? 99 : i }
// Generated from the database by backend/tools/export_catalog.py. Photographed monuments come first.
export const monuments: Monument[] = (data as Omit<Monument, 'image'>[])
  .map((m) => ({ ...m, image: monumentImages[m.id] ?? `/monuments/${m.id}.svg` }))
  .sort((a, b) => rank(a.id) - rank(b.id))
export const findMonument = (id: string) => monuments.find((m) => m.id === id)
export const getMonument = (id: string) => findMonument(id) ?? monuments[0]
