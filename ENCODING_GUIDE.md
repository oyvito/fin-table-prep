# Encoding-håndtering

## Problem
Windows PowerShell og Python kan ha encoding-problemer med norske tegn (æ, ø, å).

## Løsning
Vi har lagt til encoding-håndtering i **to steder**:

### 1. generate_prep_script_v2.py (hovedskriptet)
```python
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

### 2. Genererte prep-scripts
Template inkluderer samme encoding-håndtering:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

## Beste praksis

### Fil I/O
Bruk **alltid** `encoding='utf-8'` når du åpner filer:

```python
# JSON-filer
with open('fil.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('fil.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Pandas Excel
OpenPyXL håndterer encoding automatisk, men vær oppmerksom på:

#### XML-encoding i Excel
Excel lagrer noen spesialtegn som XML-entities internt:
- `_x0032_025` → `'2025'` (tall)
- `_x0031_5-24_x0020_år` → `'15-24 år'` (tekst med mellomrom)
- `_x0036_0_x0020_-74` → `'60 -74'` (ekstra mellomrom før bindestrek)

**Løsning:** Vi har `decode_xml_strings()` funksjon i genererte scripts:
```python
def decode_xml_strings(df):
    """
    Dekoder XML-encoded strings i Excel-filer.
    Normaliserer også whitespace for å unngå match-problemer.
    """
    import re
    
    def decode_string(val):
        if not isinstance(val, str):
            return val
        # Regex: _x[4-digit hex]_ → tilsvarende Unicode-tegn
        decoded = re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), val)
        # Normaliser whitespace (fjern doble mellomrom, ' -' → '-')
        decoded = ' '.join(decoded.split())
        decoded = decoded.replace(' -', '-')
        return decoded
    
    for col in df.columns:
        if df[col].dtype == 'object':  # Kun tekstkolonner
            df[col] = df[col].apply(decode_string)
    
    return df
```

**Bruk:**
```python
df = pd.read_excel('input.xlsx')
df = normalize_column_names(df)  # Først: lowercase kolonnenavn
df = decode_xml_strings(df)      # Deretter: dekod XML-entities
```

#### Generelt
- Bruk `str.strip()` for å fjerne whitespace

### Print til console
Med vår encoding-setup kan du trygt printe norske tegn:
```python
print("✓ Leser Øyvind's data fra Ålesund")  # Fungerer!
```

## Testing
Test at encoding fungerer:
```powershell
python -c "print('Test: Æ Ø Å æ ø å')"
```

Forventet output:
```
Test: Æ Ø Å æ ø å
```

## Hvis du fortsatt får problemer
1. Sjekk at filen er lagret som UTF-8 (ikke ANSI)
2. I VS Code: Se nederst til høyre - skal stå "UTF-8"
3. Bruk `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` i PowerShell
