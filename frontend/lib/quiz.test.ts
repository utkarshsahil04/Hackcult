import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { quiz } from './quiz'

const seed = (name: string) => JSON.parse(readFileSync(new URL(`../../backend/app/db/seed_data/${name}`, import.meta.url), 'utf8'))
const claims: { monument: string; key: string; is_legend: boolean }[] = seed('claims.json')
const claimsHi: Record<string, string> = seed('claims_hi.json')
const byId = new Map(claims.map((c) => [`${c.monument}/${c.key}`, c]))
const devanagari = /[ऀ-ॿ]/

describe('monument quiz', () => {
  // The 13 sites sourced later have too few claims for three questions each, so they carry no quiz yet.
  it('has exactly 3 questions for each of the 15 quizzed monuments', () => {
    expect(Object.keys(quiz)).toHaveLength(15)
    for (const [id, questions] of Object.entries(quiz)) expect(questions, id).toHaveLength(3)
  })

  it('draws every question from a sourced, non-legend claim of that monument', () => {
    for (const [id, questions] of Object.entries(quiz)) for (const { claim } of questions) {
      expect(byId.get(claim), claim).toBeDefined()
      expect(byId.get(claim)!.is_legend, claim).toBe(false)
      expect(byId.get(claim)!.monument, claim).toBe(id)
      expect(claimsHi[claim], claim).toBeTruthy()
    }
  })

  it('has 4 distinct options in both languages, a valid answer and Hindi text', () => {
    for (const { claim, q, options, answer, explain } of Object.values(quiz).flat()) {
      for (const lang of ['en', 'hi'] as const) {
        expect(options[lang], claim).toHaveLength(4)
        expect(new Set(options[lang]).size, claim).toBe(4)
      }
      expect([0, 1, 2, 3], claim).toContain(answer)
      expect(q.hi, claim).toMatch(devanagari)
      if (explain) expect(explain.hi, claim).toMatch(devanagari)
      // Numbers (years, counts) read the same in Hindi; any other option must be translated.
      for (const option of options.hi) expect(option, claim).toMatch(/[ऀ-ॿ]|^[\d,–]+$/)
    }
  })
})
