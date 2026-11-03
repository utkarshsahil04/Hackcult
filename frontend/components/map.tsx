'use client'
import dynamic from 'next/dynamic'
const LeafletMap=dynamic(()=>import('@/components/leaflet-map'),{ssr:false,loading:()=> <div className="grid h-full w-full place-items-center bg-[#EADBC0] text-sm text-[#5A4E3F]" role="status">Loading map…</div>})
export default function Map({route=false,stops}:{route?:boolean;stops?:string[]}){return <LeafletMap route={route} stops={stops}/>} 
