/** Archive digitising: API calls, shared copy and the freely licensed sample scans. */

import type { Lang } from './catalog'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

export type ArchiveClaim = { id: number; text: string; evidence_quote: string; status: 'draft' | 'approved' | 'rejected' }
export type ArchiveItem = {
  id: number; monument_slug: string | null; rights: string; source_note: string | null
  script: string; language: string; transcription: string; translation_en: string
  status: 'draft' | 'reviewed'; image_url: string; claims: ArchiveClaim[]
}

export const RIGHTS = ['own-photo', 'public-domain', 'cc-by', 'cc-by-sa'] as const
export type Rights = (typeof RIGHTS)[number]

export const imageSrc = (item: ArchiveItem) => `${BASE}${item.image_url}`

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try { res = await fetch(`${BASE}${path}`, init) } catch { throw new Error('network') }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${res.status}`), { status: res.status })
  return body as T
}

export function digitise(photo: Blob, rights: Rights, monument: string, name = 'scan.jpg') {
  const body = new FormData()
  body.append('photo', photo, name)
  body.append('rights', rights)
  if (monument) body.append('monument_slug', monument)
  return call<ArchiveItem>('/api/archive/digitise', { method: 'POST', body })
}

export const listDrafts = () => call<{ items: ArchiveItem[] }>('/api/archive/items?status=draft').then((r) => r.items)

export const reviewItem = (id: number, token: string, claims: Array<{ id: number; decision: 'approve' | 'reject'; text?: string }>, monument_slug?: string) =>
  call<ArchiveItem>(`/api/archive/items/${id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Review-Token': token },
    body: JSON.stringify({ claims, monument_slug: monument_slug || undefined }),
  })

/** A failing archive must never break the profile page, so any failure is an empty list. */
export const fetchMonumentArchive = (slug: string) =>
  BASE ? call<{ items: ArchiveItem[] }>(`/api/monuments/${slug}/archive`).then((r) => r.items).catch(() => [] as ArchiveItem[]) : Promise.resolve([] as ArchiveItem[])

const THUMB = 'https://upload.wikimedia.org/wikipedia/commons/thumb'
export const SAMPLES: Array<{ id: string; url: string; rights: Rights; monument: string; credit: { author: string; licence: string; page: string }; title: Record<Lang, string> }> = [
  {
    id: 'topra', rights: 'public-domain', monument: 'feroz-shah-kotla',
    url: `${THUMB}/2/24/Delhi-Topra_pillar_Ashoka_inscriptions.jpg/1280px-Delhi-Topra_pillar_Ashoka_inscriptions.jpg`,
    credit: { author: 'Eugen Hultzsch', licence: 'Public domain', page: 'https://commons.wikimedia.org/wiki/File:Delhi-Topra_pillar_Ashoka_inscriptions.jpg' },
    title: { en: 'Ashoka pillar edict, Feroz Shah Kotla', hi: 'अशोक स्तंभ लेख, फ़िरोज़ शाह कोटला' },
  },
  {
    id: 'iron-pillar', rights: 'public-domain', monument: 'qutb-complex',
    url: `${THUMB}/2/2d/4th_to_5th_century_Sanskrit_inscription_of_Chandra%2C_iron_pillar_at_Qutb_complex_Mehrauli%2C_Delhi.jpg/1280px-4th_to_5th_century_Sanskrit_inscription_of_Chandra%2C_iron_pillar_at_Qutb_complex_Mehrauli%2C_Delhi.jpg`,
    credit: { author: 'Ms Sarah Welch', licence: 'CC0', page: 'https://commons.wikimedia.org/wiki/File:4th_to_5th_century_Sanskrit_inscription_of_Chandra,_iron_pillar_at_Qutb_complex_Mehrauli,_Delhi.jpg' },
    title: { en: 'Iron Pillar inscription, Qutb complex', hi: 'लौह स्तंभ लेख, कुतुब परिसर' },
  },
  {
    id: 'qutb-arabic', rights: 'public-domain', monument: 'qutb-complex',
    url: 'https://upload.wikimedia.org/wikipedia/commons/e/ed/Arabic_words_carved_into_the_Qutb_Minar.jpg',
    credit: { author: 'Aten2005', licence: 'Public domain', page: 'https://commons.wikimedia.org/wiki/File:Arabic_words_carved_into_the_Qutb_Minar.jpg' },
    title: { en: 'Arabic inscription band, Qutb Minar', hi: 'अरबी लेख पट्टी, कुतुब मीनार' },
  },
]

export const copy = {
  en: {
    title: 'Digitise an archive', intro: 'Turn a photo of an inscription, plaque or manuscript into a searchable record that a reviewer checks.',
    photo: 'Photo of the document', camera: 'Take or choose a photo', rights: 'Who may share this photo?', choose: 'Choose…', monument: 'Monument (optional)', none: 'Not sure',
    submit: 'Digitise', reading: 'Reading the document…', samples: 'Try a sample', samplesNote: 'Free images from Wikimedia Commons.', credit: 'Credit',
    'own-photo': 'I took it myself', 'public-domain': 'Public domain', 'cc-by': 'CC BY', 'cc-by-sa': 'CC BY-SA',
    draft: 'Draft: waiting for review', original: 'Original text', english: 'English translation', claims: 'Draft claims', evidence: 'Evidence', unreadable: 'The text could not be read reliably, so nothing is guessed.',
    noClaims: 'No claim could be tied to the text.', again: 'Digitise another', review: 'Reviewer page',
    errNeedRights: 'Choose who may share this photo.', errNeedPhoto: 'Choose a photo first.', errTooBig: 'Choose an image smaller than 6 MB.', errType: 'Choose a JPEG, PNG or WebP image.', errFail: 'We could not read this document right now. Please try again.', errSample: 'The sample could not be loaded. Please try again.',
    cardBody: 'Photograph an old inscription or plaque. A reviewer checks it before visitors see it.',
    archive: 'From the archive', archiveNote: 'From an archive document, reviewed by a curator',
    rTitle: 'Review drafts', rToken: 'Reviewer token', rLoad: 'Load drafts', rNone: 'No drafts are waiting.', approve: 'Approve', reject: 'Reject', monumentFix: 'Monument', save: 'Save review', saved: 'Saved', rBad: 'The token was not accepted.', rOff: 'Review is not enabled on this server.', rFail: 'Could not reach the server. Please try again.',
  },
  hi: {
    title: 'अभिलेख डिजिटल करें', intro: 'शिलालेख, पट्टिका या पांडुलिपि की तस्वीर को खोजने योग्य रिकॉर्ड बनाएं, जिसे समीक्षक जांचता है।',
    photo: 'दस्तावेज़ की तस्वीर', camera: 'तस्वीर लें या चुनें', rights: 'यह तस्वीर कौन साझा कर सकता है?', choose: 'चुनें…', monument: 'स्मारक (वैकल्पिक)', none: 'पता नहीं',
    submit: 'डिजिटल करें', reading: 'दस्तावेज़ पढ़ा जा रहा है…', samples: 'नमूना आज़माएं', samplesNote: 'विकिमीडिया कॉमन्स की मुफ़्त तस्वीरें।', credit: 'श्रेय',
    'own-photo': 'मैंने खुद खींची है', 'public-domain': 'सार्वजनिक क्षेत्र', 'cc-by': 'CC BY', 'cc-by-sa': 'CC BY-SA',
    draft: 'मसौदा: समीक्षा की प्रतीक्षा में', original: 'मूल पाठ', english: 'अंग्रेज़ी अनुवाद', claims: 'मसौदा दावे', evidence: 'साक्ष्य', unreadable: 'पाठ भरोसे से पढ़ा नहीं जा सका, इसलिए अनुमान नहीं लगाया गया।',
    noClaims: 'कोई दावा पाठ से जोड़ा नहीं जा सका।', again: 'एक और डिजिटल करें', review: 'समीक्षक पृष्ठ',
    errNeedRights: 'चुनें कि यह तस्वीर कौन साझा कर सकता है।', errNeedPhoto: 'पहले तस्वीर चुनें।', errTooBig: '6 MB से छोटी तस्वीर चुनें।', errType: 'JPEG, PNG या WebP तस्वीर चुनें।', errFail: 'अभी यह दस्तावेज़ पढ़ा नहीं जा सका। कृपया फिर कोशिश करें।', errSample: 'नमूना लोड नहीं हो सका। कृपया फिर कोशिश करें।',
    cardBody: 'पुराने शिलालेख या पट्टिका की तस्वीर लें। आगंतुकों को दिखने से पहले समीक्षक उसे जांचता है।',
    archive: 'अभिलेखागार से', archiveNote: 'अभिलेखागार के दस्तावेज़ से, संरक्षक द्वारा जांचा गया',
    rTitle: 'मसौदों की समीक्षा', rToken: 'समीक्षक टोकन', rLoad: 'मसौदे लोड करें', rNone: 'कोई मसौदा प्रतीक्षा में नहीं है।', approve: 'मंज़ूर करें', reject: 'अस्वीकार करें', monumentFix: 'स्मारक', save: 'समीक्षा सहेजें', saved: 'सहेजा गया', rBad: 'टोकन स्वीकार नहीं हुआ।', rOff: 'इस सर्वर पर समीक्षा चालू नहीं है।', rFail: 'सर्वर तक नहीं पहुंच सके। कृपया फिर कोशिश करें।',
  },
} as const
