# OK-SYS001

Denne mappen inneholder data og konfigurasjon for OK-SYS001 tabellen.

## Filstruktur

- `data.csv` eller `data.xlsx`: Kildedata for tabellen
- `config.json`: Konfigurasjon for tabellbehandling
- `output.py`: Generert script (ikke commit dette til git)

## Bruk

Generer script for denne tabellen:

```bash
fin-table-prep data/OK-SYS001/data.csv -o data/OK-SYS001/output.py -c data/OK-SYS001/config.json
```
