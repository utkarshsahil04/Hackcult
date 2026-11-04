'use client'

import dynamic from 'next/dynamic'
import type { MapProps } from '@/components/leaflet-map'

const LeafletMap = dynamic(() => import('@/components/leaflet-map'), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-[#EADBC0]" role="status" />,
})

export default function Map(props: MapProps) {
  return <LeafletMap {...props} />
}
