import { KolamLoader } from '@/components/heritage'

export default function Loading() {
  return <main className="shell grid min-h-[70svh] place-items-center"><div className="text-center"><KolamLoader /><p className="mt-3 text-sm text-[#5A4E3F]">Opening the next path…</p></div></main>
}
