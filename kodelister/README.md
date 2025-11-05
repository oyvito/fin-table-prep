# Kodelister

Denne mappen inneholder kodelister som brukes for automatisk transformasjon.

**NB:** Kodelister er kun relevante for spesifikke tabeller. Ikke alle tabeller trenger kodelister.
Legg kun inn kodelister når du vet at de skal brukes (f.eks. TKNR for NAV-tabeller).

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
