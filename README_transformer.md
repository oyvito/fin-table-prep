# Generisk Transformasjonsanalyse-verktøy

Dette scriptet analyserer transformasjoner mellom to Excel-filer automatisk, og kan også utføre transformasjonen.

## Bruk

### Grunnleggende bruk - kun analyse:
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx
```

### Med spesifikke ark:
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx --input-sheet a --output-sheet ark1
```

### Generer Python-kode for transformasjon:
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx --generate-code
```

### **NYT! Utfør transformasjon interaktivt:**
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx --transform output_transformed.xlsx
```
Scriptet vil:
1. Endre kolonnenavn automatisk
2. Spørre om bekreftelse for hver verdi-transformasjon
3. Lagre resultatet

### **NYT! Utfør transformasjon automatisk:**
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx --transform output_transformed.xlsx --auto
```
Anvender alle transformasjoner uten å spørre.

### Justere likhet-terskel for kolonnenavn:
```bash
python analyze_transformations_generic.py input.xlsx output.xlsx --similarity-threshold 0.7
```

## Hva scriptet finner

### 1. Kolonnenavn-endringer
- Automatisk matching basert på navn-likhet
- Automatisk matching basert på datainnhold
- Viser nye og fjernede kolonner

### 2. Kategori/verdi-transformasjoner
- Finner endringer i kategoriske verdier (f.eks. "1: 0 - 5" -> "0-5 år")
- Viser kun verdier som faktisk har endret seg
- Fungerer best for kolonner med < 50 unike verdier

### 3. Datavolum-endring
- Analyser om det har skjedd aggregering eller disaggregering
- Viser antall rader før/etter og tolkning

### 4. Datatype-endringer
- Viser kolonner som har skiftet datatype (f.eks. int -> string)

### 5. Python-kode generering
- Genererer kode for å utføre transformasjonen
- Inkluderer kolonnenavn-mapping og verdi-transformasjoner
- Markerer områder som må fylles inn manuelt

## Eksempler

### OK-SOS002 eksempel:
```bash
python analyze_transformations_generic.py ok-sos002_input.xlsx OK-SOS002_prep_output.xlsx --input-sheet a --output-sheet ark1 --generate-code
```

Finner:
- Kolonnenavn: `periode` -> `år`, `barn_alder` -> `barnets alder`, osv.
- Geografikoder: TKNR-koder -> 5-sifrede bydelskoder
- Alderskategorier: `1: 0 - 5` -> `0-5 år`
- Historiske data: 288 rader (2024) -> 5184 rader (2006-2024)

## Begrensninger

- Fungerer best med kategoriske data
- Krever at kolonnene har sammenlignbart innhold
- Generert kode må ofte justeres manuelt
- Kan feile hvis det er veldig mange unike verdier

## Tips

- Bruk `--similarity-threshold` for å justere hvor streng matching skal være
- Hvis en kolonne ikke mappes riktig, kan du manuelt redigere den genererte koden
- Sjekk alltid den genererte koden før du kjører den!
