"""
Test av aggregering.py modulen
"""

import sys
import io
import pandas as pd
from aggregering import apply_aggregeringer

# UTF-8 encoding setup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Les basis-data
df_output_full = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
df_base = df_output_full[(df_output_full['bosted'] != 301) & 
                         (df_output_full['kjønn'] != 3)].copy()

print(f"Basis-data: {len(df_base)} rader")

# Definer aggregeringer
aggregeringer = [
    {
        'kolonne': 'bosted',
        'type': 'geography_rollup',
        'total_verdi': 301,
        'total_label': '0301 Oslo'
    },
    {
        'kolonne': 'kjønn',
        'type': 'binary_total',
        'total_verdi': 3,
        'total_label': 'Begge kjønn'
    }
]

# Kjør aggregering (lar den auto-detektere value_cols)
df_result = apply_aggregeringer(df_base, aggregeringer)

print(f"Resultat: {len(df_result)} rader")

# Sammenlign med forventet
df_expected = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
print(f"Forventet: {len(df_expected)} rader")

if len(df_result) == len(df_expected):
    print("✅ PERFEKT MATCH!")
else:
    diff = len(df_result) - len(df_expected)
    print(f"❌ Differanse: {diff} rader")

# Vis kombinasjoner
print("\nKombinasjon av bosted × kjønn:")
combo_result = df_result.groupby(['bosted', 'kjønn']).size().reset_index(name='count')
print(combo_result.to_string(index=False))
