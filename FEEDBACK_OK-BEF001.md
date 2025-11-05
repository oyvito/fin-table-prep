# Feedback-loop: OK-BEF001

**Dato:** 2025-11-05  
**Tabell:** OK-BEF001 (Befolkning)

## Input vs. Output

**Input kolonner:**
- aargang, alderu, bydel2, kjoenn, alderu_fmt, bydel2_fmt, kjoenn_fmt, antall

**Output kolonner:**
- år, bosted, bosted.1, kjønn, kjønn.1, alder, alder.1, antall

**Output har 3417 input-rader → 5507 output-rader** (mer data etter transformasjon)

---

## ✅ Hva fungerte bra (kan generaliseres)

### 1. Geografisk navnforslag ✅
- **Detekterte korrekt:** `bydel2` → `bosted` (ikke `bydel`)
- **Begrunnelse:** "Domene 'befolkning' indikerer bostedsdata"
- **Konklusjon:** `suggest_geographic_column_name()` fungerer!

### 2. Standardiseringsforslag ✅
- Fant korrekt: `aargang` → `år`
- Fant korrekt: `alderu` → `alder`
- Fant korrekt: `kjoenn` → `kjønn`
- **Konklusjon:** Kontrollskjema-matching fungerer

### 3. Mappet alle input-kolonner ✅
- 8/8 kolonner mappet
- Ingen umappede input-kolonner
- **Konklusjon:** Mapping-algoritmen er robust

---

## ❌ Hva gikk galt (trenger forbedring)

### 1. Duplikate mappings til samme output-kolonne ❌ **KRITISK**

**Problem:**
```python
'alderu': 'alder',      # OK
'alderu_fmt': 'alder',  # FEIL - duplikat!
'kjoenn': 'kjønn',      # OK  
'kjoenn_fmt': 'kjønn',  # FEIL - duplikat!
```

**Faktisk behov:**
- Output har `alder` OG `alder.1` (to kolonner)
- Output har `kjønn` OG `kjønn.1` (to kolonner)
- Dette er kode+navn-par!

**Årsak:**
- Applikasjonen forstår ikke at `.1` i kolonnenavn betyr "andre forekomst"
- Burde mappe: `alderu` → `alder`, `alderu_fmt` → `alder.1`

**Type:** **GENERELL forbedring** - Mange tabeller har duplikate kolonnenavn med `.1`, `.2` etc.

---

### 2. Kodeliste ikke detektert ❌

**Problem:**
- `bydel2` inneholder SSB-koder (030101, 030102...)
- `bosted` i output har PX-koder (1, 2, 3...)
- Kodeliste `SSB_til_PX_geo_bydel` finnes, men ikke brukt!

**Output:**
- "Kodeliste-transformasjoner: 0"

**Årsak:**
- Mapping fant `bydel2` → `bosted`, men sjekket ikke om VERDIENE matcher
- Kodeliste-logikk kjørte bare på umappede kolonner (linje "for in_col in input_cols: if in_col in mappings: continue")

**Type:** **GENERELL forbedring** - Må sjekke kodelister selv når kolonnenavn matcher

---

### 3. Umappede output-kolonner delvis ❌

**Problem:**
- `kjønn.1` og `alder.1` rapportert som umappet
- Men de finnes i output!

**Årsak:**
- Se #1 - duplikate mappings

**Type:** Følgefeil av #1

---

### 4. Generert rename-dict er feil ❌

```python
df1_transformed = df1_transformed.rename(columns={
    'aargang': 'år',
    'alderu': 'alder',
    'bydel2': 'bosted',        # Trenger kodeliste-transformasjon!
    'kjoenn': 'kjønn',
    'alderu_fmt': 'alder',     # FEIL - skal være 'alder.1'
    'kjoenn_fmt': 'kjønn',     # FEIL - skal være 'kjønn.1'
    'antall': 'antall',
    'bydel2_fmt': 'bosted.1',  # OK!
})
```

**Type:** Følgefeil av #1 og #2

---

## 📋 Tabell-spesifikke observasjoner

1. **Mer rader i output enn input** (3417 → 5507)
   - Dette tyder på pivoting/unpivoting eller join
   - Kan IKKE være en enkel rename + select
   - Applikasjonen bør advare: "⚠️ Output har flere rader - mulig pivoting/aggregering?"

2. **`.1` suffix i output-kolonner**
   - Pandas-navnekonvensjon for duplikater
   - Indikerer at tabellen har to kolonner med samme navn (pandas legger til .1)

---

## 🔧 Foreslåtte forbedringer

### Prioritet 1: Håndter `.1`, `.2` suffixer i output **[GENERELL]**

**Løsning:**
```python
# Når vi ser duplikate mappings til samme target:
# alderu → alder, alderu_fmt → alder
# OG output har både 'alder' og 'alder.1'
# → Fordel mappings: alderu → alder, alderu_fmt → alder.1
```

**Implementer i:** `find_column_mapping_with_codelists()`

---

### Prioritet 2: Sjekk kodelister selv når navn matcher **[GENERELL]**

**Problem:** 
Kodeliste-sjekk hopper over kolonner som allerede er mappet

**Løsning:**
```python
# Etter kontrollskjema-matching:
# Sjekk om mappede kolonner trenger kodeliste-transformasjon
for in_col, out_col in mappings.items():
    codelist = find_matching_codelist(in_col, out_col, ...)
    if codelist:
        value_transformations[in_col] = {...}
```

**Implementer i:** `find_column_mapping_with_codelists()` - flytt kodeliste-sjekk

---

### Prioritet 3: Detekter pivoting/unpivoting **[GENERELL]**

**Løsning:**
```python
if len(df_output) > len(df_input) * 1.2:  # 20% mer
    print("⚠️  Output har betydelig flere rader - mulig unpivoting/join")
    print("    Dette scriptet kan trenge manuell pivoting-logikk")
```

**Implementer i:** `generate_multi_input_script()`

---

## 🎯 Neste steg

1. **Fiks Prioritet 1 og 2** (generelle forbedringer)
2. **Test på nytt** med OK-BEF001
3. **Test på OK-SYS001** (multi-input) for å se om multi-fil-logikk fungerer
4. **Iterer** basert på ny feedback

---

## Konklusjon

**Positiv overraskelse:**
- Geografisk navnforslag fungerer!
- Kontrollskjema-matching fungerer!

**Kritiske mangler:**
- Duplikat-håndtering (`.1` suffix)
- Kodeliste-transformasjon selv når navn matcher

**Estimat:** Med 2 fikser kan applikasjonen sannsynligvis generere 70-80% korrekt script for enkle tabeller.
