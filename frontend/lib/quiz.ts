import data from './quiz.json'

type Text = { en: string; hi: string }
export type Question = { claim: string; q: Text; options: { en: string[]; hi: string[] }; answer: number; explain?: Text }

// Hand-written from the sourced, non-legend claims in backend/app/db/seed_data; quiz.test.ts checks every claim exists.
export const quiz: Record<string, Question[]> = data
export const quizFor = (id: string) => quiz[id] ?? []
