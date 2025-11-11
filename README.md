# fin-stat-prep

Automatisk generering av dataprep-script for statistikktabeller.

**Finansstatistikk Preparation Tool** - Genererer Python-script som transformerer rådata til ferdigformaterte statistikktabeller for Oslo kommune.

## 📁 Prosjektstruktur

```
fin-stat-prep/
├── README.md                    # Denne filen
├── generate_prep_script_v2.py   # Hovedverktøy for kodegenerering (v2)
├── aggregering.py               # Aggregeringsmodul (parallell strategi)
├── andeler.py                   # Andelsberegninger (teller/nevner)
├── analysemetodikk.py           # 5-stegs analysemetode
├── codelist_manager.py          # Håndtering av kodelister
├── KODELISTER_GUIDE.md          # Guide for kodelister
├── ENCODING_GUIDE.md            # Guide for UTF-8 encoding
├── README_ML_STRATEGI.md        # Strategi for maskinlæring
├── README_transformer.md        # Dokumentasjon for transformer-verktøy
├── kodelister/                  # JSON-kodelister
├── examples/                    # Eksempler (kommer)
└── training_data/              # Treningsdata for ML (kommer)
```

## 🎯 Hva gjør dette verktøyet?

Dette verktøyet **genererer Python-script** som transformerer rådata til ferdigformaterte statistikktabeller.

### Nytt i v2 (November 2025):
- ✅ **Automatisk aggregering** - Detekterer og genererer totalkategorier (f.eks. "Begge kjønn", "Oslo i alt")
- ✅ **Andelsberegninger** - Separat modul for teller/nevner-beregninger (sysselsatte/befolkning, etc.)
- ✅ **Statistikkvariabel-deteksjon** - Finner automatisk hvilke kolonner som skal summeres
- ✅ **Variabel-par identifikasjon** - Gjenkjenner kode/label-par (f.eks. `bosted` / `bosted.1`)
- ✅ **Navne-uavhengig deteksjon** - Bruker verdimønstre i stedet for kolonnenavn
- ✅ **Multi-input håndtering** - Støtte for tabeller med flere input-filer
- ✅ **Modulær arkitektur** - Gjenbrukbare moduler (`aggregering.py`, `andeler.py`)

### Input:
- En input Excel-fil (rådata)
- En output Excel-fil (ønsket format)
- Tabellkode (f.eks. OK-SOS002)

### Output:
- `tabellkode_prep.py` - Kjørbart Python-script med:
  - Input-validering
  - Transformasjonslogikk
  - Output-validering
  - Feilhåndtering

## 🚀 Kom i gang

### Installasjon

```bash
# Installer nødvendige pakker
pip install pandas openpyxl
```

### Grunnleggende bruk

**For tabeller med én input-fil:**
```bash
# Generer prep-script (v2 - forbedret versjon)
python generate_prep_script_v2.py input.xlsx --output output_referanse.xlsx --table-code OK-BEF001

# Dette lager: OK-BEF001_prep.py
# Juster scriptet manuelt om nødvendig

# Kjør det genererte scriptet
python OK-BEF001_prep.py ny_input.xlsx ferdig_output.xlsx
```

**For tabeller med flere input-filer (f.eks. sysselsetting):**
```bash
# Generer prep-script med to input-filer
python generate_prep_script_v2.py sysselsatte.xlsx befolkning.xlsx \
    --output sysselsettingsandel_output.xlsx --table-code OK-SYS001

# Kjør scriptet med begge input-filer
python OK-SYS001_prep.py sysselsatte.xlsx befolkning.xlsx output.xlsx
```

📖 **Se [QUICK_START.md](QUICK_START.md) for detaljert guide**

### Eksempel: OK-SOS002

```bash
# Fra OK-SOS002-mappen
python generate_prep_script.py \
    ok-sos002_input.xlsx \
    OK-SOS002_prep_output.xlsx \
    --table-code OK-SOS002 \
    --input-sheet a \
    --output-sheet ark1

# Generer: OK-SOS002_prep.py
# Juster manuelt (f.eks. TKNR-koding)
# Test: python OK-SOS002_prep.py test_input.xlsx test_output.xlsx
```

## 📚 Dokumentasjon

- **[ML-strategi](README_ML_STRATEGI.md)** - Plan for maskinlæring og automatisering
- **[Transformer-verktøy](README_transformer.md)** - Analyse av transformasjoner

## 🎯 Arbeidsflyt

### For hver ny tabell:

1. **Generer utgangspunkt**
   ```bash
   python generate_prep_script.py input.xlsx output.xlsx --table-code TABELL-XXX
   ```

2. **Juster manuelt**
   - Åpne det genererte scriptet
   - Fyll inn logikk for kolonner merket med TODO
   - Test grundig

3. **Lagre for fremtidig ML-trening**
   ```
   training_data/
   └── TABELL-XXX/
       ├── input.xlsx
       ├── output.xlsx
       ├── TABELL-XXX_prep.py      # Korrekt, testet versjon
       └── metadata.json            # Notater om tabellen
   ```

4. **Dokumenter**
   - Hva fungerte automatisk?
   - Hva måtte justeres?
   - Spesielle utfordringer?

## 🤖 Fremtidsplaner: Maskinlæring

Når vi har 50-100 tabeller med korrekte prep-script:

1. **Tren ML-modell** (GPT-4 fine-tuning eller CodeLlama)
2. **Forbedret nøyaktighet** over tid
3. **Mindre manuell justering** nødvendig

Se [ML-strategi](README_ML_STRATEGI.md) for detaljer.

## 📊 Status

**Nåværende versjon: v2 (November 2025)**

### Fullførte funksjoner:
- ✅ Regelbasert kodegenerering
- ✅ Kolonnenavn-mapping med fuzzy matching
- ✅ Kategori-verdimapping med kodelister
- ✅ **Automatisk aggregeringsdeteksjon** (navn-uavhengig)
- ✅ **Statistikkvariabel-identifikasjon**
- ✅ **Variabel-par gjenkjenning** (kode/label)
- ✅ **Multi-input merge-logikk**
- ✅ **Modulær aggregering** (`aggregering.py`)
- ✅ UTF-8 encoding-håndtering
- ✅ Validering

### Under utvikling:
- ⏳ ML-basert forbedring (venter på treningsdata)
- ⏳ Beregningsdeteksjon (kolonner som beregnes fra andre)
- ⏳ Template-bibliotek
- ⏳ Automatisk testing

### Aggregeringstyper som støttes:
1. **Binary total** - 2→3 verdier (f.eks. Mann/Kvinne → Begge kjønn)
2. **Geography rollup** - Detaljert→Total (f.eks. Bydel → Oslo i alt)
3. **Category grouping** - Mange→Få kategorier
4. **Kryssaggregeringer** - Automatisk kombinasjon av totalkategorier

## 🔧 Tekniske detaljer

### Analysemetodikk (5 faser):

**FASE 1: Variabel-par og statistikkvariabel-deteksjon**
- Identifiserer kode/label-par (f.eks. `bosted` / `bosted.1`)
- Detekterer statistikkvariable (kolonner som skal summeres)
- Skiller dimensjoner fra måltall

**FASE 2: Kolonnemapping**
- Fuzzy matching av kolonnenavn
- Kodeliste-basert transformasjon
- Geografiske kolonneforslag

**FASE 3: Multi-input analyse**
- Identifiserer felles nøkkelkolonner
- Foreslår merge-strategi
- Detekterer year/geo mismatches

**FASE 4: Aggregeringsdeteksjon** (navn-uavhengig!)
- Sammenligner input vs output VERDIER
- Klassifiserer aggregeringstype basert på mønstre
- Genererer totalkategori-informasjon

**FASE 5: Script-generering**
- Genererer Python-kode som bruker `aggregering.py`
- Inkluderer transformasjoner og merge-logikk
- Dokumenterer automatiske vs manuelle steg

### Hva fungerer godt nå:
- Kolonnenavn med høy likhet (f.eks. "antall" → "antall barn")
- Eksakte kategori-match via kodelister
- **Automatisk aggregering** (Oslo i alt, Begge kjønn, etc.)
- **Multi-input merge** basert på felles nøkler
- Grunnleggende struktur

### Hva krever ofte manuell justering:
- Komplekse kode-konverteringer (f.eks. TKNR 301 → 30105)
- Nye kolonner som beregnes fra eksisterende (FASE 5 kommer)
- Tidsperiode-transformasjoner
- Spesielle business-regler

## 📞 Support

Ved problemer eller spørsmål, se dokumentasjonen eller kontakt prosjekteier.

## 📝 Lisens

Internt verktøy for Oslo kommune.
