// What each marked part of a 3D model is. These describe building forms in general, not the history of a
// particular monument, because historical claims need two independent sources and live in the database.
type Text = { en: string; hi: string }

const part = (enTitle: string, hiTitle: string, en: string, hi: string) => ({ title: { en: enTitle, hi: hiTitle } as Text, desc: { en, hi } as Text })

export const architectureParts = {
  dome: part('Dome', 'गुंबद', 'The rounded roof that crowns the building and makes it recognisable from far away.', 'इमारत के ऊपर का गोल शिखर, जो उसे दूर से ही पहचान दिलाता है।'),
  pishtaq: part('Arched portal (pishtaq)', 'पिश्ताक (भव्य मेहराब)', 'A tall arch set inside a rectangular frame. It marks the most important face of the building.', 'आयताकार चौखटे में बनी ऊंची मेहराब, जो इमारत के सबसे महत्वपूर्ण भाग को उभारती है।'),
  minaret: part('Minaret', 'मीनार', 'A slender tower that frames the main building and draws the eye upward.', 'पतली ऊंची मीनार, जो मुख्य इमारत को घेरती है और नज़र को ऊपर ले जाती है।'),
  plinth: part('Raised platform', 'ऊंचा चबूतरा', 'A broad terrace that lifts the building above the ground around it.', 'चौड़ा चबूतरा, जो इमारत को आसपास की ज़मीन से ऊपर उठाता है।'),
  arcade: part('Arcade', 'मेहराबों की कतार', 'A row of arches carried on piers, giving shade and a steady rhythm to the wall.', 'खंभों पर टिकी मेहराबों की कतार, जो छाया देती है और दीवार को लय देती है।'),
  chhatri: part('Chhatri', 'छतरी', 'A small domed pavilion on slender pillars, often placed on roofs and at corners.', 'पतले स्तंभों पर टिका छोटा गुंबददार मंडप, जो अक्सर छतों और कोनों पर बनता है।'),
  charbagh: part('Charbagh garden', 'चारबाग', 'A garden divided into four parts by raised paths and water channels.', 'ऐसा बगीचा जिसे ऊंचे रास्ते और जल नालियां चार भागों में बांटते हैं।'),
  garden: part('Garden setting', 'बगीचा', 'Lawns and trees that surround the buildings and shape how visitors approach them.', 'लॉन और पेड़, जो इमारतों को घेरते हैं और उन तक पहुंचने का अनुभव गढ़ते हैं।'),
  water: part('Water feature', 'जल संरचना', 'Still water that cools the air and reflects the architecture around it.', 'शांत जल, जो हवा को ठंडा करता है और आसपास की वास्तुकला को प्रतिबिंबित करता है।'),
  gateway: part('Gateway', 'प्रवेश द्वार', 'The monumental entrance through which visitors first reach the site.', 'भव्य प्रवेश, जिससे होकर आगंतुक सबसे पहले इस स्थल तक पहुंचते हैं।'),
  rampart: part('Rampart', 'परकोटा', 'A thick defensive wall, topped with battlements that sheltered the people guarding it.', 'मोटी रक्षात्मक दीवार, जिसके ऊपर बने कंगूरे पहरेदारों को आड़ देते थे।'),
  bastion: part('Bastion', 'बुर्ज', 'A rounded tower that projects from the wall and gives a wider view along it.', 'दीवार से बाहर निकला गोल बुर्ज, जिससे दीवार के साथ दूर तक दिखाई देता है।'),
  palace: part('Palace pavilion', 'महल का मंडप', 'Living and ceremonial rooms set within the protected interior of the site.', 'स्थल के सुरक्षित भीतरी भाग में बने निवास और समारोह के कक्ष।'),
  hall: part('Pillared hall', 'स्तंभों वाला सभागार', 'A hall whose roof rests on rows of pillars, open to light and moving air.', 'ऐसा सभागार जिसकी छत स्तंभों की कतारों पर टिकी है और जिसमें रोशनी व हवा आती है।'),
  courtyard: part('Courtyard', 'आंगन', 'An open space enclosed by buildings, where people can gather.', 'इमारतों से घिरा खुला स्थान, जहां लोग एकत्र हो सकते हैं।'),
  prayerHall: part('Prayer hall', 'नमाज़ कक्ष', 'The covered hall along one side of a mosque, where worshippers gather in rows.', 'मस्जिद के एक ओर बना ढका हुआ कक्ष, जहां नमाज़ी कतारों में इकट्ठा होते हैं।'),
  tower: part('Tiered tower', 'बहुमंजिला मीनार', 'A tower built in stages, each one narrower than the stage below it.', 'चरणों में बनी मीनार, जिसका हर चरण नीचे वाले से संकरा है।'),
  balcony: part('Balcony', 'छज्जा', 'A projecting gallery that rings the structure, carried on carved brackets.', 'बाहर निकली दीर्घा, जो नक्काशीदार कोष्ठकों पर टिकी संरचना को घेरती है।'),
  pillar: part('Standing pillar', 'स्तंभ', 'A free-standing column, set up as a monument in its own right.', 'अकेला खड़ा स्तंभ, जो स्वयं में एक स्मारक है।'),
  ruin: part('Surviving walls', 'बचे हुए अवशेष', 'Remains of walls and arches that show how the structure was built.', 'दीवारों और मेहराबों के अवशेष, जो बताते हैं कि यह संरचना कैसे बनी थी।'),
  tomb: part('Tomb chamber', 'मकबरे का कक्ष', 'The main building of a mausoleum, which holds the burial.', 'मकबरे की मुख्य इमारत, जिसमें कब्र होती है।'),
  tiers: part('Stepped storeys', 'क्रमिक मंजिलें', 'Floors that become smaller as they rise, giving a pyramid-like outline.', 'ऊपर जाते हुए छोटी होती मंजिलें, जो पिरामिड जैसी आकृति बनाती हैं।'),
  jali: part('Jali screen', 'जाली', 'A pierced stone screen that lets in light and air while filtering the view.', 'छेददार पत्थर की जाली, जो रोशनी और हवा आने देती है और दृश्य को ढकती है।'),
  steps: part('Stepped descent', 'सीढ़ियां', 'Long flights of steps that lead down to the water, whatever its level.', 'लंबी सीढ़ियां, जो जलस्तर चाहे जो हो, पानी तक ले जाती हैं।'),
  tank: part('Water tank', 'जलाशय', 'A large built reservoir that stored water for the people around it.', 'बड़ा निर्मित जलाशय, जिसमें आसपास के लोगों के लिए पानी जमा होता था।'),
  memorialArch: part('Memorial arch', 'स्मारक मेहराब', 'One monumental arch that stands alone as a place of remembrance.', 'अकेली भव्य मेहराब, जो स्मरण का स्थल है।'),
  memorial: part('Memorial platform', 'समाधि मंच', 'A plain square platform that marks the place of remembrance.', 'सादा चौकोर मंच, जो स्मरण के स्थान को चिह्नित करता है।'),
  flame: part('Flame', 'ज्योति', 'A burning flame kept as a sign of remembrance.', 'स्मरण के प्रतीक के रूप में जलती ज्योति।'),
  enclosure: part('Enclosure wall', 'घेरने वाली दीवार', 'A low wall that separates the quiet inner space from its surroundings.', 'नीची दीवार, जो शांत भीतरी स्थान को आसपास से अलग करती है।'),
  petals: part('Petal shells', 'पंखुड़ियां', 'Curved shells arranged in rings, which give the building the form of a flower.', 'छल्लों में सजे घुमावदार आवरण, जो इमारत को फूल का रूप देते हैं।'),
  portico: part('Columned portico', 'स्तंभों वाला द्वारमंडप', 'A row of columns that shelters and announces the main entrance.', 'स्तंभों की कतार, जो मुख्य प्रवेश को छाया देती है और उसे उभारती है।'),
  wings: part('Long wings', 'लंबे पार्श्व भाग', 'Ranges of rooms that stretch out on both sides of the central block.', 'कमरों की कतारें, जो मध्य भाग के दोनों ओर फैली हैं।'),
  gnomon: part('Gnomon', 'शंकु', 'A large triangular wall whose shadow is used to read the position of the sun.', 'बड़ी त्रिकोणीय दीवार, जिसकी छाया से सूर्य की स्थिति पढ़ी जाती है।'),
  dial: part('Measuring scales', 'मापक वृत्त', 'Curved surfaces on which a shadow falls against marked scales.', 'घुमावदार सतहें, जिन पर छाया अंकित पैमानों पर पड़ती है।'),
  shrine: part('Central shrine', 'मुख्य मंदिर', 'The heart of the complex, rising in carved tiers above its surroundings.', 'परिसर का केंद्र, जो नक्काशीदार स्तरों में ऊपर उठता है।'),
  dargah: part('Shrine', 'दरगाह', 'The building at the centre of the site, where visitors come to pay their respects.', 'स्थल के केंद्र में बनी इमारत, जहां लोग श्रद्धा व्यक्त करने आते हैं।'),
  colonnade: part('Surrounding colonnade', 'परिक्रमा', 'A covered walkway on columns that circles the central building.', 'स्तंभों पर बना ढका रास्ता, जो मुख्य इमारत के चारों ओर जाता है।'),
  rooftopDomes: part('Rooftop domes', 'छत के छोटे गुंबद', 'Many small domes, one over each bay of the roof.', 'कई छोटे गुंबद, छत के हर खंड पर एक।'),
} as const

export type PartId = keyof typeof architectureParts
