# Quick Start Guide - Forbedret Prep-Script Generator

## 🚀 For tabeller med ÉN input-fil

```bash
python generate_prep_script_v2.py input.xlsx --output output_referanse.xlsx --table-code OK-BEF001
```

## 🔗 For tabeller med FLERE input-filer (f.eks. sysselsetting)

```bash
python generate_prep_script_v2.py sysselsatte.xlsx befolkning.xlsx --output sysselsettingsandel_output.xlsx --table-code OK-SYS001
```

## 📊 Eksempel: Sysselsettingsandel

Typisk scenario:
- **Input 1**: Antall sysselsatte per bydel
- **Input 2**: Befolkning per bydel
- **Output**: Sysselsettingsandel (sysselsatte / befolkning * 100)

```bash
python generate_prep_script_v2.py \
    input_sysselsatte.xlsx \
    input_befolkning.xlsx \
    --output referanse_sysselsettingsandel.xlsx \
    --table-code OK-SYS001
```

Dette genererer: `OK-SYS001_prep.py` med:
- Automatisk mapping av kolonner fra begge input-filer
- Kodeliste-transformasjoner (hvis geografikoder oppdages)
- Placeholder-kode for join og beregninger
- TODO-kommentarer der du må fylle inn logikk

## ✏️ Etter generering

1. **Åpne det genererte scriptet** (f.eks. `OK-SYS001_prep.py`)

2. **Fyll inn TODO-seksjoner**:
   - Velg riktig kodeliste-mapping (tknr_to_px, ssb_to_px, etc.)
   - Definer join-logikk (hvilke kolonner skal matches)
   - Legg til beregninger (andeler, summer, etc.)

3. **Test scriptet**:
```bash
python OK-SYS001_prep.py sysselsatte.xlsx befolkning.xlsx output.xlsx
```

4. **Lagre i training_data** når det fungerer:
```
training_data/
  OK-SYS001/
    ├── input_sysselsatte.xlsx
    ├── input_befolkning.xlsx
    ├── output_referanse.xlsx
    ├── OK-SYS001_prep.py          # Din korrigerte versjon
    └── metadata.json               # Kopier fra metadata_template.json
```

## 🎯 Hva systemet nå gjør automatisk

✅ **Kolonnemapping** - Finner matches basert på navn og innhold  
✅ **Kodeliste-deteksjon** - Oppdager geografiske koder automatisk  
✅ **Multi-input håndtering** - Støtte for flere input-filer  
✅ **Template-generering** - Lager grunnstruktur med TODO-markers  

## 💡 Tips

### Geografiske kolonner
Hvis du har kolonner med TKNR, SSB-koder, etc., vil systemet:
1. Automatisk finne riktig kodeliste
2. Generere kode for transformasjon
3. Du må velge om du vil ha kun koder, eller koder + navn

### Beregninger
For andeler/prosenter, skriv inn i TODO-seksjonen:
```python
df_combined['sysselsettingsandel'] = (
    df_combined['antall_sysselsatte'] / df_combined['befolkning'] * 100
).round(1)
```

### Joins
Vanlige join-patterns:
```python
# Left join (beholder alle rader fra venstre)
df_combined = df1_transformed.merge(df2_transformed, on='bydel', how='left')

# Inner join (kun rader som matches)
df_combined = df1_transformed.merge(df2_transformed, on=['bydel', 'år'], how='inner')
```

## 📚 Neste steg: Machine Learning

Når du har ~10-20 tabeller lagret i `training_data/`:
1. Systemet lærer vanlige mønstre
2. Bedre automatisk mapping
3. Mindre manuelle justeringer

Ved ~50+ tabeller:
- Kan trene lokal ML-modell (Ollama/CodeLlama)
- Fullt automatisk generering for enkle tabeller
