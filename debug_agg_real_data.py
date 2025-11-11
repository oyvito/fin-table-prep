"""
Debug aggregering på faktiske data
"""

import pandas as pd
from aggregering import apply_aggregeringer

# Les og transformer som i prep-scriptet
df1 = pd.read_excel('training_data/OK-BEF001/ok-bef001_input.xlsx')
df1.columns = df1.columns.str.lower()

df1_transformed = df1.rename(columns={
    'aargang': 'år',
    'alderu': 'alder',
    'bydel2': 'bosted',
    'kjoenn': 'kjønn',
    'antall': 'antall',
    'alderu_fmt': 'alder.1',
    'bydel2_fmt': 'bosted.1',
    'kjoenn_fmt': 'kjønn.1',
})

print(f"Før aggregering: {len(df1_transformed)} rader")
print(f"  bosted: {sorted(df1_transformed['bosted'].unique())}")
print(f"  kjønn: {sorted(df1_transformed['kjønn'].unique())}")

aggregeringer = [
    {'kolonne': 'bosted', 'type': 'geography_rollup', 'total_verdi': 301, 'total_label': '0301 Oslo'},
    {'kolonne': 'kjønn', 'type': 'binary_total', 'total_verdi': 3, 'total_label': 'Begge kjønn'},
]

print("\n=== DEBUG: Auto-detektering av value_cols ===")
# Simuler auto-deteksjon
from aggregering import apply_aggregeringer
# Sett value_cols eksplisitt for å teste
df_result_explicit = apply_aggregeringer(df1_transformed, aggregeringer, value_cols=['antall'])
print(f"Med eksplisitt value_cols=['antall']: {len(df_result_explicit)} rader")

df_result = apply_aggregeringer(df1_transformed, aggregeringer)

print(f"\nEtter aggregering: {len(df_result)} rader")
print(f"  bosted: {sorted(df_result['bosted'].unique())}")
print(f"  kjønn: {sorted(df_result['kjønn'].unique())}")

# Sjekk kombinasjoner
combos = df_result.groupby(['bosted', 'kjønn']).size().reset_index(name='count')
print(f"\nKombinasjoner:")
print(combos.to_string(index=False))

# Sammenlign med forventet
expected = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
print(f"\nForventet: {len(expected)} rader")
print(f"Differanse: {len(df_result) - len(expected)} rader")
