"""
OK-SYS002 Prep Script (Manuelt korrigert)
Basert på domenekunnskap om sysselsettingsdata

VIKTIG DOMENEKUNNSKAP:
- Input 1: Sysselsatte (aargang 2024 = 4. kvartal 2024)
- Input 2: Befolkning (aargang 2025 = per 1.1.2025)
- Merge IKKE på aargang (forskjellige år!)
- Merge på: geografi + aldersgrupper + kjønn
- Beregn: andeler = (sysselsatte / befolkning) * 100
- Output aargang: Bruk sysselsettingsdata sitt år (2024)
"""

import pandas as pd
import sys
import json
import re


def decode_xml_escapes(text):
    """
    Dekode XML numeric character references fra OpenPyXL.
    Eksempel: '_x0031_5_x0020_-_x0020_19_x0020_år' → '15 - 19 år'
    """
    if pd.isna(text):
        return text
    return re.sub(r'_x([0-9a-fA-F]{4})_', lambda m: chr(int(m.group(1), 16)), str(text))


def load_aldersgruppe_mapping():
    """Last mapping for aldersgruppe-aggregering."""
    try:
        with open('../../kodelister/aldgr5_til_aldgr16a.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['mappings']
    except FileNotFoundError:
        print("⚠️  Kodeliste ikke funnet: aldgr5_til_aldgr16a.json")
        # Hardkodet fallback
        return {
            '15 - 19 år': '15-24 år',
            '20 - 24 år': '15-24 år',
            '25 - 29 år': '25-39 år',
            '30 - 34 år': '25-39 år',
            '35 - 39 år': '25-39 år',
            '40 - 44 år': '40-49 år',
            '45 - 49 år': '40-49 år',
            '50 - 54 år': '50-59 år',
            '55 - 59 år': '50-59 år',
            '60 - 64 år': '60-74 år',
            '65 - 69 år': '60-74 år',
            '70 - 74 år': '60-74 år',
            'Alder i alt': 'Alder i alt'
        }


def transform_data(input_file1, input_file2, output_file):
    """
    Transformerer sysselsettingsdata med andelsberegning.
    """
    
    # Last aldersgruppe-mapping
    aldgr_mapping = load_aldersgruppe_mapping()
    
    # Les input fil 1 (sysselsatte)
    print(f"Leser {input_file1}...")
    df_sysselsatte = pd.read_excel(input_file1)
    print(f"  {len(df_sysselsatte)} rader")
    print(f"  Aargang: {df_sysselsatte['aargang'].unique()}")
    
    # Normaliser kolonnenavn til lowercase
    df_sysselsatte.columns = df_sysselsatte.columns.str.lower()
    
    # Dekode XML-escaped verdier
    for col in df_sysselsatte.columns:
        if df_sysselsatte[col].dtype == 'object':
            df_sysselsatte[col] = df_sysselsatte[col].apply(decode_xml_escapes)
    
    # Les input fil 2 (befolkning)
    print(f"Leser {input_file2}...")
    df_befolkning = pd.read_excel(input_file2)
    print(f"  {len(df_befolkning)} rader")
    print(f"  Aargang: {df_befolkning['aargang'].unique()}")
    
    # Normaliser kolonnenavn til lowercase
    df_befolkning.columns = df_befolkning.columns.str.lower()
    
    # Dekode XML-escaped verdier
    for col in df_befolkning.columns:
        if df_befolkning[col].dtype == 'object':
            df_befolkning[col] = df_befolkning[col].apply(decode_xml_escapes)
    
    # Standardiser kolonnenavn for sysselsatte
    df_sysselsatte = df_sysselsatte.rename(columns={
        'bo_bydel': 'geografi',
        'bo_bydel_fmt': 'geografi_navn',
        'aldgr16a_': 'aldersgrupper_kode',
        'aldgr16a__fmt': 'aldersgrupper',
        'kjoenn': 'kjoenn_kode',
        'kjoenn_fmt': 'kjoenn_fmt',
        'antall': 'sysselsatte'
    })
    
    # Standardiser kolonnenavn for befolkning
    df_befolkning = df_befolkning.rename(columns={
        'bydel2': 'geografi',
        'bydel2_fmt': 'geografi_navn',
        'aldgr5': 'aldersgrupper_kode_smal',
        'aldgr5_fmt': 'aldersgrupper_smal',
        'kjoenn': 'kjoenn_kode',
        'kjoenn_fmt': 'kjoenn_fmt',
        'antall': 'befolkning'
    })
    
    # VIKTIG: Aggreger befolkning til bredere aldersgrupper
    print(f"\nAggregerer befolkning fra smale til brede aldersgrupper...")
    print(f"  Smale grupper (eksempel): {df_befolkning['aldersgrupper_smal'].unique()[:3].tolist()}")
    
    # Mapper aldersgrupper
    df_befolkning['aldersgrupper'] = df_befolkning['aldersgrupper_smal'].map(aldgr_mapping)
    
    # Sjekk om det er umappede verdier
    unmapped = df_befolkning[df_befolkning['aldersgrupper'].isna()]['aldersgrupper_smal'].unique()
    if len(unmapped) > 0:
        print(f"⚠️  Umappede aldersgrupper: {unmapped}")
    
    print(f"  Brede grupper (eksempel): {df_befolkning['aldersgrupper'].unique()[:3].tolist()}")
    
    # Aggreger befolkning per brede aldersgrupper
    df_befolkning_agg = df_befolkning.groupby(
        ['geografi', 'aldersgrupper', 'kjoenn_fmt'],
        dropna=False
    ).agg({'befolkning': 'sum'}).reset_index()
    
    print(f"  Befolkning aggregert: {len(df_befolkning)} → {len(df_befolkning_agg)} rader")
    
    # VIKTIG: Merge på GEO + ALDER + KJØNN (IKKE aargang!)
    merge_keys = ['geografi', 'aldersgrupper', 'kjoenn_fmt']
    
    print(f"\nMerger på nøkler: {merge_keys}")
    print("MERK: Aargang er IKKE merge-nøkkel (sysselsatte=2024, befolkning=2025)")
    
    # Merge
    df_merged = pd.merge(
        df_sysselsatte[merge_keys + ['sysselsatte', 'geografi_navn']],
        df_befolkning_agg[merge_keys + ['befolkning']],
        on=merge_keys,
        how='outer',
        indicator=True,
        suffixes=('', '_bef')
    )
    
    # Sjekk merge-kvalitet
    print(f"\nMerge-resultater:")
    print(df_merged['_merge'].value_counts())
    
    # Beregn andeler
    df_merged['andeler'] = (df_merged['sysselsatte'] / df_merged['befolkning'] * 100).round(1)
    
    # Legg til aargang (fra sysselsettingsdata)
    df_merged['aargang'] = 2024
    
    # Fjern _merge kolonne
    df_merged = df_merged.drop(columns=['_merge'], errors='ignore')
    
    # Velg output-kolonner i riktig rekkefølge
    output_columns = [
        'aargang',
        'geografi',
        'geografi_navn',
        'kjoenn_fmt',
        'aldersgrupper',
        'sysselsatte',
        'andeler',
        'befolkning'
    ]
    
    df_final = df_merged[output_columns]
    
    # Sorter
    df_final = df_final.sort_values(['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper'])
    
    # Fjern rader med manglende nøkkelverdier
    df_final = df_final.dropna(subset=['geografi', 'aldersgrupper', 'kjoenn_fmt'])
    
    # Lagre
    print(f"\nLagrer {output_file}...")
    df_final.to_excel(output_file, index=False)
    print(f"✅ Ferdig! {len(df_final)} rader lagret.")
    
    # Vis eksempel
    print("\nFørste 10 rader:")
    print(df_final[['aargang', 'geografi', 'kjoenn_fmt', 'aldersgrupper', 'sysselsatte', 'befolkning', 'andeler']].head(10))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Bruk: python OK-SYS002_prep_v2.py <sysselsatte.xlsx> <befolkning.xlsx> <output.xlsx>")
        sys.exit(1)
    
    input_file1 = sys.argv[1]
    input_file2 = sys.argv[2]
    output_file = sys.argv[3]
    
    transform_data(input_file1, input_file2, output_file)
