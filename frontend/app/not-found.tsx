import Link from 'next/link'

export default function NotFound() {
  return (
    <main className="shell grid min-h-[70svh] place-items-center px-5">
      <div className="card max-w-md p-8 text-center">
        <p className="fraunces text-6xl text-[#B5452B]">404</p>
        <h1 className="fraunces mt-3 text-3xl">This monument is not on the map</h1>
        <p className="mt-3 text-[#5A4E3F]">The address may have changed, but the archive is still open.</p>
        <Link className="link-inverse mt-6 flex min-h-12 items-center justify-center rounded-full bg-[#B5452B] px-5 font-semibold" href="/explore">Browse monuments</Link>
      </div>
    </main>
  )
}
