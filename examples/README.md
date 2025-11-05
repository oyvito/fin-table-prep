# Eksempler

Dette biblioteket inneholder eksempler på bruk av fin-table-prep.

## Filer

- `sample_data.csv`: Eksempeldata med informasjon om personer
- `config.json`: Eksempelkonfigurasjon for tabellbehandling

## Bruk

Generer et script fra eksempeldataene:

```bash
fin-table-prep examples/sample_data.csv -o output.py
```

Med konfigurasjon:

```bash
fin-table-prep examples/sample_data.csv -o output.py -c examples/config.json
```
