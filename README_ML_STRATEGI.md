# Automatisk Generering av Prep-Script

## 🎯 Konsept

Dette verktøyet genererer Python-script (`tabellkode_prep.py`) som transformerer input-data til output-format.

## 📋 Bruk

### Grunnleggende:
```bash
python generate_prep_script.py input.xlsx output.xlsx --table-code OK-SOS002 --input-sheet a --output-sheet ark1
```

Dette genererer: `OK-SOS002_prep.py`

### Kjør det genererte scriptet:
```bash
python OK-SOS002_prep.py ny_input.xlsx transformed_output.xlsx
```

## ✅ Hva scriptet inkluderer

Det genererte prep-scriptet har:

1. **Input-validering**: Sjekker at alle nødvendige kolonner finnes
2. **Transformasjonslogikk**:
   - Kolonnenavn-endringer
   - Kategori-verdimappinger
   - Sletting av unødvendige kolonner
   - Placeholders for manglende kolonner
3. **Output-validering**: Sjekker at output har riktig struktur
4. **Feilhåndtering**: Gir klare feilmeldinger

## 🔍 Nåværende begrensninger

- Ikke alle kolonnemappings blir funnet automatisk
- Komplekse transformasjoner (f.eks. TKNR-koding) må fylles inn manuelt
- Krever ofte manuell justering etter generering

## 🤖 Fremtidig forbedring med maskinlæring

### Fase 1: Datainnsamling (nå - 6 måneder)
For hver tabell:
1. Input-fil (rådata)
2. Output-fil (ferdig transformert)
3. **Korrekt prep-script** (manuelt laget/justert)

### Fase 2: Modelltrening (etter ~50-100 tabeller)

**Tilnærming**: Few-shot learning med LLM eller spesialisert transformasjonsmodell

**Input til modellen**:
- Input DataFrame struktur + sample data
- Output DataFrame struktur + sample data
- Historiske eksempler på lignende transformasjoner

**Output fra modellen**:
- Komplett Python-kode for transformasjon
- Konfidenscore for hver transformasjon

**Treningsdata-format**:
```python
{
    "table_code": "OK-SOS002",
    "input_columns": ["periode", "forsorgerstatus", "barn_alder", ...],
    "output_columns": ["år", "forsørgerstatus", "barnets alder", ...],
    "input_sample": [...],
    "output_sample": [...],
    "correct_transformation": """
        # Korrekt kode her
        df = df.rename(columns={'periode': 'år'})
        ...
    """
}
```

### Fase 3: Modelltyper som kan fungere

1. **GPT-4 / Claude med few-shot prompting**
   - Fordel: Krever lite treningsdata
   - Ulempe: Kostbart, kan være upålitelig

2. **CodeLlama / StarCoder fine-tuned**
   - Fordel: Open source, kan kjøres lokalt
   - Ulempe: Krever mer treningsdata

3. **Regelbasert + ML hybrid**
   - Bruk ML kun for vanskelige case
   - Regelbasert for enkle transformasjoner

### Fase 4: Kontinuerlig forbedring

```
For hver tabell:
1. Generer script automatisk
2. Menneske gjennomgår og justerer
3. Lagre korrekt versjon som treningsdata
4. Re-tren modell periodisk
5. Forbedret nøyaktighet over tid
```

## 📊 Metrikker for suksess

- **Nøyaktighet**: % av transformasjoner som er 100% korrekte
- **Dekningsgrad**: % av kolonner som mappes korrekt
- **Manuelle justeringer**: Antall linjer som må endres manuelt
- **Tidsbesparelse**: Tid spart vs manuell koding

### Målsetting:
- Etter 50 tabeller: 60% helt korrekte
- Etter 100 tabeller: 80% helt korrekte
- Etter 200 tabeller: 90% helt korrekte

## 🔧 Neste steg

1. **Kort sikt** (nå):
   - Bruk dette verktøyet som utgangspunkt
   - Juster manuelt
   - **Lagre både input, output OG korrekt script**

2. **Mellomlang sikt** (etter 20-30 tabeller):
   - Analyser vanlige mønstre
   - Forbedre regelbasert logikk
   - Bygg bibliotek av "templates"

3. **Lang sikt** (etter 50+ tabeller):
   - Tren ML-modell
   - A/B-test mot regelbasert
   - Gradvis overgang til ML-assistert generering

## 💡 Tips

- **Dokumenter alle manuelle endringer** - dette blir treningsdata
- **Kategoriser tabelltyper** - ulike typer kan ha ulike mønstre
- **Start enkelt** - perfeksjoner på enkle case først
- **Versjonskontroll** - alle genererte script bør være i git

## 📁 Mappestruktur for ML-trening (forslag)

```
training_data/
  OK-SOS002/
    input.xlsx
    output.xlsx
    prep_script.py        # Korrekt, manuelt justert
    metadata.json         # Tabelltype, kompleksitet, osv.
  OK-SOS003/
    ...
  models/
    transformation_model_v1.pkl
    training_log.txt
```
