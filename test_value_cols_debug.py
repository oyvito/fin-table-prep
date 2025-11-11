"""
Debug value_cols auto-deteksjon
"""

import pandas as pd

df = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
df_base = df[(df['bosted'] != 301) & (df['kjønn'] != 3)].copy()

print("Kolonner i df_base:")
for col in df_base.columns:
    dtype = df_base[col].dtype
    nunique = df_base[col].nunique()
    print(f"  {col}: {dtype}, {nunique} unike verdier")

# Test auto-deteksjon
aggregeringer = [
    {'kolonne': 'bosted'},
    {'kolonne': 'kjønn'}
]

dim_cols = set()
for agg in aggregeringer:
    dim_cols.add(agg['kolonne'])
    dim_cols.add(f"{agg['kolonne']}.1")

print(f"\nDim_cols: {dim_cols}")

value_cols = [c for c in df_base.columns 
             if df_base[c].dtype in ['int64', 'float64', 'int32', 'float32']
             and c not in dim_cols 
             and not c.endswith('.1')]

print(f"\nAuto-detekterte value_cols: {value_cols}")
