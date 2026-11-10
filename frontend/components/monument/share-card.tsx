'use client'

import { useState } from 'react'
import { Share2 } from 'lucide-react'
import { imageCredits, monumentImages, type Lang, type Monument } from '@/lib/catalog'

const W = 1080
const H = 1350

function loadPhoto(src?: string) {
  return new Promise<HTMLImageElement | null>((resolve) => {
    if (!src) return resolve(null)
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = src
  })
}

function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, maxLines: number) {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word
    if (line && ctx.measureText(next).width > maxWidth) {
      lines.push(line)
      line = word
    } else line = next
  }
  if (line) lines.push(line)
  if (lines.length > maxLines) {
    lines.length = maxLines
    lines[maxLines - 1] = `${lines[maxLines - 1].replace(/\s*\S+$/, '')}…`
  }
  return lines
}

function draw(monument: Monument, lang: Lang, url: string, photo: HTMLImageElement | null) {
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no canvas')
  ctx.fillStyle = '#8F3221' // plain warm background when the photo is missing
  ctx.fillRect(0, 0, W, H)
  if (photo) {
    const scale = Math.max(W / photo.naturalWidth, H / photo.naturalHeight)
    const w = photo.naturalWidth * scale
    const h = photo.naturalHeight * scale
    ctx.drawImage(photo, (W - w) / 2, (H - h) / 2, w, h)
  }
  const shade = ctx.createLinearGradient(0, 0, 0, H)
  shade.addColorStop(0, 'rgba(31,26,20,0.55)')
  shade.addColorStop(0.3, 'rgba(31,26,20,0)')
  shade.addColorStop(0.6, 'rgba(31,26,20,0.82)')
  shade.addColorStop(1, 'rgba(31,26,20,0.95)')
  ctx.fillStyle = shade
  ctx.fillRect(0, 0, W, H)

  const pad = 80
  const fact = monument.sections.find((section) => !section.isLegend)?.text[lang] ?? ''
  const credit = imageCredits[monument.id]
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = '#FBF6EC'
  ctx.font = '600 44px Georgia, serif'
  ctx.fillText('Raahein', pad, 120)

  ctx.font = '400 38px Georgia, serif'
  const factLines = wrap(ctx, fact, W - pad * 2, 6)
  ctx.font = '600 84px Georgia, serif'
  const nameLines = wrap(ctx, monument.name[lang], W - pad * 2, 2)
  // Lay out bottom-up so long names and facts never run off the card.
  let y = H - pad - (credit ? 70 : 0) - 100 - factLines.length * 54 - 40 - (nameLines.length - 1) * 96
  for (const line of nameLines) { ctx.fillText(line, pad, y); y += 96 }
  ctx.fillStyle = '#E8A317'
  ctx.fillRect(pad, y - 50, 120, 6)
  y += 30
  ctx.fillStyle = '#FBF6EC'
  ctx.font = '400 38px Georgia, serif'
  for (const line of factLines) { ctx.fillText(line, pad, y); y += 54 }

  ctx.font = '600 30px system-ui, sans-serif'
  ctx.fillStyle = '#E8A317'
  ctx.fillText(url.replace(/^https?:\/\//, ''), pad, H - pad - (credit ? 70 : 0), W - pad * 2)
  if (credit) {
    ctx.font = '400 24px system-ui, sans-serif'
    ctx.fillStyle = 'rgba(251,246,236,0.8)'
    const text = `${lang === 'hi' ? 'तस्वीर' : 'Photo'}: ${credit.artist}, ${credit.licence}, Wikimedia Commons`
    wrap(ctx, text, W - pad * 2, 2).forEach((line, index) => ctx.fillText(line, pad, H - pad - 30 + index * 32))
  }
  return new Promise<Blob | null>((resolve) => {
    try { canvas.toBlob(resolve, 'image/png') } catch { resolve(null) } // a tainted canvas throws SecurityError
  })
}

export type ShareResult = 'shared' | 'cancelled' | 'saved' | 'saved-copied'

export async function shareMonumentCard(monument: Monument, lang: Lang, url = window.location.href): Promise<ShareResult> {
  const photo = await loadPhoto(monumentImages[monument.id])
  const blob = (await draw(monument, lang, url, photo)) ?? (photo ? await draw(monument, lang, url, null) : null)
  if (!blob) throw new Error('card could not be drawn')
  const file = new File([blob], `${monument.id}-raahein.png`, { type: 'image/png' })
  const title = monument.name[lang]
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title, url })
      return 'shared'
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return 'cancelled'
      // Any other share failure falls through to a download so the card is not lost.
    }
  }
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = file.name
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
  const copied = await navigator.clipboard?.writeText(url).then(() => true, () => false)
  return copied ? 'saved-copied' : 'saved'
}

export function ShareButton({ monument, lang }: { monument: Monument; lang: Lang }) {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const hi = lang === 'hi'

  async function share() {
    setBusy(true)
    setMessage('')
    try {
      const result = await shareMonumentCard(monument, lang)
      if (result === 'saved') setMessage(hi ? 'कार्ड डाउनलोड हो गया।' : 'Card downloaded.')
      if (result === 'saved-copied') setMessage(hi ? 'कार्ड डाउनलोड हो गया और लिंक कॉपी हो गया।' : 'Card downloaded and link copied.')
    } catch {
      setMessage(hi ? 'माफ़ कीजिए, कार्ड नहीं बन सका। कृपया फिर कोशिश करें।' : 'Sorry, the card could not be made. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button aria-busy={busy} className="inline-flex min-h-12 items-center gap-2 rounded-full border border-[#B5452B]/40 bg-[#FBF6EC] px-5 text-sm font-semibold text-[#8F3221] transition-colors hover:border-[#B5452B] disabled:opacity-60" disabled={busy} onClick={share} type="button">
        <Share2 aria-hidden="true" size={16} />{hi ? 'साझा करें' : 'Share'}
      </button>
      <p aria-live="polite" className="basis-full text-sm text-[#5A4E3F] empty:hidden" role="status">{message}</p>
    </>
  )
}
