# fin-stat-prep

Automatisk generering av dataprep-script for statistikktabeller.

**Finansstatistikk Preparation Tool** - Genererer Python-script som transformerer rådata til ferdigformaterte statistikktabeller for Oslo kommune.

## 📁 Prosjektstruktur

```
fin-stat-prep/
├── README.md                    # Denne filen
├── generate_prep_script.py      # Hovedverktøy for kodegenerering
├── codelist_manager.py          # Håndtering av kodelister
├── KODELISTER_GUIDE.md          # Guide for kodelister
├── README_ML_STRATEGI.md        # Strategi for maskinlæring
├── README_transformer.md        # Dokumentasjon for transformer-verktøy
├── kodelister/                  # JSON-kodelister
├── examples/                    # Eksempler (kommer)
└── training_data/              # Treningsdata for ML (kommer)
```

## 🎯 Hva gjør dette verktøyet?

Dette verktøyet **genererer Python-script** som transformerer rådata til ferdigformaterte statistikktabeller.

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

- ✅ Regelbasert kodegenerering
- ✅ Kolonnenavn-mapping
- ✅ Kategori-verdimapping
- ✅ Validering
- ⏳ ML-basert forbedring (venter på treningsdata)
- ⏳ Template-bibliotek
- ⏳ Automatisk testing

## 🔧 Tekniske detaljer

### Hva fungerer godt nå:
- Kolonnenavn med høy likhet (f.eks. "antall" → "antall barn")
- Eksakte kategori-match
- Grunnleggende struktur

### Hva krever ofte manuell justering:
- Komplekse kode-konverteringer (f.eks. TKNR 301 → 30105)
- Nye kolonner som beregnes fra eksisterende
- Tidsperiode-transformasjoner
- Aggregeringer

## 📞 Support

Ved problemer eller spørsmål, se dokumentasjonen eller kontakt prosjekteier.

## 📝 Lisens

Internt verktøy for Oslo kommune.
