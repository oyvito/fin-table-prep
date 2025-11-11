"""
Test forbedret detect_value_columns
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from generate_prep_script_v2 import detect_value_columns, detect_variable_pairs

# Les test-data
df = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
df_base = df[(df['bosted'] != 301) & (df['kjønn'] != 3)].copy()

print("=== TEST: OK-BEF001 output (basis) ===")
print(f"Antall rader: {len(df_base)}\n")

# Detekter variabel-par først
pairs = detect_variable_pairs(df_base)
print("Variabel-par:")
for p in pairs:
    print(f"  {p['base']} / {p['label']}")
print()

# Detekter value columns
result = detect_value_columns(df_base, pairs)

print("STATISTIKKVARIABLE (skal summeres):")
for col in result['value_columns']:
    nunique = df_base[col].nunique()
    print(f"  ✓ {col} ({nunique} unike verdier)")

print("\nDIMENSJONSVARIABLE (kategoriske):")
for col in result['dimension_columns']:
    nunique = df_base[col].nunique()
    print(f"  • {col} ({nunique} unike verdier)")

print("\nLABEL-KOLONNER:")
for col in result['label_columns']:
    print(f"  → {col}")

# Validering
expected_value_cols = ['antall']
detected_value_cols = result['value_columns']

print("\n" + "="*60)
if detected_value_cols == expected_value_cols:
    print("✅ PERFEKT! Detekterte riktige value_columns")
else:
    print(f"❌ Forventet: {expected_value_cols}")
    print(f"   Detektert: {detected_value_cols}")
