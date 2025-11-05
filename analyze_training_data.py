"""
Analyserer treningsdata og genererer innsiktsrapport.
Finner mønstre, kolonnenavn, transformasjoner på tvers av tabeller.
"""

import pandas as pd
import json
from pathlib import Path
from collections import Counter, defaultdict


def analyze_training_data():
    """Analyser alle tabeller i training_data/."""
    
    training_path = Path("training_data")
    if not training_path.exists():
        print("❌ Ingen training_data mappe funnet")
        return
    
    tables = [d for d in training_path.iterdir() if d.is_dir()]
    
    if not tables:
        print("❌ Ingen tabeller funnet i training_data/")
        return
    
    print(f"📊 ANALYSE AV TRENINGSDATA")
    print(f"=" * 70)
    print(f"Antall tabeller: {len(tables)}\n")
    
    # Saml statistikk
    all_input_columns = Counter()
    all_output_columns = Counter()
    column_mappings = defaultdict(Counter)
    table_info = []
    
    for table_dir in sorted(tables):
        table_code = table_dir.name
        print(f"\n### {table_code}")
        print("-" * 70)
        
        # Finn filer
        files = list(table_dir.glob("*.xlsx"))
        input_files = [f for f in files if 'input' in f.name.lower()]
        output_files = [f for f in files if 'output' in f.name.lower()]
        
        print(f"Input-filer: {len(input_files)}")
        print(f"Output-filer: {len(output_files)}")
        
        info = {
            'table_code': table_code,
            'num_inputs': len(input_files),
            'input_columns': [],
            'output_columns': [],
            'num_rows': {'input': [], 'output': 0}
        }
        
        # Analyser input-filer
        for i, input_file in enumerate(sorted(input_files), 1):
            try:
                df = pd.read_excel(input_file)
                cols = df.columns.tolist()
                info['input_columns'].append(cols)
                info['num_rows']['input'].append(len(df))
                
                all_input_columns.update(cols)
                
                print(f"\n  Input {i}: {input_file.name}")
                print(f"    Kolonner ({len(cols)}): {', '.join(cols[:5])}{'...' if len(cols) > 5 else ''}")
                print(f"    Rader: {len(df)}")
            except Exception as e:
                print(f"  ⚠️  Kunne ikke lese {input_file.name}: {e}")
        
        # Analyser output-fil
        if output_files:
            try:
                df_out = pd.read_excel(output_files[0])
                cols_out = df_out.columns.tolist()
                info['output_columns'] = cols_out
                info['num_rows']['output'] = len(df_out)
                
                all_output_columns.update(cols_out)
                
                print(f"\n  Output: {output_files[0].name}")
                print(f"    Kolonner ({len(cols_out)}): {', '.join(cols_out)}")
                print(f"    Rader: {len(df_out)}")
                
                # Forsøk å finne kolonnemappings
                if input_files:
                    df_in = pd.read_excel(input_files[0])
                    for col_in in df_in.columns:
                        for col_out in cols_out:
                            # Enkel likhet-sjekk
                            if col_in.lower().replace('_', '').replace(' ', '') == \
                               col_out.lower().replace('_', '').replace(' ', ''):
                                column_mappings[col_in][col_out] += 1
                            elif col_in.lower() in col_out.lower() or col_out.lower() in col_in.lower():
                                column_mappings[col_in][col_out] += 1
                
            except Exception as e:
                print(f"  ⚠️  Kunne ikke lese output: {e}")
        
        table_info.append(info)
    
    # Oppsummering
    print(f"\n\n" + "=" * 70)
    print(f"📈 OPPSUMMERING PÅ TVERS AV TABELLER")
    print(f"=" * 70)
    
    print(f"\n🔹 MEST BRUKTE INPUT-KOLONNER:")
    for col, count in all_input_columns.most_common(20):
        print(f"  {col:40} {count:2}x")
    
    print(f"\n🔹 MEST BRUKTE OUTPUT-KOLONNER:")
    for col, count in all_output_columns.most_common(20):
        print(f"  {col:40} {count:2}x")
    
    print(f"\n🔹 VANLIGE KOLONNEMAPPINGS:")
    for in_col, out_mappings in sorted(column_mappings.items(), key=lambda x: sum(x[1].values()), reverse=True)[:15]:
        most_common_out = out_mappings.most_common(1)[0]
        print(f"  '{in_col}' → '{most_common_out[0]}' ({most_common_out[1]}x)")
    
    # Finn mønstre
    print(f"\n🔹 MØNSTRE OPPDAGET:")
    
    # XML-encoding
    xml_encoded = [col for col in all_input_columns if '_x00' in col]
    if xml_encoded:
        print(f"  ⚠️  XML-encoded kolonner funnet: {len(xml_encoded)} eksempler")
        print(f"      Eksempler: {xml_encoded[:3]}")
    
    # _fmt kolonner
    fmt_columns = [col for col in all_input_columns if col.endswith('_fmt')]
    if fmt_columns:
        print(f"  📋 _fmt-kolonner: {len(fmt_columns)} stk (formaterte versjoner)")
    
    # Store bokstaver
    uppercase_cols = [col for col in all_input_columns if col.isupper() or any(c.isupper() for c in col)]
    if uppercase_cols:
        print(f"  🔤 Kolonner med store bokstaver: {len(uppercase_cols)} stk")
    
    # Geografiske kolonner
    geo_keywords = ['bydel', 'geografi', 'geo', 'kommune', 'grunnkrets']
    geo_cols_in = [col for col in all_input_columns if any(kw in col.lower() for kw in geo_keywords)]
    geo_cols_out = [col for col in all_output_columns if any(kw in col.lower() for kw in geo_keywords)]
    if geo_cols_in or geo_cols_out:
        print(f"  🗺️  Geografiske kolonner:")
        print(f"      Input: {len(geo_cols_in)} stk → Output: {len(geo_cols_out)} stk")
    
    # Multi-input tabeller
    multi_input = [t for t in table_info if t['num_inputs'] > 1]
    if multi_input:
        print(f"  🔗 Tabeller med flere input-filer: {len(multi_input)} / {len(table_info)}")
        for t in multi_input:
            print(f"      {t['table_code']}: {t['num_inputs']} input-filer")
    
    print(f"\n" + "=" * 70)
    print(f"✅ ANALYSE FERDIG")
    print(f"\n💡 Neste steg:")
    print(f"  - Oppdater kontrollskjema.json med nye mønstre")
    print(f"  - Forbedre generate_prep_script_v2.py basert på innsikter")
    print(f"  - Dokumenter spesielle transformasjoner i metadata.json")
    print(f"=" * 70)


if __name__ == "__main__":
    analyze_training_data()
