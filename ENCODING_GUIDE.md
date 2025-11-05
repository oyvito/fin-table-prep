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
- XML-escaped values: `_x0031_` → `'1'` (decode_xml_escapes)
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
