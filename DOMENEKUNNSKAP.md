# Domenekunnskap for Oslo Kommune Statistikk

**Sist oppdatert:** 2025-12-19

Dette dokumentet inneholder domene-spesifikk kunnskap som er viktig for korrekt transformasjon av statistikkdata.

---

## Sysselsetting (OK-SYS-tabeller)

### Tidsperioder og Sammenligning

**Sysselsettingsdata:**
- Produseres for **siste kvartal hvert år** (4. kvartal)
- Eksempel: Data for 2024 = 4. kvartal 2024

**Befolkningsgrunnlag for andelsberegning:**
- For å beregne sysselsettingsandeler må sysselsatte sammenlignes med befolkningsgrunnlag
- Befolkningsdata brukes per **1. januar påfølgende år**
- Eksempel: Sysselsatte Q4 2024 sammenlignes med befolkning per 1.1.2025

**Rasjonale:**
- Befolkning per 1.1. i påfølgende år er tettest på 4. kvartal foregående år
- Dette sikrer mest nøyaktig andelsberegning

### Multi-input Pattern for Sysselsettingsandeler

Typisk struktur for OK-SYS-tabeller med andeler:

```
Input 1: Sysselsatte (aargang: 2024)
  - Geografisk nivå (bydel/delbydel/grunnkrets)
  - Aldersgruppe (BREDE grupper: 15-24, 25-39, 40-49, 50-59, 60-74)
  - Kjønn
  - Antall sysselsatte

Input 2: Befolkning (aargang: 2025)
  - Samme geografisk nivå
  - Aldersgruppe (SMALE grupper: 15-19, 20-24, 25-29, 30-34, etc.)
  - Samme kjønn
  - Antall innbyggere

Output:
  - Merge på: [geografi, aldersgruppe, kjønn]
  - IKKE aargang! (forskjellige årganger: 2024 vs 2025)
  - VIKTIG: Befolkning må aggregeres til sysselsatte's aldersgrupper!
  - Beregn: andeler = (sysselsatte / befolkning) * 100
  - Output aargang: Bruk sysselsettingsdata sitt år (2024)
```

### Aldersgruppe-aggregering

**Problem:**
- Sysselsatte bruker brede aldersgrupper (15-24, 25-39, etc.)
- Befolkning bruker smale aldersgrupper (15-19, 20-24, 25-29, etc.)

**Løsning:**
Aggreger befolkningsdata til sysselsatte's aldersgrupper:

```python
# Mapping fra smale til brede aldersgrupper
aldersgruppe_mapping = {
    '15 - 19 år': '15-24 år',
    '20 - 24 år': '15-24 år',
    '25 - 29 år': '25-39 år',
    '30 - 34 år': '25-39 år',
    '35 - 39 år': '25-39 år',
    '40 - 44 år': '40-49 år',
    '45 - 49 år': '40-49 år',
    '50 - 54 år': '50-59 år',
    '55 - 59 år': '50-59 år',
    '60 - 64 år': '60-74 år',
    '65 - 69 år': '60-74 år',
    '70 - 74 år': '60-74 år',
    'Alder i alt': 'Alder i alt'
}

# Konverter befolkning til brede aldersgrupper
df_befolkning['aldersgrupper'] = df_befolkning['aldersgrupper_smal'].map(aldersgruppe_mapping)

# Aggreger (sum) per brede aldersgrupper
df_befolkning_agg = df_befolkning.groupby(
    ['geografi', 'aldersgrupper', 'kjoenn_fmt']
).agg({'befolkning': 'sum'}).reset_index()

# Nå kan vi merge med sysselsatte
df_merged = pd.merge(df_sysselsatte, df_befolkning_agg, 
                    on=['geografi', 'aldersgrupper', 'kjoenn_fmt'])
```

### Nøkkelkolonner for Merge

**IKKE bruk:**
- ❌ `aargang` (vil være forskjellig mellom sysselsatte og befolkning)

**Bruk:**
- ✅ Geografiske kolonner (geografi, geografi_navn)
- ✅ Aldersgruppe (aldersgrupper, aldgr16a_, aldgr5, etc.)
- ✅ Kjønn (kjoenn, kjoenn_fmt)

**Eksempel merge-nøkler:**
```python
merge_keys = ['geografi', 'aldersgrupper', 'kjoenn_fmt']
# IKKE inkluder 'aargang'!
```

### Beregninger

**Andeler:**
```python
# Etter merge av sysselsatte og befolkning
df['andeler'] = (df['sysselsatte'] / df['befolkning'] * 100).round(1)
```

**Output aargang:**
```python
# Bruk sysselsettingsdata sitt aargang
df['aargang'] = sysselsatte_aargang  # 2024
```

---

## Befolkning (OK-BEF-tabeller)

### Tidsperioder
- Befolkningsdata produseres per **1. januar** hvert år
- Eksempel: 2025 = Befolkning per 1.1.2025

---

## Utdanning (OK-UTD-tabeller)

### Tidsperioder
- Data per **1. oktober** hvert år
- Refererer til høyeste fullførte utdanning per denne datoen

---

## Næring (OK-NAE-tabeller)

### Tidsperioder
- Data per **4. kvartal** hvert år
- Følger samme logikk som sysselsettingsdata

---

## NAV Sosialstatistikk (OK-SOS-tabeller)

### Oversikt
NAV-tabeller dekker ulike støtte- og trygdeordninger:
- **OK-SOS002:** Barnetrygd
- **OK-SOS003:** Sosialhjelpsmottakere
- **OK-SOS004:** Grunnstønad og hjelpestønad
- **OK-SOS006:** Uføretrygd
- **OK-SOS007:** Alderspensjon

### TKNR-koder (Gamle Bydelskoder)

**Historisk kontekst:**
Eldre NAV-data bruker TKNR-koder (Trygdekontornummer) som er forløpere til dagens 5-sifrede bydelskoder.

**Kodeliste:**
Offisiell mapping finnes i: `kodelister/NAV_TKNR_til_PX.json`

Kodelisten inneholder:
- `tknr_to_ssb`: TKNR → SSB 5-sifrede bydelskoder (301, 30101-30115)
- `tknr_to_px`: TKNR → PX kortkoder (100000, 1-15)
- `labels`: Bydelsnavn for alle koder

**Eksempel mapping (tknr_to_ssb):**
```python
# Last fra kodeliste
import json
with open('kodelister/NAV_TKNR_til_PX.json', 'r', encoding='utf-8') as f:
    codelist = json.load(f)

tknr_mapping = {int(k): v for k, v in codelist['mappings']['tknr_to_ssb'].items()}
# Resultat:
# {301: '301', 312: '30105', 313: '30104', 314: '30103', ...}
```

**Bruk:**
- Identifiser TKNR-kolonner i input (ofte kalt `TKNR` eller `tknr`)
- Mappe til moderne `geografi`-koder
- Legg til `geografi_`-kolonne med bydelsnavn

### Barnetrygd-spesifikke Felt

**Forsørgerstatus:**
- `I alt` (total)
- `To forsørgere` (to-forelderhushold)
- `Enslig forsørger` (eneforsørger)

**Barnets alder:**
Aldersgrupper for barnetrygd-berettigede barn:
- `I alt`
- `0-5 år`
- `6-9 år`
- `10-12 år`
- `13-15 år`
- `16-17 år`

**Viktig datakvalitet:**
Input-data kan ha prefix på aldersgrupper (f.eks. "1: 0 - 5", "2: 6 - 9"). 
Disse må renses:
```python
alder_mapping = {
    '1: 0 - 5': '0-5 år',
    '2: 6 - 9': '6-9 år',
    '3: 10 - 12': '10-12 år',
    '4: 13 - 15': '13-15 år',
    '5: 16 - 17': '16-17 år',
    'I alt': 'I alt'
}
```

### Multi-format Support

**Problem:**
NAV leverer data i ulike formater mellom år:
- 2023: Enkelt Excel-ark
- 2024: Multi-sheet Excel med ett ark per stønad/kategori

**Løsning:**
Scripts må auto-detektere format:
```python
# Sjekk antall ark
sheet_names = pd.ExcelFile(input_file).sheet_names

if len(sheet_names) == 1:
    # 2023-format: Enkelt ark
    df = pd.read_excel(input_file)
else:
    # 2024-format: Velg spesifikt ark
    if sheet_name:
        df = pd.read_excel(input_file, sheet_name=sheet_name)
    else:
        # Auto-detekter basert på kolonnenavn eller ark-navn
        for sheet in sheet_names:
            if 'keyword' in sheet.lower():
                df = pd.read_excel(input_file, sheet_name=sheet)
```

### Sentrum/Marka-håndtering

**Spesialbydeler:**
Enkelte tabeller (f.eks. OK-SOS007 alderspensjon) har historiske kategorier:
- Bydel 30116 (Sentrum) - utgått
- Bydel 30117 (Marka) - utgått

**Moderne praksis:**
Merge til felles kategori:
- Kode: `30119192`
- Navn: `Sentrum og Marka`

```python
# Merge Sentrum og Marka
sentrum_marka = df[df['geografi'].isin(['30116', '30117'])].copy()
sentrum_marka_sum = sentrum_marka.groupby(
    ['år', 'kjønn', 'alder']
).agg({'antall': 'sum'}).reset_index()
sentrum_marka_sum['geografi'] = '30119192'
sentrum_marka_sum['geografi_'] = 'Sentrum og Marka'

# Fjern originale og legg til merged
df = df[~df['geografi'].isin(['30116', '30117'])]
df = pd.concat([df, sentrum_marka_sum], ignore_index=True)
```

### Prikkede Verdier

**Hva er prikkede verdier?**
NAV prikker (sensurerer) små tall for personvern. Vises som `*` i data.

**Håndtering:**
```python
# Behold '*' som string
if df['antall'].dtype != 'object':
    df['antall'] = df['antall'].astype(str)

# Erstatt spesielle missing-verdier
df['antall'] = df['antall'].replace(['-', '', 'NaN'], '*')
```

### Standardiserte Kolonnenavn

**NAV-tabeller bruker ofte:**
- `år` / `periode` → standardiser til `år`
- `geografi` + `geografi_` (kode + navn)
- `kjønn` / `Kjønn` → standardiser til `kjønn`
- `alder` / `Alder` / `aldersgrupper` → avhenger av tabell
- `antall` / `Antall` → standardiser til beskrivende navn (f.eks. `antall barn`, `Antall personer`)

**Best practice:**
Bruk beskrivende navn i output:
- `antall barn` (barnetrygd)
- `Antall personer` (uføretrygd, alderspensjon)
- `Antall` (sosialhjelpsmottakere)

---

## Geografiske Nivåer

### Hierarki
```
Oslo (301)
  └─ Bydel (01-17)
      └─ Delbydel
          └─ Grunnkrets
```

### Spesialhåndtering: Marka
- Marka (områder utenfor bydelsinndeling) aggregeres til administrativ bydel
- Kode: 99

### Kontekstuelle Geografinavn

**Arbeidssted vs Bosted:**
- Sysselsettingsdata har ofte BÅDE arbeidssted OG bosted
- Bruk kontekstuelle navn:
  - `arbeidssted_grunnkrets` for arbeidsplassens beliggenhet
  - `bosted_grunnkrets` for hvor personen bor

---

## Variabel-par (Kode + Label)

### Pattern: `_fmt` suffix
Mange tabeller har par av kolonner:
- **Base-kolonne:** Numerisk kode (f.eks. `bydel`, `kjoenn`)
- **Label-kolonne:** Tekstlig beskrivelse med `_fmt` suffix (f.eks. `bydel_fmt`, `kjoenn_fmt`)

**Merge-strategi:**
- Bruk **base-kolonnen** for merge-operasjoner (numerisk sammenligning)
- Inkluder **label-kolonnen** i output for lesbarhet

### Eksempel
```python
# IKKE merge på label:
# df.merge(df2, on=['bydel_fmt'])  # ❌ Tekst kan variere

# Merge på base:
df.merge(df2, on=['bydel'])  # ✅ Numerisk kode
```

---

## Aggregeringer

### "Oslo i alt"
Mange tabeller inkluderer aggregert nivå for hele Oslo:
- Geografikode: `100000` eller `301`
- Navn: "Oslo i alt" eller "0301 Oslo i alt"

**Generering:**
```python
df_oslo = df.groupby(['aargang', 'kjoenn', 'aldersgruppe']).agg({
    'antall': 'sum'
}).reset_index()
df_oslo['geografi'] = 100000
df_oslo['geografi_navn'] = 'Oslo i alt'
df_final = pd.concat([df_final, df_oslo], ignore_index=True)
```

---

## Datakvalitet

### Manglende Verdier
- NaN i nøkkelkolonner (geografi, alder, kjønn) skal vanligvis **ekskluderes**
- Bruk `dropna()` på nøkkelkolonner før merge

### Datatyper
- Geografiske koder: **Int64** (nullable integer)
- Aargang: **string** (for å håndtere formatvariasjon)
- Antall/verdier: **float** eller **Int64**

---

## Notater for Implementering

### generate_prep_script_v2.py

**TODO: Implementer sysselsetting-spesifikk logikk:**

1. **Detekter sysselsettingstabeller:**
   ```python
   if table_code.startswith('OK-SYS'):
       # Spesiell håndtering
   ```

2. **Identifiser aargang-forskjell:**
   ```python
   # Sjekk om input-filer har forskjellige årganger
   aargang1 = df1['aargang'].unique()
   aargang2 = df2['aargang'].unique()
   
   if aargang1 != aargang2:
       # Mulig sysselsatte vs befolkning
       # IKKE bruk aargang som merge-nøkkel!
   ```

3. **Eksluder aargang fra felles nøkler:**
   ```python
   if table_code.startswith('OK-SYS') and len(input_dfs) > 1:
       # Fjern aargang fra candidate_keys hvis årganger er forskjellige
       candidate_keys = [k for k in candidate_keys if k != 'aargang']
   ```

4. **Generer andelsberegning:**
   ```python
   # I generert script:
   if 'sysselsatte' in columns and 'befolkning' in columns:
       df['andeler'] = (df['sysselsatte'] / df['befolkning'] * 100).round(1)
   ```

---

## Eksempler

### OK-SYS001: Sysselsatte etter arbeidssted og bosted
- Input 1: Arbeidssted-data
- Input 2: Bosted-data
- Merge på: [aargang, grunnkrets]
- Begge har SAMME aargang

### OK-SYS002: Sysselsatte med andeler
- Input 1: Sysselsatte (aargang: 2024)
- Input 2: Befolkning (aargang: 2025)
- Merge på: [geografi, aldersgrupper, kjoenn_fmt]
- **IKKE aargang!**
- Beregn: andeler = sysselsatte / befolkning * 100
- Output aargang: 2024
