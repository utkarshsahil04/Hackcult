import React from 'react'

export const RaaheinLogo = ({ className = 'w-full max-w-2xl h-auto' }: { className?: string }) => {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 1000 600"
        className="w-full h-auto drop-shadow-sm"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="warmStone" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#F9844A" />
            <stop offset="40%" stopColor="#E76F51" />
            <stop offset="100%" stopColor="#8F2D14" />
          </linearGradient>

          <linearGradient id="terracotta" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#D9531E" />
            <stop offset="50%" stopColor="#9C2713" />
            <stop offset="100%" stopColor="#5E1609" />
          </linearGradient>

          <linearGradient id="brandIndigo" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1D2A60" />
            <stop offset="100%" stopColor="#0B1333" />
          </linearGradient>

          <linearGradient id="roadGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FFA62B" />
            <stop offset="45%" stopColor="#FF5E36" />
            <stop offset="100%" stopColor="#C9184A" />
          </linearGradient>

          <linearGradient id="scannerGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3A86FF" />
            <stop offset="100%" stopColor="#1E3A8A" />
          </linearGradient>
        </defs>

        {/* South Indian Gopuram */}
        <g id="south-gopuram" transform="translate(180, 160)">
          <rect x="0" y="160" width="110" height="40" fill="url(#warmStone)" rx="2" />
          <polygon points="8,160 102,160 95,130 15,130" fill="url(#warmStone)" />
          <polygon points="15,130 95,130 88,100 22,100" fill="url(#terracotta)" />
          <polygon points="22,100 88,100 80,72 30,72" fill="url(#warmStone)" />
          <polygon points="30,72 80,72 73,45 37,45" fill="url(#terracotta)" />
          <path d="M 37 45 Q 55 20 73 45 Z" fill="url(#warmStone)" />
          <circle cx="45" cy="22" r="3" fill="#FFD166" />
          <circle cx="55" cy="18" r="3.5" fill="#FFD166" />
          <circle cx="65" cy="22" r="3" fill="#FFD166" />
          <path d="M 43 200 V 175 Q 55 168 67 175 V 200 Z" fill="#2E0E08" />
        </g>

        {/* Gateway & Arches */}
        <g id="west-gateway" transform="translate(270, 220)">
          <rect x="15" y="45" width="180" height="95" fill="url(#warmStone)" rx="2" />
          <rect x="25" y="10" width="30" height="40" fill="url(#terracotta)" />
          <rect x="155" y="10" width="30" height="40" fill="url(#terracotta)" />
          <path d="M 75 140 V 85 Q 75 60 105 60 Q 135 60 135 85 V 140 Z" fill="#FFFDF7" />
          <path d="M 35 120 V 95 Q 40 85 45 95 V 120 Z" fill="#4A150D" />
          <path d="M 165 120 V 95 Q 170 85 175 95 V 120 Z" fill="#4A150D" />
        </g>

        {/* Chand Baori Stepwell */}
        <g id="stepwell" transform="translate(310, 160)" opacity="0.9">
          <rect x="0" y="0" width="120" height="50" fill="url(#warmStone)" />
          <polygon points="10,0 30,0 20,20" fill="#4A150D" />
          <polygon points="40,0 60,0 50,20" fill="#4A150D" />
          <polygon points="70,0 90,0 80,20" fill="#4A150D" />
          <polygon points="100,0 120,0 110,20" fill="#4A150D" />
          <polygon points="25,20 45,20 35,40" fill="#2E0E08" />
          <polygon points="75,20 95,20 85,40" fill="#2E0E08" />
        </g>

        {/* Central Dome & Minaret */}
        <g id="north-dome" transform="translate(435, 90)">
          <rect x="135" y="30" width="18" height="180" fill="url(#terracotta)" />
          <polygon points="131,30 157,30 144,10" fill="#FFD166" />
          <rect x="10" y="150" width="110" height="60" fill="url(#terracotta)" />
          <path d="M 20 150 C 10 90 65 40 65 15 C 65 40 120 90 110 150 Z" fill="url(#terracotta)" />
          <line x1="65" y1="15" x2="65" y2="0" stroke="#FFD166" strokeWidth="4" strokeLinecap="round" />
          <circle cx="65" cy="0" r="3" fill="#FFD166" />
          <path d="M 40 210 V 170 Q 65 150 90 170 V 210 Z" fill="#FFFDF7" />
        </g>

        {/* Konark Chakra */}
        <g id="east-chakra" transform="translate(570, 245)">
          <circle cx="60" cy="60" r="55" stroke="url(#terracotta)" strokeWidth="10" fill="#FFB074" />
          <circle cx="60" cy="60" r="16" fill="url(#terracotta)" />
          <line x1="60" y1="10" x2="60" y2="110" stroke="url(#terracotta)" strokeWidth="6" />
          <line x1="10" y1="60" x2="110" y2="60" stroke="url(#terracotta)" strokeWidth="6" />
          <line x1="25" y1="25" x2="95" y2="95" stroke="url(#terracotta)" strokeWidth="5" />
          <line x1="95" y1="25" x2="25" y2="95" stroke="url(#terracotta)" strokeWidth="5" />
        </g>

        {/* Sanchi Stupa & Northeast Monastery */}
        <g id="sanchi-stupa" transform="translate(640, 240)">
          <path d="M 0 120 A 80 80 0 0 1 160 120 Z" fill="url(#terracotta)" />
          <rect x="68" y="28" width="24" height="14" fill="#FFD166" />
          <line x1="80" y1="28" x2="80" y2="8" stroke="#D9531E" strokeWidth="3" />
          <line x1="70" y1="14" x2="90" y2="14" stroke="#FFD166" strokeWidth="3" />
          <line x1="73" y1="9" x2="87" y2="9" stroke="#FFD166" strokeWidth="2.5" />
        </g>

        <g id="northeast-monastery" transform="translate(750, 280)">
          <path d="M 0 80 L 15 55 L 75 55 L 90 80 Z" fill="url(#warmStone)" />
          <path d="M 12 55 L 25 35 L 65 35 L 78 55 Z" fill="url(#terracotta)" />
          <polygon points="25,35 65,35 45,15" fill="#FFD166" />
        </g>

        {/* AR Scanner Lens */}
        <g id="ar-lens" transform="translate(520, 310)">
          <rect x="0" y="10" width="70" height="52" rx="10" fill="url(#scannerGlow)" />
          <rect x="22" y="3" width="26" height="8" rx="2" fill="#1E3A8A" />
          <circle cx="35" cy="36" r="18" fill="#FFFFFF" />
          <circle cx="35" cy="36" r="14" fill="#3A86FF" />
          <circle cx="35" cy="36" r="6" fill="#0B1333" />
          <circle cx="40" cy="32" r="3" fill="#FFFFFF" opacity="0.8" />
        </g>

        {/* Route Planner Nodes */}
        <g id="planner-network" stroke="#FFA62B" strokeWidth="2.5" fill="#FFFDF7">
          <line x1="500" y1="360" x2="525" y2="340" />
          <line x1="585" y1="350" x2="650" y2="330" />
          <line x1="650" y1="330" x2="710" y2="360" />
          <line x1="710" y1="360" x2="750" y2="340" />
          <circle cx="500" cy="360" r="4" fill="#FFA62B" />
          <circle cx="650" cy="330" r="5" stroke="#FFA62B" strokeWidth="2" />
          <circle cx="710" cy="360" r="4" fill="#FFA62B" />
          <circle cx="750" cy="340" r="4.5" fill="#FFA62B" />
        </g>

        {/* Map Destination Pin */}
        <g id="destination-pin" transform="translate(795, 395)">
          <path
            d="M 35 0 C 15 0 0 15 0 35 C 0 60 35 95 35 95 C 35 95 70 60 70 35 C 70 15 55 0 35 0 Z"
            fill="#281A4C"
          />
          <circle cx="35" cy="35" r="18" fill="none" stroke="#FFD166" strokeWidth="2" strokeDasharray="3 2" />
          <circle cx="35" cy="35" r="11" fill="none" stroke="#FFA62B" strokeWidth="2" />
          <circle cx="35" cy="35" r="4" fill="#FFD166" />
        </g>

        {/* Typography */}
        <g id="brand-name" transform="translate(200, 445)">
          <line x1="450" y1="-85" x2="495" y2="-85" stroke="url(#roadGradient)" strokeWidth="8" strokeLinecap="round" />
          <text
            x="0"
            y="0"
            fontFamily="'Baloo 2', 'Rozha One', 'Poppins', sans-serif"
            fontSize="132"
            fontWeight="900"
            letterSpacing="-2"
            fill="url(#brandIndigo)"
          >
            raahein
          </text>
        </g>

        {/* Highway Sweep Trail */}
        <g id="flowing-road">
          <path
            d="M 170 535 C 320 470 540 480 830 490 C 865 470 855 435 830 395 C 790 480 480 490 170 535 Z"
            fill="url(#roadGradient)"
          />
          <path
            d="M 230 545 C 380 500 520 505 630 545 C 470 525 330 525 230 545 Z"
            fill="#FFB020"
            opacity="0.9"
          />
        </g>
      </svg>
    </div>
  )
}

export default RaaheinLogo

