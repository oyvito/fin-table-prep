# Hvordan legge til egne kodelister

## 📋 Når trenger jeg en kodeliste?

Bruk kodelister når du har:
- **Systematiske kode-konverteringer** (f.eks. TKNR 301 → 30105)
- **Standardiserte kategorier** som gjentar seg på tvers av tabeller
- **Komplekse mappings** som er vanskelige å oppdage automatisk

## ❌ Når trenger jeg IKKE kodeliste?

- Enkle navneendringer (f.eks. "antall" → "antall barn")
- Unike transformasjoner for én spesifikk tabell
- Data som endres ofte

## 🔧 Steg-for-steg: Lage en kodeliste

### 1. Identifiser behovet

Eksempel: Du har flere NAV-tabeller som bruker TKNR-koder.

### 2. Lag JSON-fil

Opprett `kodelister/min_kodeliste.json`:

```json
{
  "name": "Beskrivende navn",
  "description": "Hva denne kodelisten gjør",
  "source": "Hvor kommer dataene fra?",
  "last_updated": "2025-11-05",
  
  "source_column_patterns": [
    ".*tknr.*",
    ".*kommune_kode.*"
  ],
  
  "target_column_patterns": [
    ".*geografi.*",
    ".*bydel.*"
  ],
  
  "type": "mapping",
  
  "mappings": {
    "fra_verdi": "til_verdi",
    "301": "301",
    "312": "30105"
  }
}
```

### 3. Test kodelisten

```python
from codelist_manager import CodelistManager

manager = CodelistManager()
print(manager.list_available_codelists())
```

### 4. Bruk i transformasjon

Kodelisten vil automatisk bli brukt når relevante kolonner oppdages.

## 📝 Eksempel: TKNR for NAV-tabeller

Kun relevant for tabeller fra NAV.

**Fil**: `kodelister/nav_tknr.json`

```json
{
  "name": "NAV TKNR til bydelskode",
  "description": "Kun for NAV-tabeller som bruker TKNR",
  "source": "NAV / Oslo kommune",
  "last_updated": "2025-11-05",
  
  "source_column_patterns": ["^tknr$", ".*tknr.*"],
  "target_column_patterns": ["^geografi$", ".*bydel.*"],
  
  "mappings": {
    "301": "301",
    "312": "30105",
    ...
  },
  
  "name_mappings": {
    "Oslo": "Oslo i alt"
  }
}
```

## 📝 Eksempel: Alderskategorier

Hvis du har flere tabeller med samme aldersinndelinger.

**Fil**: `kodelister/alder_0_17.json`

```json
{
  "name": "Aldersgrupper 0-17 år",
  "description": "Standard inndeling for barnestatistikk",
  
  "source_column_patterns": [".*alder.*", ".*barn.*alder.*"],
  "target_column_patterns": [".*alder.*"],
  
  "mappings": {
    "1: 0 - 5": "0-5 år",
    "2: 6 - 9": "6-9 år",
    "3: 10 - 12": "10-12 år",
    "4: 13 - 15": "13-15 år",
    "5: 16 - 17": "16-17 år",
    "I alt": "I alt"
  }
}
```

## 🎯 Best practices

### 1. Navngi filer beskrivende
- ✅ `nav_tknr.json`
- ✅ `alder_0_17.json`
- ❌ `koder.json`
- ❌ `mapping1.json`

### 2. Bruk spesifikke mønstre
```json
// ✅ Spesifikt
"source_column_patterns": ["^tknr$", "^TKNR$"]

// ❌ For vidt
"source_column_patterns": [".*"]
```

### 3. Dokumenter kilden
```json
{
  "source": "NAV, eksportert 2024-10",
  "last_updated": "2025-11-05",
  "valid_from": "2004-01-01",
  "notes": "Kun for bydeler i Oslo"
}
```

### 4. Versjonskontroll
- Bruk Git for å spore endringer
- Dokumenter hvorfor endringer ble gjort

## 🔍 Feilsøking

### Kodeliste blir ikke brukt?

Sjekk:
1. Er JSON-filen gyldig? (test med JSON validator)
2. Matcher `source_column_patterns` dine kolonnenavn?
3. Er det overlap mellom mapping-verdier og faktiske data?

### Test manuelt:
```python
from codelist_manager import CodelistManager
import pandas as pd

manager = CodelistManager()
df_input = pd.read_excel("input.xlsx")
df_output = pd.read_excel("output.xlsx")

# Sjekk hvilken kodeliste som matches
source_values = set(df_input['TKNR'].astype(str).unique())
target_values = set(df_output['geografi'].astype(str).unique())

match = manager.find_matching_codelist(
    'TKNR', 'geografi',
    source_values, target_values
)

if match:
    print(f"Fant match: {match['name']}")
else:
    print("Ingen match funnet")
```

## 📚 Ressurser

- [JSON validator](https://jsonlint.com/)
- [Regex tester](https://regex101.com/)
- Se `examples/` for eksempler på ferdig lagde kodelister
