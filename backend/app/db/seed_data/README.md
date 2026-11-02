# Seed Data (Raahein Heritage Discovery)

Pure data for `python -m app.db.seed`. No application logic lives here.

| File | Contents | Count |
|---|---|---|
| `sources.json` | `key`, `url`, `title`, `publisher`, `source_type`. Only authoritative pages actually opened and read. | 57 |
| `monuments.json` | Slug, name, coordinates (+ `coordinates_source`), era, architectural style, location, city. No free-text description: descriptions are deterministically assembled from sourced claims. | 15 |
| `claims.json` | Sourced historical statements, each with `sources: [{source, note}]`. `note` is a paraphrase from that source. Legends are flagged `is_legend: true`. | 54 |
| `relationships.json` | Verified relationship edges. Each edge hangs off a verified non-legend `claim` (`<monument-slug>/<claim-key>`) concerning one of its endpoints. | 32 |

---

## Status against Issue #3 Targets

| Target | Required | Delivered | Status |
|---|---|---|---|
| Initial Delhi–Agra Monuments | Exactly 15 | **15** (Humayun's Tomb, Taj Mahal, Fatehpur Sikri, Qutb Complex, Red Fort, Agra Fort, Akbar's Tomb, Tomb of I'timad-ud-Daulah, Jama Masjid, Safdarjung's Tomb, Purana Qila, Tughlaqabad Fort, Jantar Mantar, Mehrauli Archaeological Park, Lodhi Gardens) | **COMPLETED** |
| Verified Relationship Edges | At least 30 | **32** (architectural influence, same patron, same dynasty, successor of, capital relationship, burial association, historical event, co-located World Heritage) | **COMPLETED** |
| Two-Independent-Publisher Rule | >= 2 publishers per fact | **100% compliant** across all 51 historical facts (3 authentic folklore legends recorded with source) | **COMPLETED** |
| Explicit `is_legend` Booleans | All claims | **100% compliant** (51 facts with `false`, 3 folklore traditions with `true`) | **COMPLETED** |
| Seed Idempotency | Safe to rerun | **Verified** (0 rows written on rerun, 0 timestamp/ID churn) | **COMPLETED** |
| Test Coverage | All pass | **37 / 37 passed** (0 failed, 0 skipped, 0 xfailed) | **COMPLETED** |

---

## Rules and Verification Policy

1. **Two-Source Rule**: Every historical claim (`is_legend: false`) must be supported by at least **two genuinely independent publishers**. Two URLs from the same publisher (e.g. UNESCO list page and UNESCO periodic report) count as one publisher.
2. **Acceptable Publishers**:
   - Intergovernmental & Heritage Registries: UNESCO World Heritage Centre.
   - Government & Tourism Bodies: Government of India (Ministry of Culture, Lok Sabha debates), Delhi Tourism (`delhitourism.gov.in`), District Administration Agra (`agra.nic.in`), Taj Mahal Tourism Department (`tajmahal.gov.in`).
   - Encyclopedias: Encyclopaedia Britannica.
   - Academic & Research Institutions: Aga Khan Trust for Culture / MIT Documentation Center (Archnet), University of Tokyo archaeological mission.
   - Heritage Trusts: Indian National Trust for Art and Cultural Heritage (INTACH).
3. **Banned Sources**: Wikipedia, Wikipedia mirrors, and unverified derivative aggregator sites (e.g., Wikiwand, New World Encyclopedia, IndiaTV) are strictly prohibited and automatically rejected by `validate_dataset`.
4. **Folklore vs. Established History**: Folklore, myths, and unproven traditions must be flagged with `is_legend: true` and `type: "tradition"`. Legends require at least one credible recording source, are strictly excluded from generated monument descriptions, and can never back a relationship edge.
5. **Monument Descriptions**: Monuments contain no arbitrary prose in `monuments.json`. Descriptions are assembled dynamically at seed time by concatenating own verified historical claims of type `built`, `style`, `recognition`, and `event` ordered by position and key.
6. **Coordinates**: Coordinates are decimal degrees converted from official source records (UNESCO GIS / maps, District Administration Agra, Delhi Tourism). Swapped coordinates or values outside India are rejected at validation time.

---

## Seeded Monuments (15)

1. **Humayun's Tomb** (`humayuns-tomb`, Delhi) — Early Mughal garden tomb, UNESCO World Heritage (1993).
2. **Taj Mahal** (`tajmahal`, Agra) — White marble mausoleum built by Shah Jahan, UNESCO World Heritage (1983).
3. **Fatehpur Sikri** (`fatehpur-sikri`, Agra District) — Mughal imperial capital founded by Akbar in 1571, UNESCO World Heritage (1986).
4. **Qutb Minar and its Monuments** (`qutb-complex`, Delhi) — 72.5m minaret and early Delhi Sultanate complex, UNESCO World Heritage (1993).
5. **Red Fort Complex** (`red-fort`, Delhi) — Shah Jahan's palace citadel of Shahjahanabad, UNESCO World Heritage (2007).
6. **Agra Fort** (`agra-fort`, Agra) — Imperial walled city rebuilt in red sandstone by Akbar, UNESCO World Heritage (1983).
7. **Akbar's Tomb, Sikandra** (`akbars-tomb`, Agra) — Five-tiered pyramidal mausoleum planned by Akbar and completed by Jahangir (1613).
8. **Tomb of I'timad-ud-Daulah** (`itimad-ud-daulah`, Agra) — White marble tomb commissioned by Empress Nur Jahan with pietra dura inlay, direct precursor to the Taj Mahal.
9. **Jama Masjid** (`jama-masjid`, Delhi) — Imperial congregational mosque of Shahjahanabad commissioned by Shah Jahan (1650–1656).
10. **Safdarjung's Tomb** (`safdarjungs-tomb`, Delhi) — Last enclosed garden tomb built in Delhi (1753–1754) for Mughal Grand Vizier Safdarjung.
11. **Purana Qila** (`purana-qila`, Delhi) — Ancient citadel site developed as Dinpanah by Humayun and rebuilt by Sher Shah Suri (6th city of Delhi).
12. **Tughlaqabad Fort** (`tughlaqabad-fort`, Delhi) — Colossal stone fortress and third city of Delhi built by Sultan Ghiyas-ud-din Tughlaq (1321).
13. **Jantar Mantar** (`jantar-mantar`, Delhi) — Architectural astronomy observatory constructed in 1724 by Maharaja Sawai Jai Singh II of Jaipur.
14. **Mehrauli Archaeological Park** (`mehrauli-archaeological-park`, Delhi) — Contiguous heritage precinct spanning over 1,000 years of Delhi's first city (Lal Kot).
15. **Lodhi Gardens** (`lodhi-gardens`, Delhi) — Monumental tombs and mosques of the Sayyid and Lodi dynasties, including the precursor garden tomb of Sikandar Lodi.

---

## How to Run

From `backend/`:

```powershell
python -m app.db.seed --check   # Validate all JSON records against rules and constraints
python -m app.db.seed           # Seed or update the database (idempotent, safe to rerun)
python -m app.db.seed --strict  # Exit non-zero if Issue #3 targets are not met
python -m pytest tests -v       # Run full schema and seed test suite
```
