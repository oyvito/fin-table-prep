# Kontrollskjema for Statistikktabeller

## 🎯 Formål

Kontrollskjemaet sikrer at **alle statistikktabeller** har:
- ✅ Identisk variabelnavn for samme konsept
- ✅ Riktig geografisk koding (PX-format)
- ✅ Konsistent datastruktur
- ✅ Validerte verdier

## 📋 Standard variabelnavn

### Må alltid følges:

| Variabel | Korrekt navn | IKKE bruk |
|----------|-------------|-----------|
| Årstall | `år` | årgang, År, year, periode |
| Kjønn | `kjønn` | kjonn, Kjønn, gender |
| Alder | `alder` | Alder, age, aldersgruppe |
| Antall | `antall` | Antall, count, n, sum |
| Andel (%) | `andel` | Andel, prosent, pct |
| Geografi | `geografi` | bydel, område, region |

**Regel**: Alltid små bokstaver!

## 🗺️ Geografisk koding

### Viktig!
- **ALLTID** bruk PX-koder (fra kodelister)
- **ALDRI** bruk SSB-koder direkte i output

### Eksempel:

❌ **Feil:**
```
bydel_kode: 030101
bydel_navn: Gamle Oslo
```

✅ **Riktig:**
```
bydel_kode: 1
bydel_navn: Gamle Oslo
```

### Kodelister per nivå:

| Geografisk nivå | Kodeliste |
|-----------------|-----------|
| Kommune | `SSB_til_PX_geo_kommune.json` |
| Bydel | `SSB_til_PX_geo_bydel.json` |
| Delbydel | `SSB_til_PX_geo_delbydel.json` |
| Grunnkretsområde | `SSB_til_PX_geo_grunnkretsområde.json` |
| Grunnkrets | `SSB_til_PX_geo_grunnkrets.json` |
| TKNR (NAV) | `NAV_TKNR_til_PX.json` |

## 🔧 Bruk av validering

### Valider en tabell:

```bash
python validate_table.py output_tabell.xlsx
```

Dette gir rapport med:
- Forslag til standardisering av kolonnenavn
- Advarsler om datatyper
- Sjekk av geografisk koding
- Validering av verdier (årstall, prosenter, etc.)

### Eksempel output:

```
============================================================
VALIDERINGSRAPPORT: OK-BEF001
============================================================
Antall rader: 150
Antall kolonner: 5

📝 FORSLAG TIL STANDARDISERING AV KOLONNENAVN:
------------------------------------------------------------
  'År' → 'år'
  'Bydel' → 'geografi'
  'Antall personer' → 'antall'

⚠️  GEOGRAFISK KODING:
------------------------------------------------------------
  bydel_kode: Mulig SSB-kode funnet. Skal være PX-kode.
    Eksempel: 030101

============================================================
OPPSUMMERING:
  Forslag til standardisering: 3
  Geografisk koding-advarsler: 1
  Totalt: 4
============================================================
```

## 📊 Tabellstruktur

### Anbefalt kolonnerekkefølge:

1. `år`
2. `geografi_kode`
3. `geografi_navn`
4. `kjønn` (hvis relevant)
5. `alder` (hvis relevant)
6. Kategorivariabler (utdanning, status, etc.)
7. `antall`
8. `andel`

## 🔄 Oppdatering av kontrollskjema

Når du finner nye mønstre eller variabler:

1. Åpne `kontrollskjema.json`
2. Legg til under `standard_variables`
3. Oppdater `version` og `changelog`
4. Commit til Git

### Eksempel på ny variabel:

```json
"utdanningsnivå": {
  "required_name": "utdanningsnivå",
  "description": "Utdanningsnivå etter NUS",
  "data_type": "string",
  "alternative_names": ["utdanning", "Utdanningsnivå", "education"],
  "notes": "Følger NUS-standard"
}
```

## 💡 Tips

### Ved nye tabeller:
1. Generer først med `generate_prep_script_v2.py`
2. Kjør `validate_table.py` på output
3. Juster basert på valideringsrapport
4. Kjør validering igjen
5. Når godkjent → lagre i training_data

### Ved flere like tabeller:
- Dokumenter mønstre i kontrollskjema
- Legg til domain-spesifikke regler
- Bygg opp pattern library

## 📚 Domene-spesifikke regler

### Befolkning
Standard variabler: `år`, `geografi`, `kjønn`, `alder`, `antall`

### Sysselsetting
Standard variabler: `år`, `geografi`, `kjønn`, `alder`, `antall_sysselsatte`, `antall_befolkning`, `sysselsettingsandel`

Beregning: `sysselsettingsandel = (antall_sysselsatte / antall_befolkning) * 100`

## 🎯 Kvalitetskrav

### Må være oppfylt:
- ✅ Alle standardvariabler bruker korrekt navn
- ✅ Geografisk koding følger PX-format
- ✅ Årstall er 4 sifre (YYYY)
- ✅ Andeler er 0-100 (ikke 0-1)
- ✅ Ingen duplikate rader
- ✅ Konsistente datatyper

### Ønskelig:
- Separate kolonner for kode og navn
- Metadata-fil (JSON) for hver tabell
- Testet prep-script i training_data

## 🔄 Workflow

```
1. Få rådata
2. Kjør generate_prep_script_v2.py
3. Juster generert script
4. Test transformation
5. Valider output med validate_table.py
6. Fiks issues
7. Valider igjen → Godkjent?
8. Lagre i training_data/
9. Oppdater kontrollskjema hvis nytt mønster
```

---

**Husk**: Kontrollskjemaet er levende dokumentasjon. Oppdater det når du lærer nye mønstre! 🚀
