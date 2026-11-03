'use client'

import Link from 'next/link'

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="shell grid min-h-[70svh] place-items-center px-5">
      <div className="card max-w-md p-8 text-center">
        <h1 className="fraunces text-3xl">This path is temporarily closed</h1>
        <p className="mt-3 text-[#5A4E3F]">Your place is safe. Try this page again or return to the monuments.</p>
        <button className="mt-6 min-h-12 w-full rounded-full bg-[#B5452B] px-5 font-semibold text-[#FBF6EC]" onClick={reset} type="button">Try again</button>
        <Link className="link-primary mt-2 flex min-h-12 items-center justify-center" href="/explore">Browse monuments</Link>
      </div>
    </main>
  )
}
