'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowRight, Compass, Eye, Info, Layers, Sparkles, Sun, Volume2, VolumeX } from 'lucide-react'
import { monuments } from '@/lib/mock'
import { InlayFrame } from '@/components/heritage'

type Lang = 'en' | 'hi'

const architecturalData: Record<string, {
  alignment: { en: string; hi: string }
  material: { en: string; hi: string }
  acoustic: { en: string; hi: string }
  facts: { en: string; hi: string }[]
}> = {
  'taj-mahal': {
    alignment: { en: 'Equinoctial River Axis & Solstice Alignment', hi: 'विषुवतीय यमुना अक्ष व संक्रांति रेखा' },
    material: { en: 'Makrana White Marble & Pietra Dura Inlays', hi: 'मकराना श्वेत संगमरमर व पच्चीकारी' },
    acoustic: { en: '28-second reverberation beneath main dome', hi: 'मुख्य गुम्बद के नीचे २८ सेकंड की प्रतिध्वनि' },
    facts: [
      { en: 'Pietra dura floral panels use 28 varieties of semi-precious stones (jade, lapis, turquoise).', hi: 'पच्चीकारी में २८ प्रकार के दुर्लभ रत्न (लापिस, फिरोज़ा, जेड) जड़े गए हैं।' },
      { en: 'Four minarets lean outward by 3 degrees to prevent collapse onto the tomb during earthquakes.', hi: 'चारों मीनारें ३ डिग्री बाहर झुकी हैं ताकि भूकंप में मुख्य मकबरे पर न गिरें।' },
      { en: 'The charbagh garden cross-axis reflects the full moon precisely in the lotus pond.', hi: 'चारबाग का अक्ष पूर्णिमा के चांद को कमल ताल में सटीक प्रतिबिंबित करता है।' },
    ],
  },
  'agra-fort': {
    alignment: { en: 'Yamuna River Defense & Sunrise Darshan Axis', hi: 'यमुना रक्षा प्राचीर व सूर्योदय झरोखा दर्शन' },
    material: { en: 'Dholpur Red Sandstone & Inlaid Marble', hi: 'धौलपुर लाल बलुआ पत्थर व संगमरमर' },
    acoustic: { en: 'Musamman Burj acoustic river whisper conduit', hi: 'मुसम्मन बुर्ज की सूक्ष्म ध्वनि संवाहक रचना' },
    facts: [
      { en: 'Massive double-curtain walls stand over 21 meters high, stretching 2.5 kilometers along the river.', hi: '२१ मीटर ऊंची दोहरी रक्षा प्राचीर नदी के किनारे २.५ किमी तक फैली है।' },
      { en: 'Sheesh Mahal features thousands of Syrian convex mirrors reflecting candlelight across the hall.', hi: 'शीश महल में सीरियाई दर्पण मोमबत्ती की रोशनी को हजारों तारों में बदलते हैं।' },
      { en: 'Shah Jahan spent his final years here gazing at the Taj Mahal across the bend of the Yamuna.', hi: 'शाहजहाँ ने जीवन के अंतिम वर्ष यहीं से यमुना पार ताजमहल को निहारते हुए बिताए।' },
    ],
  },
  'red-fort': {
    alignment: { en: 'Shahjahanabad Cardinal Grid & Riverfront', hi: 'शाहजहानाबाद प्रधान अक्ष व यमुना किनारा' },
    material: { en: 'Ochre Red Sandstone & Marble Pavilions', hi: 'गेरुआ लाल बलुआ पत्थर व संगमरमर मंडप' },
    acoustic: { en: 'Diwan-i-Khas marble portico sound resonance', hi: 'दीवाने-खास के संगमरमर बरामदे का ध्वनि विस्तार' },
    facts: [
      { en: 'The Stream of Paradise (Nahr-i-Bihisht) flowed continuously through all royal pavilions for natural cooling.', hi: 'नहर-ए-बहिश्त सभी शाही महलों के बीच से बहकर प्राकृतिक वातानुकूलन करती थी।' },
      { en: 'Lahori Gate bastions incorporate ingenious zigzag barbicans added by Aurangzeb for artillery defense.', hi: 'लाहौरी गेट में तोपों से बचाव के लिए टेढ़े-मेढ़े सुरक्षा द्वार बनाए गए।' },
      { en: 'Site of the historic Peacock Throne before it was carried away in the 18th century.', hi: '१८वीं सदी से पहले यह विश्व प्रसिद्ध मयूर सिंहासन का मूल स्थान था।' },
    ],
  },
  'humayuns-tomb': {
    alignment: { en: 'Astronomical Cardinal Charbagh Geometry', hi: 'खगोलीय चारबाग सममिति व दिशा अक्ष' },
    material: { en: 'Chunar Red Sandstone with White Marble Borders', hi: 'चुनार लाल पत्थर व सफेद संगमरमर की पट्टियां' },
    acoustic: { en: 'Octagonal chamber double-dome acoustic balance', hi: 'अष्टकोणीय कक्ष व दोहरे गुम्बद का ध्वनि संतुलन' },
    facts: [
      { en: 'First grand garden tomb in the Indian subcontinent, introducing the iconic double dome architecture.', hi: 'भारतीय उपमहाद्वीप का पहला विशाल बाग मकबरा, जिसने दोहरे गुम्बद की शुरुआत की।' },
      { en: 'The four-part Charbagh symbolizes the four rivers of paradise described in historic manuscripts.', hi: 'चारबाग की चार धाराएं ऐतिहासिक ग्रंथों में वर्णित जन्नत की नदियों का प्रतीक हैं।' },
      { en: 'Served as the direct architectural inspiration and proportion blueprint for the Taj Mahal.', hi: 'यह ताजमहल के निर्माण का प्रत्यक्ष वास्तुशिल्प और अनुपातिक प्रेरणा स्रोत बना।' },
    ],
  },
  'qutb-complex': {
    alignment: { en: 'Astronomical Gnomon & Solar Noon Shadow', hi: 'खगोलीय शंकु व मध्याह्न छाया मापन अक्ष' },
    material: { en: 'Fluted Red Sandstone & White Marble Upper Storeys', hi: 'धारदार लाल बलुआ पत्थर व ऊपरी संगमरमर' },
    acoustic: { en: 'Projecting corbelled balcony vocal propagation', hi: 'झरोखा बालकनी की खुली ध्वनि प्रसार क्षमता' },
    facts: [
      { en: 'At 72.5 meters, it is the tallest brick minaret in the world, tapering from 14.3m base to 2.7m at the top.', hi: '७२.५ मीटर के साथ यह दुनिया की सबसे ऊंची ईंट-मीनार है, जो आधार से शिखर तक संकरी होती है।' },
      { en: 'Alternates angular and rounded flutes across the lower tiers, carved with intricate epigraphy.', hi: 'निचली मंजिलों पर कोणीय और गोलाकार पट्टियों पर सूक्ष्म नक्काशी की गई है।' },
      { en: 'The neighboring Iron Pillar has stood for 1,600+ years without corroding due to a protective misawite layer.', hi: 'प्रांगण का लौह स्तंभ १६०० वर्षों से बिना जंग लगे प्राचीन धातु विज्ञान का प्रमाण है।' },
    ],
  },
  'fatehpur-sikri': {
    alignment: { en: 'Buland Darwaza South Cardinal Gateway Axis', hi: 'बुलंद दरवाज़ा दक्षिण दिशा प्रधान अक्ष' },
    material: { en: 'Sikri Red Sandstone with Mortarless Joinery', hi: 'सीकरी लाल बलुआ पत्थर व बिना गारे की चुनाई' },
    acoustic: { en: 'Anup Talao central musical platform acoustics', hi: 'अनूप ताल के केंद्रीय संगीत मंच की ध्वनि तरंगें' },
    facts: [
      { en: 'Buland Darwaza stands 54 meters high, built to commemorate Akbar’s victory in Gujarat in 1573.', hi: '५४ मीटर ऊंचा बुलंद दरवाज़ा १५७३ में गुजरात विजय की स्मृति में बनवाया गया था।' },
      { en: 'Diwan-i-Khas features a singular central carved pillar branching out into 36 serpentine brackets.', hi: 'दीवाने-खास के मध्य में ३६ नक्काशीदार कोष्ठकों वाला एक अद्वितीय केंद्रीय स्तंभ है।' },
      { en: 'The five-tiered Panch Mahal cools its open pavilions using Persian wind-catcher principles.', hi: 'पांच मंजिला पंच महल फ़ारसी पवन-मार्ग सिद्धांत पर खुली हवा से ठंडा रहता है।' },
    ],
  },
}

const timesOfDay = [
  {
    id: 'dawn',
    time: '05:30',
    name: { en: 'Dawn (Bhor)', hi: 'भोर (05:30)' },
    skyClass: 'from-[#4A3B59] via-[#9B5D68] to-[#E8A578]',
    sunColor: '#FFA767',
    overlayFilter: 'sepia(30%) hue-rotate(-20deg) brightness(85%) contrast(105%)',
    sunPosition: 'left-6 top-8',
    glowColor: 'rgba(255, 140, 80, 0.45)',
  },
  {
    id: 'golden',
    time: '06:45',
    name: { en: 'Golden Hour', hi: 'स्वर्णिम प्रहर (06:45)' },
    skyClass: 'from-[#E8A317]/60 via-[#E88E3A]/40 to-[#FCE8D5]',
    sunColor: '#F59E0B',
    overlayFilter: 'sepia(45%) saturate(140%) brightness(105%)',
    sunPosition: 'left-1/4 top-4',
    glowColor: 'rgba(232, 163, 23, 0.55)',
  },
  {
    id: 'midday',
    time: '12:00',
    name: { en: 'High Noon', hi: 'मध्याह्न (12:00)' },
    skyClass: 'from-[#6BA4D9]/40 via-[#B3D6F5]/30 to-[#FBF6EC]',
    sunColor: '#FDE047',
    overlayFilter: 'brightness(112%) contrast(108%) saturate(102%)',
    sunPosition: 'left-1/2 -translate-x-1/2 top-2',
    glowColor: 'rgba(253, 224, 71, 0.6)',
  },
  {
    id: 'dusk',
    time: '18:15',
    name: { en: 'Godhuli (Dusk)', hi: 'गोधूलि (18:15)' },
    skyClass: 'from-[#6E2A3A] via-[#B5452B]/80 to-[#E89E47]',
    sunColor: '#EF4444',
    overlayFilter: 'sepia(50%) hue-rotate(-30deg) saturate(135%) brightness(92%)',
    sunPosition: 'right-1/4 top-6',
    glowColor: 'rgba(181, 69, 43, 0.55)',
  },
  {
    id: 'twilight',
    time: '20:30',
    name: { en: 'Twilight (Sandhya)', hi: 'संध्या (20:30)' },
    skyClass: 'from-[#0F1423] via-[#1E2742] to-[#2E3C61]',
    sunColor: '#E2E8F0',
    overlayFilter: 'brightness(65%) contrast(115%) hue-rotate(190deg) saturate(75%)',
    sunPosition: 'right-8 top-3',
    glowColor: 'rgba(226, 232, 240, 0.4)',
  },
]

export function HeritageSimulator({ lang = 'en' }: { lang?: Lang }) {
  const [selectedId, setSelectedId] = useState('taj-mahal')
  const [timeIndex, setTimeIndex] = useState(1) // Default to Golden Hour
  const [factIndex, setFactIndex] = useState(0)
  const [isPlayingTanpura, setIsPlayingTanpura] = useState(false)

  const audioCtxRef = useRef<AudioContext | null>(null)
  const gainNodeRef = useRef<GainNode | null>(null)

  const activeMonument = monuments.find((m) => m.id === selectedId) ?? monuments[0]
  const activeDetails = architecturalData[activeMonument.id] ?? architecturalData['taj-mahal']
  const activeTime = timesOfDay[timeIndex]

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close().catch(() => {})
      }
    }
  }, [])

  const toggleTanpura = () => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ctx = new AudioCtx()
      audioCtxRef.current = ctx

      const masterGain = ctx.createGain()
      masterGain.gain.setValueAtTime(0.045, ctx.currentTime)
      masterGain.connect(ctx.destination)
      gainNodeRef.current = masterGain

      // Authentic Indian Tanpura Drone: Pa (196 Hz) + Sa (130.81 Hz) + Sa' (261.63 Hz)
      const dronePitches = [130.81, 196.0, 261.63, 392.0]
      dronePitches.forEach((freq, idx) => {
        const osc = ctx.createOscillator()
        const noteGain = ctx.createGain()
        osc.type = idx % 2 === 0 ? 'sine' : 'triangle'
        osc.frequency.setValueAtTime(freq, ctx.currentTime)

        // Subtle acoustic micro-vibrato
        const vibrato = ctx.createOscillator()
        vibrato.frequency.setValueAtTime(0.18 + idx * 0.08, ctx.currentTime)
        const vibGain = ctx.createGain()
        vibGain.gain.setValueAtTime(1.2, ctx.currentTime)
        vibrato.connect(vibGain)
        vibGain.connect(osc.frequency)
        vibrato.start()

        noteGain.gain.setValueAtTime(0.28, ctx.currentTime)
        osc.connect(noteGain)
        noteGain.connect(masterGain)
        osc.start()
      })
    }

    if (isPlayingTanpura) {
      audioCtxRef.current.suspend().catch(() => {})
      setIsPlayingTanpura(false)
    } else {
      audioCtxRef.current.resume().catch(() => {})
      setIsPlayingTanpura(true)
    }
  }

  return (
    <section aria-labelledby="heritage-sim-title" className="px-5 py-10 lg:px-0 lg:py-16">
      <InlayFrame className="w-full">
        <div className="relative overflow-hidden rounded-[14px] bg-[#FBF6EC] p-5 sm:p-7 lg:p-8">
          {/* Subtle jali pattern overlay */}
          <div
            className="pointer-events-none absolute inset-0 opacity-25"
            style={{
              backgroundImage: 'radial-gradient(circle at 10px 10px, rgba(232, 163, 23, 0.22) 1.5px, transparent 1.5px)',
              backgroundSize: '22px 22px',
            }}
            aria-hidden="true"
          />

          {/* Section Header */}
          <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[#E8A317]/25 pb-5">
            <div>
              <div className="inline-flex items-center gap-1.5 rounded-full border border-[#E8A317]/60 bg-[#EADBC0]/50 px-3 py-1 text-xs font-semibold text-[#8F3221]">
                <Sparkles size={13} className="text-[#E8A317] animate-pulse" aria-hidden="true" />
                {lang === 'hi' ? 'इंटरैक्टिव वास्तुकला व सूर्य पथ' : 'Interactive Architectural & Solar Simulator'}
              </div>
              <h2 id="heritage-sim-title" className="fraunces mt-2 text-2xl sm:text-3xl lg:text-4xl text-[#1F1A14]">
                {lang === 'hi' ? 'समय और प्रकाश में भारत की धरोहर' : 'India’s Heritage in Time & Light'}
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-[#5A4E3F]">
                {lang === 'hi'
                  ? 'स्मारक चुनें, सूर्य की दिशा बदलें और ऐतिहासिक संरेखण को साक्षात अनुभव करें।'
                  : 'Select a monument, shift the solar angle, and experience archival alignments in real time.'}
              </p>
            </div>

            {/* Tanpura Drone Acoustic Button */}
            <button
              onClick={toggleTanpura}
              type="button"
              className={`inline-flex min-h-12 items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition-all ${
                isPlayingTanpura
                  ? 'border-[#B5452B] bg-[#B5452B] text-[#FBF6EC] shadow-md shadow-[#B5452B]/20'
                  : 'border-[#E8A317] bg-[#EADBC0]/60 text-[#1F1A14] hover:bg-[#EADBC0]'
              }`}
              aria-label={isPlayingTanpura ? 'Mute ambient tanpura' : 'Play ambient tanpura'}
            >
              {isPlayingTanpura ? <Volume2 size={16} aria-hidden="true" /> : <VolumeX size={16} aria-hidden="true" />}
              <span>{isPlayingTanpura ? (lang === 'hi' ? 'तानपुरा चालू' : 'Tanpura On') : (lang === 'hi' ? 'तानपुरा ध्वनि' : 'Tanpura Sound')}</span>
            </button>
          </div>

          {/* Monument Selector Tabs */}
          <div className="relative z-10 mt-5 flex gap-2 overflow-x-auto pb-2 no-scrollbar" role="tablist" aria-label="Monument selection">
            {monuments.map((m) => {
              const isSelected = m.id === selectedId
              return (
                <button
                  key={m.id}
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => {
                    setSelectedId(m.id)
                    setFactIndex(0)
                  }}
                  className={`flex min-h-11 shrink-0 items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-medium transition-all ${
                    isSelected
                      ? 'border-[#B5452B] bg-[#B5452B] text-[#FBF6EC] shadow-sm'
                      : 'border-[#E8A317]/40 bg-[#EADBC0]/40 text-[#1F1A14] hover:border-[#E8A317] hover:bg-[#EADBC0]/70'
                  }`}
                >
                  <span className="font-semibold">{m.name[lang]}</span>
                  <span className={`text-[10px] rounded px-1.5 py-0.5 ${isSelected ? 'bg-black/20 text-[#FBF6EC]' : 'bg-[#EADBC0] text-[#5A4E3F]'}`}>
                    {m.city}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Main Visualizer Stage */}
          <div className="relative z-10 mt-5 grid gap-6 lg:grid-cols-12 lg:items-center">
            {/* Monument Photo & Dynamic Atmospheric Light Filter */}
            <div className="relative lg:col-span-7 overflow-hidden rounded-2xl border border-[#E8A317]/40 bg-gradient-to-b shadow-xl">
              {/* Dynamic Sky Gradient Container */}
              <div className={`relative h-64 sm:h-80 w-full overflow-hidden bg-gradient-to-b transition-colors duration-700 ${activeTime.skyClass}`}>
                {/* Sun/Moon Celestial Orb */}
                <div
                  className={`absolute ${activeTime.sunPosition} pointer-events-none size-14 sm:size-16 rounded-full transition-all duration-700`}
                  style={{
                    background: `radial-gradient(circle, ${activeTime.sunColor} 0%, rgba(255,255,255,0) 70%)`,
                    boxShadow: `0 0 45px 15px ${activeTime.glowColor}`,
                  }}
                  aria-hidden="true"
                />

                {/* Monument Image with Dynamic Solar Lighting Filter */}
                <div
                  className="relative h-full w-full transition-all duration-700"
                  style={{ filter: activeTime.overlayFilter }}
                >
                  <Image
                    src={activeMonument.image}
                    alt={activeMonument.name[lang]}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 640px, 720px"
                    className="object-cover object-center"
                  />
                  <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#1F1A14]/85 via-[#1F1A14]/30 to-transparent" />
                </div>

                {/* Monument Header Overlay */}
                <div className="absolute inset-x-0 bottom-0 p-4 sm:p-5 text-[#FBF6EC]">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="fraunces text-2xl sm:text-3xl drop-shadow-md">{activeMonument.name[lang]}</p>
                      <p className="text-xs sm:text-sm text-[#FBF6EC]/90 drop-shadow">
                        {activeMonument.city} • {activeMonument.yearBuilt} CE • {lang === 'hi' ? `निर्माता: ${activeMonument.builder}` : `By ${activeMonument.builder}`}
                      </p>
                    </div>
                    <span className="rounded-full border border-[#E8A317]/60 bg-[#1F1A14]/65 px-3 py-1 text-xs font-semibold backdrop-blur text-[#E8A317]">
                      {activeTime.name[lang]}
                    </span>
                  </div>
                </div>
              </div>

              {/* Time-of-Day Slider Controls */}
              <div className="border-t border-[#E8A317]/30 bg-[#FBF6EC]/95 p-4 backdrop-blur">
                <div className="flex items-center justify-between text-xs font-semibold text-[#1F1A14]">
                  <span className="flex items-center gap-1.5 text-[#B5452B]">
                    <Sun size={15} aria-hidden="true" />
                    <span>{lang === 'hi' ? 'सूर्य पथ व प्रकाश चक्र:' : 'Solar Arc & Light Phase:'}</span>
                  </span>
                  <span className="font-mono text-[#8F3221]">{activeTime.time}</span>
                </div>
                <div className="mt-2.5">
                  <input
                    type="range"
                    min={0}
                    max={timesOfDay.length - 1}
                    value={timeIndex}
                    onChange={(e) => setTimeIndex(Number(e.target.value))}
                    className="w-full accent-[#B5452B] cursor-pointer"
                    aria-label={lang === 'hi' ? 'सूर्य का समय' : 'Solar time of day'}
                  />
                  <div className="mt-1 flex justify-between text-[11px] font-medium text-[#5A4E3F]">
                    <span>{lang === 'hi' ? 'भोर' : 'Dawn'}</span>
                    <span>{lang === 'hi' ? 'स्वर्णिम' : 'Golden'}</span>
                    <span>{lang === 'hi' ? 'मध्याह्न' : 'Noon'}</span>
                    <span>{lang === 'hi' ? 'गोधूलि' : 'Dusk'}</span>
                    <span>{lang === 'hi' ? 'संध्या' : 'Night'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Architectural Layer Breakdown & Insights */}
            <div className="lg:col-span-5 flex flex-col justify-between space-y-4">
              {/* Metric Chips */}
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-1">
                <div className="rounded-xl border border-[#E8A317]/40 bg-[#EADBC0]/40 p-3.5">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#B5452B]">
                    <Compass size={13} aria-hidden="true" />
                    <span>{lang === 'hi' ? 'खगोलीय व भौगोलिक संरेखण' : 'Astronomical & Solar Alignment'}</span>
                  </div>
                  <div className="mt-1 text-xs font-medium text-[#1F1A14] leading-relaxed">
                    {activeDetails.alignment[lang]}
                  </div>
                </div>

                <div className="rounded-xl border border-[#E8A317]/40 bg-[#EADBC0]/40 p-3.5">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#B5452B]">
                    <Layers size={13} aria-hidden="true" />
                    <span>{lang === 'hi' ? 'शिल्प सामग्री व शैली' : 'Materials & Masonry'}</span>
                  </div>
                  <div className="mt-1 text-xs font-medium text-[#1F1A14] leading-relaxed">
                    {activeDetails.material[lang]}
                  </div>
                </div>

                <div className="rounded-xl border border-[#E8A317]/40 bg-[#EADBC0]/40 p-3.5 sm:col-span-2 lg:col-span-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#B5452B]">
                    <Volume2 size={13} aria-hidden="true" />
                    <span>{lang === 'hi' ? 'ध्वनि व स्थानिक वास्तुकला' : 'Acoustics & Spatial Resonance'}</span>
                  </div>
                  <div className="mt-1 text-xs font-medium text-[#1F1A14] leading-relaxed">
                    {activeDetails.acoustic[lang]}
                  </div>
                </div>
              </div>

              {/* Architectural Fact Box with Rotator */}
              <div className="rounded-xl border border-[#E8A317]/50 bg-[#EADBC0]/60 p-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 font-semibold text-[#8F3221]">
                    <Info size={14} aria-hidden="true" />
                    <span>{lang === 'hi' ? 'प्रमाणित तथ्य' : 'Documented Fact'}</span>
                  </span>
                  <button
                    onClick={() => setFactIndex((prev) => (prev + 1) % activeDetails.facts.length)}
                    className="inline-flex min-h-8 items-center gap-1 text-xs font-semibold text-[#B5452B] hover:underline"
                    type="button"
                  >
                    <span>{lang === 'hi' ? 'अगला तथ्य' : 'Next fact'}</span>
                    <ArrowRight size={12} aria-hidden="true" />
                  </button>
                </div>
                <p className="mt-2 text-xs sm:text-sm text-[#1F1A14] leading-relaxed">
                  {activeDetails.facts[factIndex][lang]}
                </p>
              </div>

              {/* Action Link to Full Monument Story */}
              <div className="pt-2 flex flex-wrap items-center justify-between gap-3">
                <Link
                  href={`/monument/${activeMonument.id}`}
                  className="link-inverse inline-flex min-h-12 items-center gap-2 rounded-full bg-[#B5452B] px-6 text-xs font-semibold shadow-md transition-transform hover:-translate-y-0.5"
                >
                  <Eye size={15} aria-hidden="true" />
                  <span>{lang === 'hi' ? 'पूरा इतिहास और पांडुलिपि पढ़ें' : 'Read Full Archival Story'}</span>
                </Link>
                <Link
                  href="/plan"
                  className="inline-flex min-h-12 items-center text-xs font-semibold text-[#B5452B] hover:text-[#8F3221]"
                >
                  <span>{lang === 'hi' ? 'इसे अपने मार्ग में जोड़ें' : 'Add to Day Plan'}</span>
                  <ArrowRight size={14} className="ml-1" aria-hidden="true" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </InlayFrame>
    </section>
  )
}
