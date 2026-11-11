'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Camera, FileText } from 'lucide-react'
import { Header, useLang } from '@/components/raahein'
import { copy, digitise, RIGHTS, SAMPLES, type ArchiveItem, type Rights } from '@/lib/archive'
import { monuments } from '@/lib/catalog'

const MAX_BYTES = 6 * 1024 * 1024
const field = 'card mt-1 min-h-12 w-full bg-transparent px-3 py-2'

export default function Digitise() {
  const { lang, setLang } = useLang()
  const t = copy[lang]
  const [file, setFile] = useState<File | null>(null)
  const [rights, setRights] = useState<Rights | ''>('')
  const [monument, setMonument] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [item, setItem] = useState<ArchiveItem | null>(null)
  const [preview, setPreview] = useState('') // drafts are private on the server, so show the uploader their own file

  async function run(photo: Blob, r: Rights | '', slug: string, name?: string) {
    if (busy) return
    if (!r) return setError(t.errNeedRights)
    if (photo.size > MAX_BYTES) return setError(t.errTooBig)
    if (!/^image\/(jpeg|png|webp)$/.test(photo.type)) return setError(t.errType)
    setError('')
    setBusy(true)
    try {
      setItem(await digitise(photo, r, slug, name))
      setPreview((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(photo) })
    } catch {
      setError(t.errFail)
    } finally {
      setBusy(false)
    }
  }

  async function runSample(sample: (typeof SAMPLES)[number]) {
    if (busy) return
    setError('')
    let blob: Blob
    try {
      const res = await fetch(sample.url)
      if (!res.ok) throw new Error()
      blob = await res.blob()
    } catch {
      return setError(t.errSample)
    }
    setRights(sample.rights)
    setMonument(sample.monument)
    await run(blob, sample.rights, sample.monument, `${sample.id}.jpg`)
  }

  const devanagari = item?.script.toLowerCase().includes('devanagari')
  return (
    <main className="shell pb-28 lg:mx-auto lg:max-w-3xl lg:px-8" lang={lang}>
      <Header lang={lang} setLang={setLang} />
      <div className="px-5 pt-6 lg:px-0 lg:pt-10">
        <h1 className="fraunces text-4xl">{t.title}</h1>
        <p className="mt-2 text-sm leading-6 text-[#5A4E3F]">{t.intro}</p>

        {!item && (
          <>
            <form className="card mt-6 space-y-4 p-4" onSubmit={(e) => { e.preventDefault(); if (!file) return setError(t.errNeedPhoto); void run(file, rights, monument, file.name) }}>
              <label className="block text-sm font-semibold" htmlFor="archive-photo">
                {t.photo}
                <span className="mt-1 flex min-h-12 items-center gap-2 rounded-xl border border-dashed border-[#B5452B]/50 px-3 py-2 font-normal">
                  <Camera aria-hidden="true" size={18} className="shrink-0 text-[#B5452B]" />
                  <input accept="image/jpeg,image/png,image/webp" capture="environment" className="w-full min-w-0 text-sm" id="archive-photo" onChange={(e) => setFile(e.target.files?.[0] ?? null)} type="file" />
                </span>
              </label>
              <label className="block text-sm font-semibold" htmlFor="archive-rights">
                {t.rights}
                <select className={field} id="archive-rights" onChange={(e) => setRights(e.target.value as Rights)} required value={rights}>
                  <option value="">{t.choose}</option>
                  {RIGHTS.map((value) => <option key={value} value={value}>{t[value]}</option>)}
                </select>
              </label>
              <label className="block text-sm font-semibold" htmlFor="archive-monument">
                {t.monument}
                <select className={field} id="archive-monument" onChange={(e) => setMonument(e.target.value)} value={monument}>
                  <option value="">{t.none}</option>
                  {monuments.map((m) => <option key={m.id} value={m.id}>{m.name[lang]}</option>)}
                </select>
              </label>
              <button className="primary-action flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-[#B5452B] font-semibold text-[#FBF6EC] disabled:opacity-60" disabled={busy} type="submit">
                <FileText aria-hidden="true" size={18} />{busy ? t.reading : t.submit}
              </button>
            </form>

            <section aria-labelledby="samples-heading" className="mt-8">
              <h2 className="fraunces text-2xl" id="samples-heading">{t.samples}</h2>
              <p className="mt-1 text-xs text-[#5A4E3F]">{t.samplesNote}</p>
              <ul className="mt-3 space-y-3">
                {SAMPLES.map((s) => (
                  <li className="rounded-xl border border-[#B5452B]/15 bg-[#FBF6EC] p-3" key={s.id}>
                    <button className="min-h-12 w-full rounded-full border border-[#B5452B] px-4 text-left text-sm font-semibold text-[#8F3221] disabled:opacity-60" disabled={busy} onClick={() => void runSample(s)} type="button">{s.title[lang]}</button>
                    <p className="mt-2 text-xs text-[#5A4E3F]">{t.credit}: <a className="underline" href={s.credit.page} rel="noreferrer" target="_blank">{s.credit.author}</a>, {s.credit.licence}, Wikimedia Commons</p>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}

        <p aria-live="polite" className="mt-4 text-sm text-[#8F3221]" role="status">{busy ? t.reading : error}</p>

        {item && (
          <article className="mt-6 space-y-5" data-testid="digitise-result">
            <span className="inline-block rounded-full border border-dashed border-[#E8A317] bg-[#FBF6EC] px-3 py-1 text-sm font-semibold text-[#8F3221]">{t.draft}</span>
            {/* eslint-disable-next-line @next/next/no-img-element -- served by the API, not the Next.js optimizer */}
            <img alt="" className="max-h-80 w-full rounded-xl border border-[#B5452B]/20 object-contain bg-[#EADBC0]/40" src={preview} />
            <section>
              <h2 className="fraunces text-xl">{t.original}{item.script && <span className="ml-2 text-sm font-normal text-[#5A4E3F]">{item.script}</span>}</h2>
              {item.transcription
                ? <p className="mt-2 whitespace-pre-wrap rounded-xl border border-[#B5452B]/15 bg-[#FBF6EC] p-4 text-lg leading-8" dir="auto" lang={devanagari ? 'hi' : undefined}>{item.transcription}</p>
                : <p className="mt-2 text-sm text-[#5A4E3F]">{t.unreadable}</p>}
            </section>
            {item.translation_en && (
              <section>
                <h2 className="fraunces text-xl">{t.english}</h2>
                <p className="mt-2 rounded-xl border border-[#B5452B]/15 bg-[#FBF6EC] p-4 text-[15px] leading-[1.7]" lang="en">{item.translation_en}</p>
              </section>
            )}
            <section>
              <h2 className="fraunces text-xl">{t.claims}</h2>
              {item.claims.length ? (
                <ul className="mt-2 space-y-3">
                  {item.claims.map((c) => (
                    <li className="rounded-xl border border-dashed border-[#E8A317] bg-[#FBF6EC]/70 p-4 text-[15px] leading-[1.7]" key={c.id}>
                      {c.text}
                      <blockquote className="mt-2 border-l-2 border-[#E8A317] pl-3 text-sm text-[#5A4E3F]"><span className="font-semibold">{t.evidence}:</span> {c.evidence_quote}</blockquote>
                    </li>
                  ))}
                </ul>
              ) : <p className="mt-2 text-sm text-[#5A4E3F]">{t.noClaims}</p>}
            </section>
            <button className="min-h-12 rounded-full border border-[#B5452B] px-5 text-sm font-semibold text-[#8F3221]" onClick={() => { setItem(null); setFile(null) }} type="button">{t.again}</button>
          </article>
        )}
        <Link className="link-primary mt-8 inline-flex min-h-12 items-center text-sm font-semibold underline-offset-2 hover:underline" href="/digitise/review">{t.review}</Link>
      </div>
    </main>
  )
}
