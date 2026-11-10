import { noIndex } from '@/lib/seo'

export const metadata = { title: 'A shared tour', ...noIndex }

export default function Layout({ children }: { children: React.ReactNode }) { return children }
