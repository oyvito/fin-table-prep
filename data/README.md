# Data

Denne mappen inneholder data og konfigurasjon for ulike statistikktabeller.

## Organisering

Hver tabell har sin egen mappe med følgende struktur:

```
data/
└── [TABELL-ID]/
    ├── README.md          # Dokumentasjon for tabellen
    ├── config.json        # Konfigurasjon for tabellbehandling
    ├── data.csv           # Kildedata (CSV eller Excel)
    └── output.py          # Generert script (ignoreres av git)
```

## Eksempel: OK-SYS001

```bash
# Legg inn datakildefilen
cp din_datafil.csv data/OK-SYS001/data.csv

# Rediger config.json etter behov
nano data/OK-SYS001/config.json

# Generer script
fin-table-prep data/OK-SYS001/data.csv -o data/OK-SYS001/output.py -c data/OK-SYS001/config.json
```

## Å legge til en ny tabell

1. Opprett en ny mappe under `data/` med tabellens ID som navn
2. Legg til datakildefilen (CSV eller Excel)
3. Opprett en `config.json` med tabellkonfigurasjon
4. Opprett en `README.md` for å dokumentere tabellen
5. Generer scriptet med `fin-table-prep`

## Merknad

Genererte output-filer (`output.py`, `output_*.py`) blir automatisk ignorert av git.
Kun kildedata og konfigurasjonsfiler blir committet til repositoryet.
