'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Header, useLang } from '@/components/raahein'
import { copy, draftImageUrl, listDrafts, reviewItem, type ArchiveItem } from '@/lib/archive'
import { monuments } from '@/lib/catalog'

const TOKEN_KEY = 'raahein-review-token'
const field = 'card mt-1 min-h-12 w-full bg-transparent px-3 py-2'

function initialToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) ?? '' } catch { return '' }
}

// Claims start as rejected: nothing reaches visitors unless the reviewer approves it.
type Edit = { approve: boolean; text: string }

function ReviewCard({ item, token, onDone }: { item: ArchiveItem; token: string; onDone: (id: number) => void }) {
  const { lang } = useLang()
  const [src, setSrc] = useState('')
  useEffect(() => {
    let url = ''
    draftImageUrl(item, token).then((u) => setSrc((url = u))).catch(() => setSrc(''))
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [item, token])
  const t = copy[lang]
  const [edits, setEdits] = useState<Record<number, Edit>>(() => Object.fromEntries(item.claims.map((c) => [c.id, { approve: false, text: c.text }])))
  const [slug, setSlug] = useState(item.monument_slug ?? '')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const patch = (id: number, p: Partial<Edit>) => setEdits((e) => ({ ...e, [id]: { ...e[id], ...p } }))

  async function save() {
    setBusy(true)
    setStatus('')
    try {
      await reviewItem(item.id, token, item.claims.map((c) => ({ id: c.id, decision: edits[c.id].approve ? 'approve' : 'reject', text: edits[c.id].text })), slug)
      onDone(item.id)
    } catch (e) {
      const code = (e as { status?: number }).status
      setStatus(code === 401 ? t.rBad : code === 403 ? t.rOff : t.rFail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="card space-y-4 p-4" data-testid="review-item">
      {/* eslint-disable-next-line @next/next/no-img-element -- served by the API, not the Next.js optimizer */}
      {src && <img alt="" className="max-h-60 w-full rounded-lg object-contain bg-[#EADBC0]/40" src={src} />}
      {item.transcription && <p className="whitespace-pre-wrap text-base leading-7" dir="auto">{item.transcription}</p>}
      {item.translation_en && <p className="text-sm leading-6 text-[#5A4E3F]" lang="en">{item.translation_en}</p>}
      <ul className="space-y-3">
        {item.claims.map((c) => (
          <li className="rounded-xl border border-dashed border-[#E8A317] p-3" key={c.id}>
            <label className="block text-sm font-semibold" htmlFor={`claim-${c.id}`}>{t.claims}</label>
            <textarea className={field} id={`claim-${c.id}`} onChange={(e) => patch(c.id, { text: e.target.value })} rows={2} value={edits[c.id].text} />
            <p className="mt-1 text-xs text-[#5A4E3F]">{t.evidence}: {c.evidence_quote}</p>
            <div className="mt-2 flex gap-2" role="group">
              {[true, false].map((approve) => (
                <button aria-pressed={edits[c.id].approve === approve} className={`min-h-12 flex-1 rounded-full border px-4 text-sm font-semibold ${edits[c.id].approve === approve ? 'border-[#B5452B] bg-[#B5452B] text-white' : 'border-[#C8B594] bg-[#FBF6EC]'}`} key={String(approve)} onClick={() => patch(c.id, { approve })} type="button">{approve ? t.approve : t.reject}</button>
              ))}
            </div>
          </li>
        ))}
      </ul>
      <label className="block text-sm font-semibold" htmlFor={`slug-${item.id}`}>
        {t.monumentFix}
        <select className={field} id={`slug-${item.id}`} onChange={(e) => setSlug(e.target.value)} value={slug}>
          <option value="">{t.none}</option>
          {monuments.map((m) => <option key={m.id} value={m.id}>{m.name[lang]}</option>)}
        </select>
      </label>
      <button className="primary-action min-h-12 w-full rounded-full bg-[#B5452B] font-semibold text-[#FBF6EC] disabled:opacity-60" disabled={busy} onClick={() => void save()} type="button">{t.save}</button>
      <p aria-live="polite" className="text-sm text-[#8F3221]" role="status">{status}</p>
    </li>
  )
}

export default function ReviewPage() {
  const { lang, setLang } = useLang()
  const t = copy[lang]
  const [token, setToken] = useState(initialToken)
  const [items, setItems] = useState<ArchiveItem[] | null>(null)
  const [error, setError] = useState('')

  async function load() {
    try { sessionStorage.setItem(TOKEN_KEY, token) } catch { /* the token just stays in memory */ }
    setError('')
    try { setItems(await listDrafts(token)) } catch (e) { setError((e as { status?: number }).status === 401 ? t.rBad : t.rFail) }
  }

  return (
    <main className="shell pb-28 lg:mx-auto lg:max-w-3xl lg:px-8" lang={lang}>
      <Header lang={lang} setLang={setLang} />
      <div className="px-5 pt-6 lg:px-0 lg:pt-10">
        <h1 className="fraunces text-4xl">{t.rTitle}</h1>
        <form className="mt-4 flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); void load() }}>
          <label className="block flex-1 text-sm font-semibold" htmlFor="review-token">
            {t.rToken}
            <input autoComplete="off" suppressHydrationWarning className={field} id="review-token" onChange={(e) => setToken(e.target.value)} type="password" value={token} />
          </label>
          <button className="min-h-12 rounded-full bg-[#B5452B] px-5 font-semibold text-[#FBF6EC]" type="submit">{t.rLoad}</button>
        </form>
        <p aria-live="polite" className="mt-3 text-sm text-[#8F3221]" role="status">{error}</p>
        {items && (items.length
          ? <ul className="mt-4 space-y-4">{items.map((item) => <ReviewCard item={item} key={item.id} onDone={(id) => setItems((list) => list?.filter((i) => i.id !== id) ?? null)} token={token} />)}</ul>
          : <p className="mt-4 text-sm text-[#5A4E3F]">{t.rNone}</p>)}
        <Link className="link-primary mt-8 inline-flex min-h-12 items-center text-sm font-semibold underline-offset-2 hover:underline" href="/digitise">{t.title}</Link>
      </div>
    </main>
  )
}
