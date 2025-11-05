# Analyseprosess for Multi-Input Transformasjon

**Oppdatert:** 2025-11-05  
**Formål:** Dokumentere den korrekte rekkefølgen for analyse og skriptgenerering

---

## 🎯 Overordnet Flyt

```
INPUT-FILER (originale kolonnenavn)
    ↓
ANALYSE-FASE (forstå strukturen)
    ↓
GENERERE PREP-SCRIPT (med standardisering)
    ↓
KJØRE PREP-SCRIPT (standardiser → merge → output)
```

---

## 📊 ANALYSE-FASE (generate_prep_script_v2.py)

**Prinsipp:** Analyser originalnavnene, foreslå standardnavn, MEN IKKE standardiser i analysen!

### FASE 1: Innlasting & Forberedelse
```python
# Last inn ALLE input-filer med ORIGINALE kolonnenavn
input_dfs = []
for input_file in input_files:
    df = pd.read_excel(input_file)  # Beholder originale navn!
    input_dfs.append(df)

# Last output-fil (referanse)
df_output = pd.read_excel(output_file)
```

**Viktig:** Ingen endring av kolonnenavn her!

---

### FASE 2: Variabel-Par Deteksjon (PER INPUT)
```python
# TIDLIG i analysen - før kolonnemapping!
variable_pairs_all = []
for df_input in input_dfs:
    pairs = detect_variable_pairs(df_input)
    # Eksempel: {base: 'bydel', label: 'bydel_fmt', pattern: '_fmt'}
    variable_pairs_all.append(pairs)
```

**Output:**
- Liste over par-forhold (kode/navn)
- Brukes senere for å unngå å mappe begge kolonner

**Hvorfor tidlig?**
- Informerer kolonnemapping (kan hoppe over _fmt-kolonner)
- Forebygger at vi mapper både 'bydel' og 'bydel_fmt'

---

### FASE 3: Kolonne-Mapping (PER INPUT)
```python
all_mappings = []
all_geographic_suggestions = []

for i, df_input in enumerate(input_dfs):
    result = find_column_mapping_with_codelists(
        df_input,           # Med ORIGINALE kolonnenavn
        df_output, 
        codelist_mgr, 
        kontrollskjema,
        table_code,
        known_pairs=variable_pairs_all[i]  # Bruker par-info!
    )
    
    # Lagre mappings: original_navn → standard_navn
    all_mappings.append({
        'mappings': result['mappings'],          # {'arb_gkrets_a': 'arbeidssted_grunnkrets'}
        'geographic_suggestions': result['geographic_suggestions']
    })
```

**Sub-steg i find_column_mapping_with_codelists():**

#### 3.1. Kontrollskjema-sjekk
```python
# Match mot standard_variables i kontrollskjema.json
# Eksempel: 'aar' → 'aargang', 'kjoenn' → 'kjoenn'
```

#### 3.2. Geografisk analyse
```python
# suggest_geographic_column_name()
# - Detekterer kontekst (arbeid/bosted)
# - Foreslår standardnavn basert på tabellkode
# Eksempel: 'arb_gkrets_a' → 'arbeidssted_grunnkrets'
```

#### 3.3. Kodeliste-matching
```python
# codelist_mgr.find_matching_codelist()
# - Sjekk verdier mot kjente kodelister
# Eksempel: [0, 1] → kjoenn.json
```

#### 3.4. Likhets-sjekk
```python
# similarity() for kolonnenavn som ikke matched over
# Eksempel: 'tot_ant' vs 'totalt_antall' = 0.75
```

#### 3.5. Innholdsanalyse
```python
# Sammenlign unike verdier mellom input/output
# Nyttig for å bekrefte mapping
```

**Output:**
- Mapping-dict per input: `{'original_navn': 'standard_navn'}`
- Geografiske forslag med begrunnelse
- Kodeliste-transformasjoner

---

### FASE 4: Felles Nøkkel-Identifikasjon (MULTI-INPUT)
```python
# KRITISK: Må bruke de FORESLÅTTE standardnavnene!
common_keys_info = identify_common_keys(
    input_dfs, 
    df_output,
    all_mappings  # <-- Bruker mapping-resultater!
)

# Intern logikk:
# 1. Konverter alle kolonner til standardnavn
mapped_cols = []
for df, mapping_info in zip(input_dfs, all_mappings):
    std_cols = [mapping_info['mappings'].get(col, col) for col in df.columns]
    mapped_cols.append(std_cols)

# 2. Finn felles kolonner (case-insensitive)
common = set(c.lower() for c in mapped_cols[0])
for cols in mapped_cols[1:]:
    common &= set(c.lower() for c in cols)

# 3. Filtrer bort measure-kolonner (antall, sum, etc.)
candidate_keys = [c for c in common if not is_measure_column(c)]

# 4. Beregn unikhetsratio per kolonne
# 5. Vurder om komposisjonen gir unik identifikasjon
```

**Output:**
- `candidate_keys`: ['aargang', 'arbeidssted_grunnkrets', 'kjoenn']
- `key_quality`: {'aargang': 0.01, 'arbeidssted_grunnkrets': 0.85, ...}
- `composite_uniqueness`: 0.98

**Hvorfor etter mapping?**
- 'arb_gkrets_a' (input1) og 'ny_krets_b' (input2) er ULIKE
- MEN 'arbeidssted_grunnkrets' (standard) finnes i BEGGE
- Vi ser fellesskap først når vi bruker standardnavn

---

### FASE 5: Verdi-Analyse
```python
# Sammenlign verdier i potensielle nøkkelkolonner
# Sjekk om input-verdier finnes i output
for key_col in candidate_keys:
    input_values = set()
    for df, mapping in zip(input_dfs, all_mappings):
        original_col = reverse_lookup(mapping, key_col)
        if original_col in df.columns:
            input_values.update(df[original_col].unique())
    
    output_values = set(df_output[key_col].unique())
    missing = input_values - output_values
```

**Output:**
- Manglende verdier
- Verdier som kun finnes i output (kan indikere aggregering)

---

### FASE 6: Aggregerings-Deteksjon
```python
# Kjør på FØRSTE input (kan utvides til å sjekke alle)
aggregation_insights = detect_aggregation_patterns(
    input_dfs[0], 
    df_output, 
    all_mappings[0]['mappings']
)
```

**Detekterer:**
- Gender rollup (kjoenn-kolonnen forsvinner)
- Geographic rollup (grunnkrets → bydel)
- Totalisering (sum/mean over grupper)

**TODO:** Burde sjekke ALLE inputs og MERGED data

---

## 🔨 GENERERINGS-FASE

### FASE 7: Script-Generering
```python
script_content = generate_script_content_multi_input(
    input_files,
    all_mappings,                  # Original → Standard mappings
    all_transformations,           # Kodeliste-transformasjoner
    all_geographic_suggestions,    # Begrunnelser (for kommentarer)
    aggregation_insights,
    df_output.columns.tolist(),
    table_code,
    common_keys_info,              # Felles nøkler (med standardnavn!)
    variable_pairs_all
)

# Skriv til fil
with open(f"{table_code}_prep.py", 'w') as f:
    f.write(script_content)
```

**Det genererte scriptet har følgende struktur:**

---

## 📝 GENERERT PREP-SCRIPT (f.eks. OK-SYS001_prep.py)

### Steg 1: Innlasting (originale navn)
```python
df_arbeidssted = pd.read_excel('input1.xlsx')
df_bosted = pd.read_excel('input2.xlsx')

# Kolonner: ['aar', 'arb_gkrets_a', 'arb_gkrets_a_fmt', 'kjoenn', ...]
```

---

### Steg 2: Datatype-Normalisering (ORIGINALE navn)
```python
# Viktig: Gjør FØR rename for å unngå KeyError
df_arbeidssted['aar'] = df_arbeidssted['aar'].astype(str)
df_arbeidssted['arb_gkrets_a'] = df_arbeidssted['arb_gkrets_a'].astype('Int64')

df_bosted['aar'] = df_bosted['aar'].astype(str)
df_bosted['ny_krets_b'] = df_bosted['ny_krets_b'].astype('Int64')
```

---

### Steg 3: STANDARDISERING (Rename)
```python
# NÅ SKJER STANDARDISERINGEN!
df_arbeidssted = df_arbeidssted.rename(columns={
    'aar': 'aargang',
    'arb_gkrets_a': 'arbeidssted_grunnkrets',
    'arb_gkrets_a_fmt': 'arbeidssted_grunnkrets_navn',
    'kjoenn': 'kjoenn',
    'ant_arb': 'antall_arbeidssted'
})

df_bosted = df_bosted.rename(columns={
    'aar': 'aargang',
    'ny_krets_b': 'arbeidssted_grunnkrets',  # SAMME standardnavn!
    'ny_krets_b_navn': 'arbeidssted_grunnkrets_navn',
    'kjoenn': 'kjoenn',
    'ant_bo': 'antall_bosted'
})
```

**Nå har begge DataFrames:**
- `aargang` (standardisert)
- `arbeidssted_grunnkrets` (standardisert, FELLES navn!)
- `kjoenn` (standardisert)

---

### Steg 4: Merge (standardiserte navn)
```python
# Merge på STANDARDNAVN
merged = pd.merge(
    df_arbeidssted,
    df_bosted,
    on=['aargang', 'arbeidssted_grunnkrets', 'kjoenn'],  # Standardnavn!
    how='outer',
    suffixes=('_arb', '_bo')
)
```

---

### Steg 5: Kodeliste-Transformasjoner
```python
# Legg til kodeliste-baserte kolonner (hvis nødvendig)
if 'kjoenn' in merged.columns:
    kjoenn_map = {0: 'Mann', 1: 'Kvinne'}
    merged['kjoenn_fmt'] = merged['kjoenn'].map(kjoenn_map)
```

---

### Steg 6: Aggregering/Beregninger
```python
# TODO: Implementer aggregeringer (hvis detektert i analysen)
# Eksempel: Group by bydel, sum antall
```

---

### Steg 7: Output
```python
# Velg kun kolonner som finnes i referanse-output
output_cols = ['aargang', 'arbeidssted_grunnkrets', 'antall', ...]
result = merged[output_cols]

# Skriv til Excel
result.to_excel(output_file, index=False)
```

---

## 🎓 NØKKEL-LÆRDOMMER

### ✅ RIKTIG TILNÆRMING

1. **Analyser med originale navn**
   - Forstå hva som faktisk finnes i dataen
   - Match mot kontrollskjema/kodelister

2. **Foreslå standardnavn**
   - Geografiske kolonner får kontekstuelle navn
   - Lagre mapping: original → standard

3. **Identifiser felles nøkler VED Å BRUKE standardnavn**
   - Konverter midlertidig til standard for sammenligning
   - Finn felles kolonner PÅ TVERS av inputs

4. **Generert script standardiserer FØRST, merger DERETTER**
   - Innlasting med originale navn
   - Rename til standardnavn
   - Merge på standardnavn

### ❌ TIDLIGERE FEIL

1. ~~Identifisere felles nøkler med originale navn~~
   - 'arb_gkrets_a' ≠ 'ny_krets_b' → ingen felles nøkler funnet
   
2. ~~Standardisere i analyse-fasen~~
   - Ville ødelagt mapping mot kontrollskjema
   
3. ~~Variabel-par deteksjon etter kolonnemapping~~
   - Informasjonen kommer for sent til å påvirke mapping

---

## 🔄 FORBEDRINGER Å IMPLEMENTERE

### 1. Pass variabel-par til kolonnemapping
```python
result = find_column_mapping_with_codelists(
    df_input, 
    df_output, 
    codelist_mgr, 
    kontrollskjema,
    table_code,
    known_pairs=variable_pairs  # NY PARAMETER
)
```

**Effekt:** Hopper over _fmt-kolonner i første runde

---

### 2. Bruk mappings i identify_common_keys
```python
def identify_common_keys(input_dfs, output_df, all_mappings):
    """
    Args:
        all_mappings: Liste med {'mappings': {...}} per input
    """
    # Konverter til standardnavn før sammenligning
    mapped_cols = []
    for df, mapping_info in zip(input_dfs, all_mappings):
        std_cols = [mapping_info['mappings'].get(col, col) 
                   for col in df.columns]
        mapped_cols.append(set(c.lower() for c in std_cols))
    
    # Finn felles standardnavn
    common = mapped_cols[0]
    for cols in mapped_cols[1:]:
        common &= cols
    
    return list(common)
```

**Effekt:** Finner 'arbeidssted_grunnkrets' som felles selv om original er forskjellig

---

### 3. Case-insensitive kolonnenavn i generert script
```python
# Legg til i toppen av generert script:
def normalize_columns(df):
    """Normaliser kolonnenavn til lowercase."""
    df.columns = df.columns.str.lower()
    return df

df1 = normalize_columns(df1)
df2 = normalize_columns(df2)
```

**Effekt:** Unngår KJOENN vs kjoenn-problemer

---

### 4. Aggregering på merged data
```python
# I stedet for kun første input:
aggregation_insights = detect_aggregation_patterns(
    merged_preview,  # Simuler merge før generering
    df_output,
    final_mappings
)
```

**Effekt:** Ser aggregeringer som skjer PÅ TVERS av inputs

---

## 📈 NESTE STEG

1. ✅ Dokumentert korrekt flyt
2. ⏳ Implementer forbedring #2 (mappings til identify_common_keys)
3. ⏳ Implementer forbedring #3 (case-insensitive i generert script)
4. ⏳ Test med OK-SYS002
5. ⏳ Implementer forbedring #1 (variable_pairs til mapping)
6. ⏳ Implementer forbedring #4 (aggregering på merged)

---

**Konklusjon:** Standardisering er det SISTE scriptet gjør, men analysen må BRUKE de foreslåtte standardnavnene for å finne felles nøkler.
