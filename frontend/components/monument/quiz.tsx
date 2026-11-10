'use client'

import { useState } from 'react'
import { useLang } from '@/components/raahein'
import { quizFor } from '@/lib/quiz'

export function MonumentQuiz({ id }: { id: string }) {
  const { lang } = useLang()
  const questions = quizFor(id)
  const [index, setIndex] = useState(0)
  const [picked, setPicked] = useState<number | null>(null)
  const [score, setScore] = useState(0)
  if (!questions.length) return null

  const done = index >= questions.length
  const question = questions[Math.min(index, questions.length - 1)]
  const right = picked === question.answer
  const pick = (choice: number) => {
    if (picked !== null) return
    setPicked(choice)
    if (choice === question.answer) setScore((s) => s + 1)
  }
  const next = () => { setIndex((i) => i + 1); setPicked(null) }
  const restart = () => { setIndex(0); setPicked(null); setScore(0) }
  const button = 'min-h-12 rounded-xl px-4 py-2 font-semibold'

  return (
    <section data-testid="quiz" className="mt-8 rounded-xl border border-[#B5452B]/15 bg-[#FBF6EC] p-4 text-[#1F1A14]" aria-labelledby={`quiz-${id}`}>
      <h2 id={`quiz-${id}`} className="fraunces text-2xl">{lang === 'hi' ? 'जो पढ़ा, उसे परखें' : 'Test what you just learned'}</h2>
      {done ? (
        <div className="mt-3" aria-live="polite">
          <p className="text-lg font-semibold">{lang === 'hi' ? `${questions.length} में से ${score} सही` : `${score} of ${questions.length}`}</p>
          <button type="button" onClick={restart} className={`${button} mt-3 bg-[#B5452B] text-white hover:bg-[#8F3221]`}>{lang === 'hi' ? 'फिर से कोशिश करें' : 'Try again'}</button>
        </div>
      ) : (
        <>
          <p className="mt-1 text-sm text-[#5A4E3F]">{lang === 'hi' ? `प्रश्न ${index + 1} / ${questions.length}` : `Question ${index + 1} of ${questions.length}`}</p>
          <p className="mt-3 font-semibold">{question.q[lang]}</p>
          <div className="mt-3 grid gap-2">
            {question.options[lang].map((option, choice) => (
              <button key={option} type="button" aria-pressed={picked === choice} onClick={() => pick(choice)}
                className={`${button} border text-left ${picked !== null && choice === question.answer ? 'border-[#E8A317] bg-[#E8A317]/20' : picked === choice ? 'border-[#8F3221] bg-[#B5452B]/10' : 'border-[#B5452B]/25 bg-white/60 hover:bg-[#B5452B]/5'}`}>
                {option}
              </button>
            ))}
          </div>
          <div aria-live="polite" className="mt-3">
            {picked !== null && (
              <>
                <p className="font-semibold">{right ? (lang === 'hi' ? 'सही!' : 'Correct') : (lang === 'hi' ? 'सही नहीं' : 'Not quite')}{!right && ` — ${lang === 'hi' ? 'सही उत्तर' : 'the answer is'}: ${question.options[lang][question.answer]}`}</p>
                {question.explain && <p className="mt-1 text-sm leading-6 text-[#5A4E3F]">{question.explain[lang]}</p>}
                <button type="button" onClick={next} className={`${button} mt-3 bg-[#B5452B] text-white hover:bg-[#8F3221]`}>{index + 1 < questions.length ? (lang === 'hi' ? 'आगे' : 'Next') : (lang === 'hi' ? 'नतीजा देखें' : 'See score')}</button>
              </>
            )}
          </div>
        </>
      )}
    </section>
  )
}
