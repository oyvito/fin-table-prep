# Kodelister

Denne mappen inneholder kodelister som brukes for automatisk transformasjon.

**NB:** Kodelister er kun relevante for spesifikke tabeller. Ikke alle tabeller trenger kodelister.
Legg kun inn kodelister når du vet at de skal brukes (f.eks. TKNR for NAV-tabeller).

## Når skal vi bruke kodeliste vs inline mapping?

### Bruk KODELISTE når:
✅ Mappingen er **stabil og gjenbrukbar** på tvers av flere tabeller
✅ Mappingen er **kompleks** (mange verdier, >10 entries)
✅ Mappingen kan **endres over tid** og trenger versjonskontroll
✅ Mappingen kommer fra **ekstern kilde** (SSB, NAV, etc.)
✅ Eksempler:
   - TKNR-koder → moderne bydelskoder (NAV_TKNR_til_PX.json)
   - SSB geografikoder → PX-koder (SSB_til_PX_geo_*.json)
   - Aldersgruppe-konverteringer mellom standarder (aldgr5_til_aldgr16a.json)

### Bruk INLINE MAPPING når:
✅ Mappingen er **tabell-spesifikk** og brukes kun i én fil
✅ Mappingen er **enkel** (<10 entries)
✅ Mappingen er **dynamisk** (bygges fra dataene selv)
✅ Mappingen er **midlertidig rensing** (prefix-fjerning, formatering)
✅ Eksempler:
   - Aldersgruppe prefix-fjerning: "1: 0 - 5" → "0-5 år" (OK-SOS002)
   - Dynamisk bydelsnavn-mapping fra inputdata (OK-SOS004)
   - Sentrum/Marka merging for én spesifikk tabell (OK-SOS007)

## Standard pattern for scripts

```python
# 1. Hvis du bruker kodeliste - Last den øverst i funksjonen
from pathlib import Path
import json

script_dir = Path(__file__).parent
codelist_path = script_dir.parent / 'kodelister' / 'NAV_TKNR_til_PX.json'

with open(codelist_path, 'r', encoding='utf-8') as f:
    codelist = json.load(f)

# Bruk mapping fra kodeliste
tknr_mapping = {int(k): v for k, v in codelist['mappings']['tknr_to_ssb'].items()}

# 2. Hvis du bruker inline mapping - Definer den like etter kodeliste-loading
# (eller øverst hvis ingen kodeliste)
alder_mapping = {
    '1: 0 - 5': '0-5 år',
    '2: 6 - 9': '6-9 år',
    # ... tabell-spesifikk mapping
}

# 3. Kommenter ALLTID hvorfor du bruker inline vs kodeliste
# Eksempel:
# Aldersgruppe mapping (tabell-spesifikk prefix-fjerning, ikke gjenbrukbar)
alder_mapping = {...}
```

## Struktur

Kodelister lagres som JSON-filer for enkel vedlikehold.

### Format

#### JSON-format (anbefalt for enkle mappings):
```json
{
  "name": "Oslo bydeler - TKNR til bydelskode",
  "description": "Mapping fra gamle TKNR-koder til nye 5-sifrede bydelskoder",
  "type": "numeric_mapping",
  "mappings": {
    "301": "301",
    "312": "30105",
    "313": "30104",
    ...
  }
}
```

#### Excel-format (for komplekse kodelister):
| fra_kode | til_kode | fra_navn | til_navn | gyldig_fra | gyldig_til |
|----------|----------|----------|----------|------------|------------|
| 301      | 301      | Oslo     | Oslo i alt | 2004-01-01 | |
| 312      | 30105    | Frogner  | Frogner    | 2004-01-01 | |

## Eksisterende kodelister

Legg inn dine kodelister her. Eksempler:

- `oslo_bydeler.json` - TKNR → Bydelskode
- `aldersgrupper.json` - Ulike aldersinndelinger
- `kjonn.json` - Kjønnskategorier
- `tidsperioder.json` - År, kvartal, måned-formater
- osv.

## Hvordan kodelister brukes

Når `generate_prep_script.py` kjøres:

1. Laster inn alle kodelister fra denne mappen
2. Prøver å matche kolonner i input/output mot kodelister
3. Hvis match: Genererer automatisk transformasjonskode
4. Hvis ikke match: Lager placeholder for manuell utfylling

## Legge til ny kodeliste

### Manuelt (JSON):
```json
{
  "name": "Min kodeliste",
  "description": "Beskrivelse av hva denne gjør",
  "source_column_pattern": ".*tknr.*|.*kommune.*",  // Regex for å matche kolonnenavn
  "target_column_pattern": ".*geografi.*|.*bydel.*",
  "type": "mapping",
  "mappings": {
    "fra": "til",
    ...
  }
}
```

### Fra Excel:
Bruk `create_codelist.py` (kommer) til å konvertere Excel → JSON

## Tips

- **Versjonskontroll**: Bruk git for å spore endringer i kodelister
- **Dokumentasjon**: Inkluder alltid 'description' og 'source'
- **Gyldighetstid**: For tidsavhengige koder, bruk gyldig_fra/til
- **Testing**: Test kodelister på eksempeldata før produksjon
