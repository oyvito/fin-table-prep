# Production Scripts - NAV Statistikk Data Prep

Denne mappen inneholder produksjonsklare prep-scripts for transformering av NAV-statistikkdata til PX-format.

## Standard for Script-utvikling

### Kodeliste vs Inline Mapping

Alle scripts følger denne standarden:

**Bruk KODELISTE når:**
- Mappingen er stabil og gjenbrukbar på tvers av flere tabeller
- Mappingen er kompleks (>10 entries)
- Mappingen kan endres over tid
- Eksempel: TKNR → moderne bydelskoder (brukt av OK-SOS002)

**Bruk INLINE MAPPING når:**
- Mappingen er tabell-spesifikk
- Mappingen er enkel (<10 entries)
- Mappingen er dynamisk (bygges fra data)
- Mappingen er midlertidig formatering
- Eksempel: Aldersgruppe prefix-fjerning i OK-SOS002

**Dokumentasjon:**
Alle mappings MÅ ha kommentarer som forklarer:
```python
# ============================================================
# KODELISTE/INLINE MAPPING: <Beskrivelse>
# Hvorfor: <Begrunnelse for valg av metode>
# ============================================================
```

Se [kodelister/README.md](../kodelister/README.md) for mer info.

---

## Tabeller

### OK-SOS002 - Barnetrygd
**Script:** `OK-SOS002_prep.py`

**Bruk:**
```bash
python OK-SOS002_prep.py input.xlsx output.xlsx [--year ÅRSTALL]
```

**Format:**
- Input: periode, forsorgerstatus, barn_alder, TKNR, antall, navn
- Output: år, geografi, geografi_, forsørgerstatus, barnets alder, antall barn
- **TKNR mapping:** Konverterer gamle bydelskoder (312=Frogner, 313=St. Hanshaugen osv.) til nye 5-sifrede koder (30105, 30104 osv.)
- Standardiserer aldersgrupper: fjerner prefix fra "1: 0 - 5" → "0-5 år"

**Kvalitetssikring:**
- ✓ Validert mot fasit for 2023
- ✓ Korrekt TKNR mapping for alle 16 bydeler
- ✓ Riktig kolonnenavn og format
- ✓ Ingen duplikater

---

### OK-SOS003 - Sosialhjelpsmottakere
**Script:** `OK-SOS003_prep.py`

**Bruk:**
```bash
python OK-SOS003_prep.py input.xlsx output.xlsx [--year ÅRSTALL]
```

**Format:**
- Input: År, Bydel, Bydel nr, Kjønn, Alder, Antall
- Output: År, bosted, bosted_, kjønn, alder, Antall

---

### OK-SOS004 - Grunnstønad og hjelpestønad
**Script:** `OK-SOS004_prep.py`

**Bruk:**
```bash
python OK-SOS004_prep.py input.xlsx output.xlsx [--sheet ARKNAVN] [--year ÅRSTALL]
```

**Format:**
- Håndterer både 2023-format (enkelt ark) og 2024-format (multi-sheet)
- Output: År, bosted_, bosted, Type stønad, Alder, Antall
- Standardiserer "St. Hanshaugen" (med mellomrom)
- Beholder '*' for prikkede verdier

---

### OK-SOS006 - Uføretrygd
**Script:** `OK-SOS006_prep.py`

**Bruk:**
```bash
python OK-SOS006_prep.py input.xlsx output.xlsx [--sheet ARKNAVN] [--year ÅRSTALL]
```

**Format:**
- Håndterer både 2023-format og 2024-format
- Output: År, bosted, bosted_, Kjønn, Alder, Antall personer
- Auto-detekterer riktig ark (søker etter "uføretrygd")

---

### OK-SOS007 - Alderspensjon
**Script:** `OK-SOS007_prep.py`

**Bruk:**
```bash
python OK-SOS007_prep.py input.xlsx output.xlsx [--sheet ARKNAVN] [--year ÅRSTALL]
```

**Format:**
- Håndterer både 2023-format og 2024-format
- Output: År, bosted_, bosted, kjønn, aldersgruppe, antall mottakere
- Slår sammen Sentrum og Marka til "Sentrum, Marka og uten registrert adresse" (bydel 30119192)
- Standardiserer "Oslo i alt" og "85 år+" aldersgruppe

---

## Generelle funksjoner

Alle scripts:
- Håndterer prikkede verdier ('*') - beholder som string
- Sjekker for duplikater
- Standardiserer bydelsnavn (fjerner "Bydel " prefix)
- Konverterer bosted-koder til string format
- Kan kjøres fra kommandolinje med parametere
- Støtter både nye og gamle dataformater

## Eksempler

```bash
# SOS003 - prosesser 2024-data
python OK-SOS003_prep.py ../training_data/OK-SOS003/input_2024.xlsx output_2024.xlsx --year 2024

# SOS004 - prosesser med spesifikt ark
python OK-SOS004_prep.py ../training_data/OK-SOS004/input.xlsx output.xlsx --sheet "grunnstønad - hjelpestønad"

# SOS006 - auto-detect ark
python OK-SOS006_prep.py ../training_data/OK-SOS006/input.xlsx output.xlsx

# SOS007 - med årstall
python OK-SOS007_prep.py ../training_data/OK-SOS007/input.xlsx output.xlsx --year 2024
```
