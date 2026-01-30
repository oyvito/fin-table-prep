# fin-table-prep
Applikasjon for å generere python-script til statistikktabeller.

## Installasjon

```bash
pip install -e .
```

For utvikling:
```bash
pip install -e ".[dev]"
```

## Organisering av tabeller

Tabeller organiseres i `data/` mappen, med en undermappe for hver tabell:

```
data/
└── [TABELL-ID]/
    ├── README.md          # Dokumentasjon
    ├── config.json        # Konfigurasjon
    ├── data.csv           # Kildedata
    └── output.py          # Generert script (ignoreres av git)
```

Se [data/README.md](data/README.md) for mer informasjon.

## Bruk

### Kommandolinje

```bash
fin-table-prep input_data.csv -o output_script.py
```

Med konfigurasjonsfil:
```bash
fin-table-prep input_data.csv -o output_script.py -c config.json
```

### Python API

```python
from fin_table_prep.table_prep import TablePrep

prep = TablePrep()
data = prep.load_data('data.csv')
config = {'columns': ['col1', 'col2']}
prepared = prep.prepare_table(data, config)
script = prep.generate_script(config, 'output.py')
```

## Utvikling

### Kjøre tester

```bash
pytest
```

Med coverage:
```bash
pytest --cov=fin_table_prep
```

### Formatering

```bash
black src/ tests/
```

### Linting

```bash
flake8 src/ tests/
```
