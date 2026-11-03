import type { Lang } from './catalog'

type Narration = { type: 'speech'; voice: SpeechSynthesisVoice } | { type: 'audio'; url?: string; note?: string }

export async function getNarration(lang: Lang): Promise<Narration> {
  const voice = typeof window !== 'undefined' && 'speechSynthesis' in window
    ? speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang))
    : undefined
  return voice ? { type: 'speech', voice } : { type: 'audio' }
}
