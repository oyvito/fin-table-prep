"""
Debug: Sjekk merge av sysselsatte + befolkning for OK-SYS002
"""

import pandas as pd
import re


def decode_xml_strings(df):
    """Dekoder XML-encoded strings."""
    def decode_string(val):
        if not isinstance(val, str):
            return val
        return re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), val)
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(decode_string)
    return df


# Les inputs
print("=== LASTER DATA ===")
df_sys = pd.read_excel('training_data/OK-SYS002/OK-SYS002_input_1.xlsx')
df_bef = pd.read_excel('training_data/OK-SYS002/OK-SYS002_input_2.xlsx')
df_output = pd.read_excel('training_data/OK-SYS002/OK-SYS002_output.xlsx')

# Normaliser
df_sys.columns = df_sys.columns.str.lower()
df_bef.columns = df_bef.columns.str.lower()

# Dekod XML
df_sys = decode_xml_strings(df_sys)
df_bef = decode_xml_strings(df_bef)

print(f"Sysselsatte: {len(df_sys)} rader")
print(f"Befolkning: {len(df_bef)} rader")
print(f"Forventet output: {len(df_output)} rader")

# Sjekk dimensjoner
print("\n=== SYSSELSATTE DIMENSJONER ===")
print(f"År: {sorted(df_sys['aargang'].unique())}")
print(f"Bydeler: {df_sys['b_delbydel2017_01'].nunique()} unike")
print(f"Kjønn: {sorted(df_sys['kjoenn_fmt'].unique())}")
print(f"Aldersgrupper: {sorted(df_sys['aldgr16a__fmt'].unique())}")

print("\n=== BEFOLKNING DIMENSJONER ===")
print(f"År: {sorted(df_bef['aargang'].unique())}")
print(f"Bydeler: {df_bef['delbydel2017_01'].nunique()} unike")
print(f"Kjønn: {sorted(df_bef['kjoenn_fmt'].unique())}")
print(f"Aldersgrupper: {sorted(df_bef['aldgr5_fmt'].unique())}")

# Sjekk OUTPUT dimensjoner
print("\n=== OUTPUT DIMENSJONER ===")
print(f"År: {sorted(df_output['aargang'].unique())}")
print(f"Geografi: {df_output['geografi'].nunique()} unike")
print(f"Kjønn: {sorted(df_output['kjoenn_fmt'].unique())}")
print(f"Aldersgrupper: {sorted(df_output['aldersgrupper'].unique())}")

# Beregn forventet antall rader
print("\n=== FORVENTET ANTALL RADER ===")
n_aar = df_output['aargang'].nunique()
n_geo = df_output['geografi'].nunique()
n_kjonn = df_output['kjoenn_fmt'].nunique()
n_alder = df_output['aldersgrupper'].nunique()

print(f"År: {n_aar}")
print(f"Geografi: {n_geo}")
print(f"Kjønn: {n_kjonn}")
print(f"Aldersgrupper: {n_alder}")
print(f"Teoretisk max: {n_aar} × {n_geo} × {n_kjonn} × {n_alder} = {n_aar * n_geo * n_kjonn * n_alder}")
print(f"Faktisk output: {len(df_output)}")

# Sjekk om alle kombinasjoner finnes
print("\n=== MERGE-SJEKK ===")
merge_cols = ['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper']

# Test merge-logikken
# Først: simuler transformasjonen
df_sys_test = df_sys.copy()
df_sys_test['aargang'] = pd.to_numeric(df_sys_test['aargang'], errors='coerce').astype('Int64')
df_sys_test['aldersgrupper'] = df_sys_test['aldgr16a__fmt']
df_sys_test = df_sys_test.rename(columns={
    'b_delbydel2017_01': 'geografi',
    'antall': 'sysselsatte'
})

df_bef_test = df_bef.copy()
df_bef_test['aargang'] = pd.to_numeric(df_bef_test['aargang'], errors='coerce').astype('Int64')
df_bef_test['aargang'] = df_bef_test['aargang'] - 1  # Juster år

# Mapper aldersgrupper
import json
with open('kodelister/aldgr5_til_aldgr16a.json', 'r', encoding='utf-8') as f:
    codelist = json.load(f)
    mappings = codelist['mappings']

df_bef_test['aldersgrupper'] = df_bef_test['aldgr5_fmt'].map(mappings)

# Aggreger befolkning
df_bef_agg = df_bef_test.groupby(
    ['aargang', 'delbydel2017_01', 'kjoenn_fmt', 'aldersgrupper'],
    dropna=False
).agg({'antall': 'sum'}).reset_index()

df_bef_agg = df_bef_agg.rename(columns={
    'delbydel2017_01': 'geografi',
    'antall': 'befolkning'
})

print(f"Sysselsatte transformert: {len(df_sys_test)} rader")
print(f"Befolkning aggregert: {len(df_bef_agg)} rader")

# Test merge
df_merged = df_sys_test[['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper', 'sysselsatte']].merge(
    df_bef_agg[['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper', 'befolkning']],
    on=['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper'],
    how='outer'
)

print(f"\nMerge resultat: {len(df_merged)} rader")
print(f"Sysselsatte NaN: {df_merged['sysselsatte'].isna().sum()}")
print(f"Befolkning NaN: {df_merged['befolkning'].isna().sum()}")

# Sjekk om vi har data for begge
df_complete = df_merged[df_merged['sysselsatte'].notna() & df_merged['befolkning'].notna()]
print(f"Komplette rader (begge verdier): {len(df_complete)}")

print("\n=== KONKLUSJON ===")
if len(df_merged) == len(df_sys_test):
    print("✅ OUTER JOIN gir samme antall som sysselsatte")
    print("   → Alle befolkningsrader matcher eksisterende sysselsatte-rader")
else:
    print(f"⚠️  OUTER JOIN gir {len(df_merged) - len(df_sys_test)} flere rader")
    print("   → Noen befolkningsrader har ikke sysselsatte-match")
    
    # Finn rader som kun er i befolkning
    df_only_bef = df_merged[df_merged['sysselsatte'].isna()]
    print(f"\nRader kun i befolkning: {len(df_only_bef)}")
    if len(df_only_bef) > 0:
        print("Eksempel på manglende kombinasjoner:")
        print(df_only_bef[['geografi', 'kjoenn_fmt', 'aldersgrupper']].head(10))
