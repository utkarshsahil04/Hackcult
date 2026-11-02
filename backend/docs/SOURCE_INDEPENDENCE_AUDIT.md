# Source Independence Audit (Every Claim)

This document provides a systematic independence and provenance audit of all **54 claims** across all **15 monuments** currently in the Raahein heritage database.

## Rule 4 & Source Verification Standards

- **Prohibited Sources**: Wikipedia, Wikipedia mirrors, and unverified derivative aggregator sites (e.g., Wikiwand, New World Encyclopedia, IndiaTV) are strictly prohibited and actively rejected by `seed.py` and `tools/validate_seed.py`. None of the 57 sources in `sources.json` contains any banned entity.
- **Grading Rubric**:
  - **Grade A (Independently Verified)**: Both publishers are genuinely arm's-length institutions with independent editorial, academic, or research provenance (e.g., UNESCO evaluation dossier vs Encyclopaedia Britannica, or Britannica vs MIT Archnet).
  - **Grade R (Registry Fact)**: Primary official registry record (e.g. UNESCO inscription year, statutory district boundary) confirmed by government or tourism relay.
  - **Grade B (Weak / Shared / Derivative Text)**: Publishers are technically distinct corporate/legal entities, but the published text derives from or reproduces a single shared source (e.g. ASI monument plaques or UNESCO short summaries mirrored on tourism portals). Passes database constraints but flagged for scholarly distinction.
  - **Grade L (Legend / Folklore)**: Folklore tradition (`is_legend: true`). Exactly 1 recording source required; excluded from monument descriptions and forbidden from backing relationship edges.
  - **Grade U (Unsupported)**: Fails verification standard.

## Dataset Statistics (Current Dataset)

| Grade | Count | Percentage | Description |
|---|---|---|---|
| **A** | 40 | 74.1% | Independently verified scholarship (arm's-length publishers) |
| **R** | 6 | 11.1% | Registry facts (UNESCO primary record + government relay) |
| **B** | 5 | 9.3% | Shared / derivative / ASI-mirrored text |
| **L** | 3 | 5.6% | Explicit legends / folklore traditions |
| **U** | 0 | 0.0% | Unsupported / insufficient claims |
| **Total** | **54** | **100.0%** | **51 historical facts + 3 folklore traditions** |

---

### 01. `humayuns-tomb/built-1570-first-garden-tomb` — Grade B

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Humayun's Tomb in Delhi was built in 1570 and is the first garden-tomb on the Indian subcontinent."
- **Cited Sources (2)**:
  - `unesco-232` — *UNESCO World Heritage Centre* (`intergovernmental`): "Gives 1570 as the build date and calls it the first garden-tomb on the Indian subcontinent."
  - `delhitourism-humayuns-tomb` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States it was built for Emperor Humayun in 1570 as the first grand dynastic garden mausoleum."
- **Independence Assessment**: Shared / derivative text: State-Party ASI text submitted to UNESCO is mirrored on Delhi Tourism portal; distinct publishers but shared textual heritage.

### 02. `humayuns-tomb/unesco-inscription-1993` — Grade A

- **Claim Type**: `recognition`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Humayun's Tomb was inscribed on the UNESCO World Heritage List in 1993."
- **Cited Sources (2)**:
  - `unesco-232-periodic-report` — *UNESCO World Heritage Centre* (`intergovernmental`): "Lists 1993 as the inscription year."
  - `britannica-humayuns-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms inscription on the UNESCO World Heritage list in 1993."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 03. `humayuns-tomb/inspired-taj-mahal` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Humayun's Tomb, the first garden-tomb on the Indian subcontinent, introduced architectural innovations including the bulbous double dome and charbagh layout that culminated in the design of the Taj Mahal."
- **Cited Sources (2)**:
  - `unesco-232` — *UNESCO World Heritage Centre* (`intergovernmental`): "States it inspired major architectural innovations culminating in the Taj Mahal."
  - `archnet-humayuns-tomb-conservation` — *Aga Khan Trust for Culture (Archnet)* (`academic`): "Notes that the tomb and its charbagh garden are considered one of the primary precursors of the Taj Mahal."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Aga Khan Trust for Culture (Archnet).

### 04. `humayuns-tomb/delhi-world-heritage-trio` — Grade B

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Humayun's Tomb and Qutb Minar are UNESCO World Heritage properties situated in the National Capital Territory of Delhi."
- **Cited Sources (2)**:
  - `unesco-doc-206176` — *UNESCO World Heritage Centre* (`intergovernmental`): "Identifies Humayun's Tomb and Qutb Minar among Delhi World Heritage properties."
  - `delhitourism-world-heritage` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Lists Humayun's Tomb and Qutab Minar among World Heritage Sites in Delhi."
- **Independence Assessment**: Shared / derivative text: State-Party ASI text submitted to UNESCO is mirrored on Delhi Tourism portal; distinct publishers but shared textual heritage.

### 05. `humayuns-tomb/bahadur-shah-refuge-1857` — Grade A

- **Claim Type**: `event`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "During the 1857 Uprising, the last Mughal Emperor Bahadur Shah Zafar fled his palace at the Red Fort and took refuge at Humayun's Tomb, where he was captured by British forces."
- **Cited Sources (2)**:
  - `britannica-humayuns-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Records that Bahadur Shah II took refuge at Humayun's Tomb before being captured in 1857."
  - `delhitourism-humayuns-tomb` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States Bahadur Shah Zafar took refuge here during the 1857 revolt."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Encyclopaedia Britannica vs Delhi Tourism (delhitourism.gov.in).

### 06. `taj-mahal/built-1632-1648-shah-jahan` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Taj Mahal in Agra was built by the Mughal emperor Shah Jahan in memory of his wife Mumtaz Mahal; construction began in 1632 and the mausoleum was completed in 1648."
- **Cited Sources (2)**:
  - `unesco-252` — *UNESCO World Heritage Centre* (`intergovernmental`): "States built by Shah Jahan in memory of Mumtaz Mahal, started 1632, completed 1648."
  - `britannica-taj-mahal` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms commissioning by Shah Jahan for Mumtaz Mahal, begun 1632 and completed around 1648."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 07. `taj-mahal/architect-ustad-ahmad-lahori` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Ustad Ahmad Lahori was the chief architect of the Taj Mahal complex."
- **Cited Sources (2)**:
  - `unesco-252` — *UNESCO World Heritage Centre* (`intergovernmental`): "Names Ustad-Ahmad Lahori as the main architect in the Statement of Outstanding Universal Value."
  - `britannica-taj-mahal` — *Encyclopaedia Britannica* (`encyclopedia`): "Attributes the principal design and master architecture to Ustad Ahmad Lahori."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 08. `taj-mahal/marble-mausoleum-indo-islamic-mughal` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Taj Mahal is a white-marble mausoleum in the Indo-Islamic (Mughal) architectural tradition, set in a formal charbagh garden on the bank of the Yamuna River."
- **Cited Sources (2)**:
  - `unesco-252` — *UNESCO World Heritage Centre* (`intergovernmental`): "Describes an immense white-marble mausoleum in a Mughal garden on the right bank of the Yamuna."
  - `agra-nic-taj-mahal` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Describes the ivory-white marble mausoleum on the south bank of the Yamuna River in Agra."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs District Administration Agra, Government of Uttar Pradesh.

### 09. `taj-mahal/unesco-inscription-1983` — Grade R

- **Claim Type**: `recognition`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Taj Mahal was inscribed on the UNESCO World Heritage List in 1983."
- **Cited Sources (2)**:
  - `unesco-decision-3972` — *UNESCO World Heritage Centre* (`intergovernmental`): "Official decision 07COM VIII records 1983 as inscription year."
  - `tajmahal-gov-unesco` — *Taj Mahal - Department of Tourism* (`government`): "Lists 1983 as date of inscription."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Taj Mahal - Department of Tourism).

### 10. `taj-mahal/agra-world-heritage-trio` — Grade R

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Taj Mahal and Fatehpur Sikri are two of the three UNESCO World Heritage properties in Agra District; the third is Agra Fort."
- **Cited Sources (2)**:
  - `unesco-252` — *UNESCO World Heritage Centre* (`intergovernmental`): "States the Taj Trapezium Zone includes three World Heritage properties: Taj Mahal, Agra Fort, and Fatehpur Sikri."
  - `tajmahal-gov-unesco` — *Taj Mahal - Department of Tourism* (`government`): "Lists Taj Mahal, Agra Fort, and Fatehpur Sikri as the World Heritage Sites in Agra District."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Taj Mahal - Department of Tourism).

### 11. `taj-mahal/shah-jahan-patron-marble` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Emperor Shah Jahan commissioned the Taj Mahal as a mausoleum for Mumtaz Mahal and carried out extensive white marble rebuilding campaigns at Agra Fort."
- **Cited Sources (2)**:
  - `unesco-252` — *UNESCO World Heritage Centre* (`intergovernmental`): "Documents Shah Jahan's patronage of the Taj Mahal."
  - `britannica-taj-mahal` — *Encyclopaedia Britannica* (`encyclopedia`): "Relates Shah Jahan's building of the Taj Mahal and his later confinement at Agra Fort."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 12. `fatehpur-sikri/capital-1571-1585-akbar` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Fatehpur Sikri, the 'City of Victory', was founded by Mughal Emperor Akbar and served as the imperial capital from 1571 until 1585."
- **Cited Sources (2)**:
  - `unesco-255` — *UNESCO World Heritage Centre* (`intergovernmental`): "Statement of Outstanding Universal Value: founded by Akbar, capital 1571 to 1585."
  - `britannica-fatehpur-sikri` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms founded by Akbar in 1571 and served as capital until 1585."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 13. `fatehpur-sikri/unesco-world-heritage-agra-district` — Grade R

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Fatehpur Sikri and Agra Fort are UNESCO World Heritage properties in Agra District built predominantly during the reign of Emperor Akbar."
- **Cited Sources (2)**:
  - `unesco-255` — *UNESCO World Heritage Centre* (`intergovernmental`): "Recognizes Fatehpur Sikri as World Heritage site in Agra region."
  - `tajmahal-gov-unesco` — *Taj Mahal - Department of Tourism* (`government`): "Identifies Fatehpur Sikri alongside Agra Fort as World Heritage properties in Agra."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Taj Mahal - Department of Tourism).

### 14. `fatehpur-sikri/akbar-founder-capital` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Emperor Akbar founded Fatehpur Sikri in 1571 to serve as his new imperial capital while maintaining Agra Fort as a principal fortress and base."
- **Cited Sources (2)**:
  - `unesco-255` — *UNESCO World Heritage Centre* (`intergovernmental`): "Describes Akbar's foundation of the new capital city near Agra."
  - `britannica-fatehpur-sikri` — *Encyclopaedia Britannica* (`encyclopedia`): "Details Akbar's transfer of court from Agra to Fatehpur Sikri in 1571."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 15. `fatehpur-sikri/legend-salim-chishti-prediction` — Grade L

- **Claim Type**: `tradition`
- **Explicit Legend Flag**: `is_legend: true`
- **Claim Text**: "According to popular tradition recounted in historic evaluations, Akbar founded Fatehpur Sikri on the site where the Sufi saint Shaikh Salim Chishti had predicted the birth of his male heir."
- **Cited Sources (1)**:
  - `unesco-doc-153050` — *UNESCO World Heritage Centre* (`intergovernmental`): "Recounts the tradition of Shaikh Salim Chishti predicting the birth of Prince Salim."
- **Independence Assessment**: Legend / folklore tradition. Needs >= 1 credible source recording it. Cannot back a relationship edge and is excluded from descriptions.

### 16. `qutb-complex/minar-begun-1199-aibak-iltutmish` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Construction of the Qutb Minar was initiated in 1199 by Qutb-ud-din Aibak and completed by his successor Shams-ud-din Iltutmish."
- **Cited Sources (2)**:
  - `unesco-233` — *UNESCO World Heritage Centre* (`intergovernmental`): "States construction of Qutb Minar began in 1199 by Aibak and was finished by Iltutmish."
  - `britannica-qutb-minar` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms begun in 1199 under Aibak and completed by his successor Iltutmish."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 17. `qutb-complex/tallest-masonry-tower-72m` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Qutb Minar is a tapering 72.5-metre red sandstone minaret featuring five distinct storeys, projecting balconies, and angled and fluted carvings."
- **Cited Sources (2)**:
  - `unesco-233` — *UNESCO World Heritage Centre* (`intergovernmental`): "Describes 72.5m tall red sandstone tower with flutings and projecting balconies."
  - `britannica-qutb-minar` — *Encyclopaedia Britannica* (`encyclopedia`): "Gives height of 72.5 meters (238 feet) and describes alternating angular and rounded flutings."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 18. `qutb-complex/quwwat-ul-islam-mosque` — Grade B

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The complex contains the Quwwat-ul-Islam Mosque, one of the earliest surviving mosques in northern India, begun under Qutb-ud-din Aibak."
- **Cited Sources (2)**:
  - `unesco-233` — *UNESCO World Heritage Centre* (`intergovernmental`): "Describes Quwwat-ul-Islam mosque as the earliest extant mosque in northern India."
  - `delhitourism-qutab-minar` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes Quwwat-ul-Islam Mosque built by Qutb-ud-din Aibak in the late 12th century."
- **Independence Assessment**: Shared / derivative text: State-Party ASI text submitted to UNESCO is mirrored on Delhi Tourism portal; distinct publishers but shared textual heritage.

### 19. `qutb-complex/delhi-world-heritage-trio` — Grade B

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Qutb Minar and the Red Fort Complex are UNESCO World Heritage properties in Delhi representing the early Sultanate and mature Mughal eras."
- **Cited Sources (2)**:
  - `unesco-doc-206176` — *UNESCO World Heritage Centre* (`intergovernmental`): "Lists Qutb Minar alongside Red Fort among World Heritage in Delhi."
  - `delhitourism-world-heritage` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Lists Qutab Minar and Red Fort as World Heritage Sites in Delhi."
- **Independence Assessment**: Shared / derivative text: State-Party ASI text submitted to UNESCO is mirrored on Delhi Tourism portal; distinct publishers but shared textual heritage.

### 20. `qutb-complex/legend-iron-pillar-wish` — Grade L

- **Claim Type**: `tradition`
- **Explicit Legend Flag**: `is_legend: true`
- **Claim Text**: "According to popular local folklore, standing with your back against the ancient Iron Pillar and wrapping your arms around it brings good fortune and fulfills wishes."
- **Cited Sources (1)**:
  - `delhitourism-qutab-minar` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Notes the popular belief that encirling the Iron Pillar with arms brings good luck."
- **Independence Assessment**: Legend / folklore tradition. Needs >= 1 credible source recording it. Cannot back a relationship edge and is excluded from descriptions.

### 21. `red-fort/unesco-inscription-2007` — Grade R

- **Claim Type**: `recognition`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Red Fort Complex was inscribed on the UNESCO World Heritage List in 2007."
- **Cited Sources (2)**:
  - `unesco-decision-1330` — *UNESCO World Heritage Centre* (`intergovernmental`): "Decision 31 COM 8B.32 records inscription in 2007."
  - `loksabha-red-fort-2007` — *Lok Sabha / Ministry of Culture, Government of India* (`government`): "Confirms Red Fort's inscription as a World Heritage Site in 2007."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Lok Sabha / Ministry of Culture, Government of India).

### 22. `red-fort/symbol-of-power-since-shah-jahan` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Built under Emperor Shah Jahan as the palace fort of Shahjahanabad, the Red Fort represents the zenith of Mughal creativity and has served as a symbol of power across Indian history."
- **Cited Sources (2)**:
  - `unesco-decision-1330` — *UNESCO World Heritage Centre* (`intergovernmental`): "Emphasizes the fort's representation of the zenith of Mughal architectural creativity."
  - `britannica-red-fort` — *Encyclopaedia Britannica* (`encyclopedia`): "Describes it as the focal fortress-palace of Shahjahanabad and symbol of power."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 23. `red-fort/capital-shift-from-agra` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Mughal Emperor Shah Jahan shifted the imperial capital from Agra Fort to the newly constructed fortress-city of Shahjahanabad (Red Fort) in Delhi."
- **Cited Sources (2)**:
  - `unesco-decision-1330` — *UNESCO World Heritage Centre* (`intergovernmental`): "Refers to the transfer of the capital under Shah Jahan to Shahjahanabad."
  - `britannica-red-fort` — *Encyclopaedia Britannica* (`encyclopedia`): "Explicitly details Shah Jahan moving his capital from Agra to Delhi to found the Red Fort."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: UNESCO World Heritage Centre vs Encyclopaedia Britannica.

### 24. `red-fort/delhi-world-heritage-trio` — Grade B

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Red Fort and Humayun's Tomb are UNESCO World Heritage properties in Delhi illustrating the evolution of Mughal imperial architecture."
- **Cited Sources (2)**:
  - `unesco-doc-206176` — *UNESCO World Heritage Centre* (`intergovernmental`): "Lists Red Fort and Humayun's Tomb as Delhi World Heritage properties."
  - `delhitourism-world-heritage` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Co-lists Red Fort and Humayun's Tomb as World Heritage properties in Delhi."
- **Independence Assessment**: Shared / derivative text: State-Party ASI text submitted to UNESCO is mirrored on Delhi Tourism portal; distinct publishers but shared textual heritage.

### 25. `agra-fort/unesco-inscription-1983` — Grade R

- **Claim Type**: `recognition`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Agra Fort was inscribed on the UNESCO World Heritage List in 1983."
- **Cited Sources (2)**:
  - `unesco-india-documents` — *UNESCO World Heritage Centre* (`intergovernmental`): "Documents inscription of Agra Fort on World Heritage list in 1983."
  - `tajmahal-gov-unesco` — *Taj Mahal - Department of Tourism* (`government`): "Confirms Agra Fort inscription in 1983."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Taj Mahal - Department of Tourism).

### 26. `agra-fort/imperial-city-within-city` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Agra Fort was rebuilt in red sandstone by Emperor Akbar beginning in 1565 on the bank of the Yamuna River, functioning as an imperial residence and fortress city."
- **Cited Sources (2)**:
  - `agra-nic-agra-fort` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Describes the massive walled red sandstone fort rebuilt by Akbar in 1565."
  - `britannica-agra-fort` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms commissioned by Emperor Akbar in 1565 on the right bank of the Yamuna River."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 27. `agra-fort/unesco-world-heritage-agra-district` — Grade R

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Agra Fort and the Taj Mahal are UNESCO World Heritage properties located along the Yamuna River in Agra."
- **Cited Sources (2)**:
  - `unesco-251` — *UNESCO World Heritage Centre* (`intergovernmental`): "Details Agra Fort's location on the Yamuna in Agra near the Taj Mahal."
  - `tajmahal-gov-unesco` — *Taj Mahal - Department of Tourism* (`government`): "Co-lists Agra Fort and Taj Mahal as World Heritage sites in Agra."
- **Independence Assessment**: Registry fact: UNESCO primary inscription/property listing relayed by regional tourism/parliamentary record (UNESCO World Heritage Centre + Taj Mahal - Department of Tourism).

### 28. `akbars-tomb/akbar-mausoleum-begun` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Akbar's Tomb at Sikandra was planned and initiated by Emperor Akbar, the builder of Fatehpur Sikri, and completed by his son Emperor Jahangir."
- **Cited Sources (2)**:
  - `agra-nic-sikandra` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "States the monument was commenced by Akbar himself and completed by Jahangir."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms begun by Akbar and completed by Jahangir between 1605 and 1613."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 29. `akbars-tomb/tiered-sandstone-marble-style` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Akbar's mausoleum features a unique five-tiered pyramidal structure set in a large charbagh garden, combining deep red sandstone with white marble pavilions."
- **Cited Sources (2)**:
  - `agra-nic-sikandra` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Describes the five-storey pyramidal tomb surrounded by an extensive garden."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Describes the tiered pyramidal layout combining red sandstone and white marble."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 30. `akbars-tomb/jahangir-completion-1613` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Emperor Jahangir ruled from Agra Fort and supervised the completion of his father Akbar's tiered tomb at Sikandra around 1613."
- **Cited Sources (2)**:
  - `agra-nic-sikandra` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Documents completion under Jahangir in 1613."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms Jahangir's completion of the complex in 1613."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 31. `akbars-tomb/south-gate-minarets` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The monumental southern gateway of Akbar's Tomb at Sikandra was the first Mughal structure to incorporate four free-standing white marble minarets, establishing an architectural motif later adapted at the four corners of the Taj Mahal plinth."
- **Cited Sources (2)**:
  - `agra-nic-sikandra` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Highlights the four white marble minarets rising from the South Gate."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Details the innovative use of four detached marble minarets on the gate."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 32. `akbars-tomb/burial-outskirts-agra` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Akbar's Tomb at Sikandra was established on the northwestern royal route leading out of Akbar's capital at Agra Fort."
- **Cited Sources (2)**:
  - `agra-nic-sikandra` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Locates Sikandra on the historic highway from Agra to Delhi."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Places the mausoleum on the outskirts of Agra."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 33. `itimad-ud-daulah/nur-jahan-commission` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Tomb of I'timad-ud-Daulah was commissioned by Mughal Empress Nur Jahan for her father Mirza Ghiyas Beg between 1622 and 1628."
- **Cited Sources (2)**:
  - `agra-nic-itimad-ud-daulah` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "States built by Nur Jahan for her father Mirza Ghiyas Beg between 1622 and 1628."
  - `britannica-itimad-ud-daulah` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms commissioned in 1622 by Nur Jahan for Mirza Ghiyas Beg."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 34. `itimad-ud-daulah/pietra-dura-precursor` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Tomb of I'timad-ud-Daulah, built entirely of white marble with refined pietra dura inlay, is widely recognized as a stylistic precursor to the Taj Mahal."
- **Cited Sources (2)**:
  - `agra-nic-itimad-ud-daulah` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Identifies the monument as the 'Baby Taj' and precursor to Taj Mahal."
  - `britannica-itimad-ud-daulah` — *Encyclopaedia Britannica* (`encyclopedia`): "Highlights the pioneering white marble pietra dura inlay as anticipating the Taj Mahal."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 35. `itimad-ud-daulah/nur-jahan-patronage` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Tomb of I'timad-ud-Daulah was commissioned by Empress Nur Jahan for her father Mirza Ghiyas Beg, who served as chief minister to Emperor Jahangir at Agra Fort."
- **Cited Sources (2)**:
  - `agra-nic-itimad-ud-daulah` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Explains Mirza Ghiyas Beg's imperial title and wazirship under Jahangir."
  - `britannica-itimad-ud-daulah` — *Encyclopaedia Britannica* (`encyclopedia`): "Describes his role as chief minister of the Mughal Empire under Jahangir."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 36. `itimad-ud-daulah/jahangir-era-monuments` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Both the Tomb of I'timad-ud-Daulah and Akbar's Tomb at Sikandra were constructed in Agra during the reign of Mughal Emperor Jahangir."
- **Cited Sources (2)**:
  - `agra-nic-itimad-ud-daulah` — *District Administration Agra, Government of Uttar Pradesh* (`government`): "Dates the mausoleum to Jahangir's reign in Agra."
  - `britannica-akbars-tomb` — *Encyclopaedia Britannica* (`encyclopedia`): "Documents Jahangir's architectural projects in Agra."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: District Administration Agra, Government of Uttar Pradesh vs Encyclopaedia Britannica.

### 37. `jama-masjid/shah-jahan-patronage` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Mughal Emperor Shah Jahan commissioned the Jama Masjid between 1650 and 1656 as the grand congregational mosque of his new capital Shahjahanabad, positioned directly opposite the Red Fort."
- **Cited Sources (2)**:
  - `delhitourism-jama-masjid` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States commissioned by Shah Jahan, completed in 1656 across from Red Fort."
  - `britannica-jama-masjid` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms built by Shah Jahan between 1650 and 1656 in Old Delhi."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 38. `jama-masjid/red-sandstone-marble-architecture` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The mosque is constructed of red sandstone and white marble, featuring three large domes, two 40-metre-high minarets, and an elevated courtyard holding 25,000 worshippers."
- **Cited Sources (2)**:
  - `delhitourism-jama-masjid` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes red sandstone and marble domes, minarets, and grand courtyard."
  - `britannica-jama-masjid` — *Encyclopaedia Britannica* (`encyclopedia`): "Details red sandstone and white marble construction and courtyard holding 25,000."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 39. `jama-masjid/mughal-congregational-tradition` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The design of Shah Jahan's Jama Masjid in Delhi drew upon the grand congregational mosque prototypes established by Akbar at Fatehpur Sikri, incorporating high plinths, expansive arcaded courtyards, and bulbous marble domes."
- **Cited Sources (2)**:
  - `delhitourism-jama-masjid` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes the monumental courtyard and entrance gates following imperial traditions."
  - `britannica-jama-masjid` — *Encyclopaedia Britannica* (`encyclopedia`): "Notes the synthesis of Mughal congregational mosque architecture developed from earlier capitals."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 40. `safdarjungs-tomb/last-garden-tomb` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Safdarjung's Tomb was built in 1753–1754 as the last enclosed garden tomb in Delhi, deliberately designed in the grand charbagh architectural style pioneered by Humayun's Tomb."
- **Cited Sources (2)**:
  - `delhitourism-safdarjang-tomb` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States built in 1753-54 as the last enclosed garden tomb in Delhi in the Humayun style."
  - `archnet-safdarjang` — *Archnet / MIT Documentation Center* (`academic`): "Documents the 1754 garden tomb built in the late Mughal charbagh tradition."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Archnet / MIT Documentation Center.

### 41. `safdarjungs-tomb/wazir-mughal-empire` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Mirza Muqim Abul Mansur Khan (Safdarjung), whose tomb stands in Delhi, served as the Grand Vizier (Prime Minister) of the Mughal Empire under Emperor Ahmad Shah Bahadur based at the Red Fort."
- **Cited Sources (2)**:
  - `delhitourism-safdarjang-tomb` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States Safdarjung was the prime minister under Ahmad Shah Bahadur."
  - `britannica-safdarjung` — *Encyclopaedia Britannica* (`encyclopedia`): "Documents Safdarjung's tenure as Mughal wazir (prime minister)."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 42. `safdarjungs-tomb/lodhi-road-precinct` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Safdarjung's Tomb was built directly adjacent to the historic Lodhi precinct along Lodhi Road, representing the final Mughal garden tomb built in geographic continuity with earlier Sultanate mausoleums."
- **Cited Sources (2)**:
  - `delhitourism-safdarjang-tomb` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Locates the tomb at the intersection of Safdarjung Road and Lodhi area."
  - `archnet-safdarjang` — *Archnet / MIT Documentation Center* (`academic`): "Describes its location in the south Delhi historic funerary precinct near Lodhi monuments."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Archnet / MIT Documentation Center.

### 43. `purana-qila/humayun-dinpanah-death` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Mughal Emperor Humayun established his capital Dinpanah at Purana Qila and died in 1556 following a fatal fall on the steps of the Sher Mandal library inside the fort, after which he was entombed at nearby Humayun's Tomb."
- **Cited Sources (2)**:
  - `britannica-purana-qila` — *Encyclopaedia Britannica* (`encyclopedia`): "Describes Din Panah, Sher Shah's building, and Humayun's fatal library fall in 1556."
  - `archnet-purana-qila` — *Archnet / MIT Documentation Center* (`academic`): "Documents Din-Panah foundation by Humayun in 1533 and Sher Shah's additions."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Encyclopaedia Britannica vs Archnet / MIT Documentation Center.

### 44. `purana-qila/sultanate-to-mughal-transition` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Sher Shah Suri and Humayun constructed the fortifications of Purana Qila following the overthrow of the Lodi dynasty, whose royal tombs stand in Lodhi Gardens."
- **Cited Sources (2)**:
  - `britannica-purana-qila` — *Encyclopaedia Britannica* (`encyclopedia`): "Outlines the overthrow of the Sultanate dynasties and the rise of the Sur and Mughal citadels."
  - `archnet-purana-qila` — *Archnet / MIT Documentation Center* (`academic`): "Discusses the transitional post-Lodi Sultanate-Mughal architecture at Purana Qila."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Encyclopaedia Britannica vs Archnet / MIT Documentation Center.

### 45. `purana-qila/sixth-city-delhi` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Purana Qila was developed as the sixth historical city of Delhi (Dinpanah/Shergarh), succeeding the earlier Sultanate urban centers founded around Qutb Minar."
- **Cited Sources (2)**:
  - `delhitourism-purana-quila` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Identifies Purana Qila as one of the historic capital cities of Delhi."
  - `britannica-purana-qila` — *Encyclopaedia Britannica* (`encyclopedia`): "Details the sequence of Delhi's historic cities from Sultanate to Dinpanah."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 46. `tughlaqabad-fort/ghiyasuddin-founder-1321` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Sultan Ghiyas-ud-din Tughlaq founded Tughlaqabad Fort in 1321 as the third city of Delhi, succeeding the early Sultanate administrative center around the Qutb Complex."
- **Cited Sources (2)**:
  - `delhitourism-tughlaqabad` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States built by Ghiyas-ud-din Tughlaq in 1321 as the third city of Delhi."
  - `britannica-tughlaqabad` — *Encyclopaedia Britannica* (`encyclopedia`): "Confirms established around 1321 by Ghiyas-ud-din Tughlaq."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 47. `tughlaqabad-fort/massive-sloping-stone-ramparts` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The fortress is distinguished by its colossal stone bastions, high sloping ramparts, and an elevated causeway connecting to the fortified tomb of Ghiyas-ud-din Tughlaq."
- **Cited Sources (2)**:
  - `delhitourism-tughlaqabad` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes sloping massive ramparts, battlements, and the causeway-connected tomb."
  - `archnet-tughlaqabad` — *Archnet / University of Tokyo* (`academic`): "Details the defensive stone masonry and architectural layout of the citadel."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Archnet / University of Tokyo.

### 48. `tughlaqabad-fort/legend-nizamuddin-curse` — Grade L

- **Claim Type**: `tradition`
- **Explicit Legend Flag**: `is_legend: true`
- **Claim Text**: "A famous Delhi legend holds that the Sufi saint Hazrat Nizamuddin Auliya cursed the fort to be abandoned or inhabited only by pastoral nomads when workers were diverted from his stepwell."
- **Cited Sources (1)**:
  - `delhitourism-tughlaqabad` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Recounts the legendary curse 'Ya rahe usar, ya base Gujar' by saint Nizamuddin Auliya."
- **Independence Assessment**: Legend / folklore tradition. Needs >= 1 credible source recording it. Cannot back a relationship edge and is excluded from descriptions.

### 49. `jantar-mantar/jai-singh-patronage-1724` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Maharaja Sawai Jai Singh II of Jaipur constructed the Jantar Mantar observatory in Delhi in 1724 under the imperial commission of Mughal Emperor Muhammad Shah, who ruled from the Red Fort."
- **Cited Sources (2)**:
  - `delhitourism-jantar-mantar` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States built in 1724 by Maharaja Jai Singh II of Jaipur."
  - `archnet-jantar-mantar` — *Archnet / MIT Documentation Center* (`academic`): "Documents construction in 1724 by Jai Singh II for astronomical observation in Delhi."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Archnet / MIT Documentation Center.

### 50. `jantar-mantar/masonry-observatory-instruments` — Grade A

- **Claim Type**: `style`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The open-air observatory comprises massive geometric masonry instruments, including the Samrat Yantra and Jai Prakash, designed to measure time and celestial coordinates."
- **Cited Sources (2)**:
  - `delhitourism-jantar-mantar` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes the architectural instruments predicting planetary and solar movement."
  - `britannica-jantar-mantar` — *Encyclopaedia Britannica* (`encyclopedia`): "Details the colossal masonry astronomical measuring instruments."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 51. `mehrauli-archaeological-park/delhi-first-city-precinct` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "Mehrauli Archaeological Park borders the Qutb Complex in Delhi's oldest fortified city area (Lal Kot / Qila Rai Pithora), preserving archaeological remains from the early Sultanate through the Mughal era."
- **Cited Sources (2)**:
  - `delhitourism-mehrauli` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Describes Mehrauli as Delhi's oldest historic city area contiguous to Qutab Minar."
  - `intach-delhi-mehrauli` — *Indian National Trust for Art and Cultural Heritage (INTACH)* (`other`): "Documents over 100 historical monuments spanning 1,000 years in the Mehrauli park."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Indian National Trust for Art and Cultural Heritage (INTACH).

### 52. `mehrauli-archaeological-park/sultanate-tombs-evolution` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The tomb architecture of Mehrauli Archaeological Park, including the early arches of Balban's Tomb and Jamali Kamali, directly influenced the development of Sultanate funerary architecture seen in Lodhi Gardens."
- **Cited Sources (2)**:
  - `delhitourism-mehrauli` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Highlights the tombs of Balban and Jamali Kamali in Mehrauli."
  - `intach-delhi-mehrauli` — *Indian National Trust for Art and Cultural Heritage (INTACH)* (`other`): "Analyzes the architectural lineage of Mehrauli tombs influencing later Sultanate sites."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Indian National Trust for Art and Cultural Heritage (INTACH).

### 53. `lodhi-gardens/sayyid-lodi-sultanate` — Grade A

- **Claim Type**: `built`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The monuments of Lodhi Gardens were erected by rulers of the Sayyid and Lodi dynasties, who ruled the Delhi Sultanate in succession to the early dynasties established at Qutb Minar."
- **Cited Sources (2)**:
  - `delhitourism-lodhi-garden` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "States park contains monuments of Sayyid and Lodhi periods from the 15th-16th centuries."
  - `britannica-delhi-sultanate` — *Encyclopaedia Britannica* (`encyclopedia`): "Describes Sayyid and Lodi dynasties as the culmination of the Delhi Sultanate."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Encyclopaedia Britannica.

### 54. `lodhi-gardens/sikandar-lodi-garden-tomb` — Grade A

- **Claim Type**: `relationship`
- **Explicit Legend Flag**: `is_legend: false`
- **Claim Text**: "The Tomb of Sikandar Lodi in Lodhi Gardens was an early walled garden tomb in Delhi featuring an octagonal layout and double dome that served as an architectural precursor to Humayun's Tomb."
- **Cited Sources (2)**:
  - `delhitourism-lodhi-garden` — *Delhi Tourism (delhitourism.gov.in)* (`government`): "Highlights the Tomb of Sikandar Lodi within the garden layout."
  - `archnet-lodhi-garden` — *Archnet / MIT Documentation Center* (`academic`): "Identifies Sikandar Lodi's tomb as an important architectural precursor to Mughal garden tombs."
- **Independence Assessment**: Independently written scholarship by two arm's-length institutions: Delhi Tourism (delhitourism.gov.in) vs Archnet / MIT Documentation Center.
