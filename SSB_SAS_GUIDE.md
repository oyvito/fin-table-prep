# Håndtering av SSB SAS-uttrekk

## 📊 Kilde: SSB sine databaser via SAS

### Typisk struktur:

SSB-uttrekk har ofte **kolonnepar**:
- `variabel` - Koden (tall/ID)
- `variabel_fmt` - Navnet (tekst)

**Eksempel:**
```
bydel2='030101', bydel2_fmt='Gamle Oslo'
kjoenn='1', kjoenn_fmt='Mann'
aldgr5='25', aldgr5_fmt='25-29 år'
```

---

## 🔧 Transformasjonsregler

### ✅ Når kodeliste FINNES (geografiske variabler):

**Input:**
```
bydel2='030101'
bydel2_fmt='Gamle Oslo'
```

**Transformasjon:**
1. Bruk kodeliste `SSB_til_PX_geo_bydel`
2. `030101` → PX-kode `1`
3. Hent standardisert navn fra kodeliste: `"Gamle Oslo"`

**Output:**
```python
df['geografi'] = df['bydel2'].map(kodeliste['mappings'])  # '030101' → '1'
df['geografi_navn'] = df['geografi'].map(kodeliste['labels'])  # '1' → 'Gamle Oslo'
# Ignorer bydel2_fmt - vi har standardisert navn fra kodeliste
```

---

### ✅ Når kodeliste IKKE finnes:

**Input:**
```
utdanning='3'
utdanning_fmt='Videregående skole'
```

**Transformasjon:**
Behold begge, men standardiser navnene.

**Output:**
```python
df['utdanning'] = df['utdanning']  # Kode som den er
df['utdanning_navn'] = df['utdanning_fmt']  # Bruk _fmt som navn
```

---

## 🗺️ Geografiske variabler (bruk kodeliste)

| SSB-kolonne | _fmt-kolonne | Kodeliste | Output |
|-------------|--------------|-----------|--------|
| `bydel2` | `bydel2_fmt` | `SSB_til_PX_geo_bydel` | `geografi` + `geografi_navn` |
| `b_delbydel2017_01` | `b_delbydel2017_01_fmt` | `SSB_til_PX_geo_delbydel` | `geografi` + `geografi_navn` |
| `bo_bydel` | `bo_bydel_fmt` | `SSB_til_PX_geo_bydel` | `geografi` + `geografi_navn` |

**Resultat:** Ignorér `_fmt` når kodeliste brukes (vi har standardiserte navn).

---

## 📋 Andre variabler (behold begge)

| SSB-kolonne | _fmt-kolonne | Output kode | Output navn |
|-------------|--------------|-------------|-------------|
| `kjoenn` | `kjoenn_fmt` | `kjønn` | `kjønn_navn` |
| `aldgr5` | `aldgr5_fmt` | `alder` | `alder_navn` |
| `utdanning` | `utdanning_fmt` | `utdanning` | `utdanning_navn` |

**Resultat:** Behold begge, bare endre kolonnenavn til standard.

### 💡 ML-læring over tid:

Etter hvert som systemet ser flere eksempler, vil det lære at:

**Variabler som KUN trenger navn (ikke kode):**
- `kjønn` → Output: Kun "Mann"/"Kvinne"/"Begge kjønn"
- `alder` → Output: Kun "15-24 år", "25-39 år" osv.
- `utdanning` → Output: Kun "Videregående", "Universitets-/høgskole" osv.

**Variabler som ALLTID trenger kode:**
- Geografiske (PxWeb-krav)
- Variabler brukt i joins
- Variabler brukt i filtre/aggregeringer

**Midlertidig tilnærming (før ML er trent):**
Behold begge for å være trygg. Når du ser at kode-kolonnen aldri brukes i output, dokumenter dette i `metadata.json` slik at modellen kan lære.

---

## ⚠️ XML-encoding

SSB-data kan ha XML-encoded verdier:
- `_x0030_` = `0`
- `_x0031_` = `1`
- `_x0032_` = `2`
- `_x0020_` = mellomrom
- `aargang='_x0032_024'` = `'2024'`

**Dekoding:**
```python
import html

def decode_xml_value(val):
    """Dekoder XML-encoded verdier fra SSB."""
    if pd.isna(val):
        return val
    
    val_str = str(val)
    
    # Fjern XML-encoding
    if '_x00' in val_str:
        # Enkel dekoding av vanlige tilfeller
        val_str = val_str.replace('_x0030_', '0')
        val_str = val_str.replace('_x0031_', '1')
        val_str = val_str.replace('_x0032_', '2')
        # ... osv
        
        # Eller bruk html.unescape for komplekse tilfeller
    
    return val_str

# Bruk på relevante kolonner
df['aargang'] = df['aargang'].apply(decode_xml_value)
```

---

## 💡 Beslutningstre

```
Er det en geografisk variabel?
├─ JA: Finnes det kodeliste (SSB_til_PX_geo_*)?
│  ├─ JA: 
│  │  ├─ Transformer kode med kodeliste
│  │  ├─ Hent navn fra kodeliste
│  │  └─ IGNORER _fmt-kolonnen
│  └─ NEI:
│     ├─ Behold kode-kolonnen
│     └─ Behold _fmt som _navn
│
└─ NEI:
   ├─ Behold kode-kolonnen → standardiser navn
   └─ Behold _fmt-kolonnen → som _navn
```

---

## 📝 Eksempel-transformasjon

**Input (SSB SAS-uttrekk):**
```python
aargang='_x0032_024'
bydel2='030101'
bydel2_fmt='Gamle Oslo'
kjoenn='1'
kjoenn_fmt='Mann'
antall=1234
```

**Output (PxWeb-format):**
```python
år=2024                    # Dekodet
geografi='1'               # Fra SSB_til_PX_geo_bydel kodeliste
geografi_navn='Gamle Oslo' # Fra kodeliste (IKKE fra bydel2_fmt)
kjønn='Mann'               # Direkte fra kjoenn_fmt (ingen kodeliste)
antall=1234
```

**Kode:**
```python
# Dekod årstall
df['år'] = df['aargang'].apply(decode_xml_value).astype(int)

# Geografisk kode med kodeliste
bydel_kodeliste = load_codelist('SSB_til_PX_geo_bydel')
df['geografi'] = df['bydel2'].map(bydel_kodeliste['mappings'])
df['geografi_navn'] = df['geografi'].map(bydel_kodeliste['labels'])

# Kjønn - ingen kodeliste, bruk _fmt direkte
df['kjønn'] = df['kjoenn_fmt']

# Antall - direkte
df['antall'] = df['antall']

# Velg kolonner for output
df_output = df[['år', 'geografi', 'geografi_navn', 'kjønn', 'antall']]
```

---

## ✅ Huskeliste

- [ ] Identifiser geografiske variabler
- [ ] Sjekk om kodeliste finnes for hver variabel
- [ ] Dekod XML-encoding i årstall og andre kolonner
- [ ] Bruk kodelister for geografiske variabler
- [ ] Behold kode + navn for ikke-geografiske variabler
- [ ] Standardiser kolonnenavn (små bokstaver)
- [ ] Valider output mot kontrollskjema

---

**Se også:**
- `kontrollskjema.json` - Standardvariabler
- `kodelister/` - Tilgjengelige kodelister
- `validate_table.py` - Valider output
