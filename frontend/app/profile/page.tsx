import { JourneyProfile } from '@/components/journey/JourneyProfile'
import { noIndex } from '@/lib/seo'

export const metadata = { title: 'My journey', ...noIndex }

export default function Page() { return <JourneyProfile /> }
