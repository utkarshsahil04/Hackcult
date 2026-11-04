// Decorative motifs drawn from Indian tradition: a rangoli mandala and a lotus divider.
const PETAL = 'M0 0C-7-10-7-22 0-32C7-22 7-10 0 0Z'
const LEAF = 'M0 0C-3-5-3-11 0-16C3-11 3-5 0 0Z'

function Ring({ count, radius, path, scale = 1, opacity = 1 }: { count: number; radius: number; path: string; scale?: number; opacity?: number }) {
  return <g opacity={opacity}>{Array.from({ length: count }, (_, i) => <path d={path} key={i} transform={`rotate(${(i * 360) / count}) translate(0 ${-radius}) scale(${scale})`} />)}</g>
}

export function Mandala({ className = '' }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} fill="none" stroke="currentColor" strokeWidth=".7" viewBox="-200 -200 400 400">
      <circle r="196" strokeDasharray="2 6" />
      <circle r="188" />
      <Ring count={36} path={LEAF} radius={172} />
      <circle r="150" />
      <Ring count={24} opacity={.8} path={PETAL} radius={114} />
      <circle r="108" strokeDasharray="1 4" />
      <Ring count={16} path={PETAL} radius={72} />
      <circle r="66" />
      <Ring count={12} path={LEAF} radius={44} />
      <circle r="24" />
      <Ring count={8} path={LEAF} radius={8} />
    </svg>
  )
}

export function LotusDivider({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden="true" className={`flex items-center justify-center gap-3 text-[#E8A317] ${className}`}>
      <span className="h-px max-w-40 flex-1 bg-gradient-to-r from-transparent to-[#E8A317]" />
      <svg className="h-7 w-12" fill="none" stroke="currentColor" strokeWidth="1.1" viewBox="-24 -26 48 30">
        <path d="M0 2C-5-6-5-15 0-24C5-15 5-6 0 2Z" fill="#B5452B" fillOpacity=".18" stroke="#B5452B" />
        <path d="M-2 2C-11-3-14-11-13-19C-7-16-3-10-2 2ZM2 2C11-3 14-11 13-19C7-16 3-10 2 2Z" />
        <path d="M-5 2C-14 2-20-3-23-9C-16-10-9-6-5 2ZM5 2C14 2 20-3 23-9C16-10 9-6 5 2Z" />
      </svg>
      <span className="h-px max-w-40 flex-1 bg-gradient-to-l from-transparent to-[#E8A317]" />
    </div>
  )
}
