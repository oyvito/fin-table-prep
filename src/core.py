"""
Kjernefunksjonalitet for fin-stat-prep.

Hovedlogikk for analyse og script-generering.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sys

# Legg til parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from codelist_manager import CodelistManager
from .analysis import (
    detect_variable_pairs,
    detect_value_columns,
    detect_aggregation_patterns_v2,
    find_column_mapping_with_codelists
)
from .generation import generate_script_content


def load_kontrollskjema(path: str = "kontrollskjema.json") -> dict:
    """Last inn kontrollskjema for standardisering."""
    kontrollskjema_path = Path(path)
    if kontrollskjema_path.exists():
        with open(kontrollskjema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def simulate_merge(input_dfs: list) -> pd.DataFrame:
    """
    Simuler merge av multiple input DataFrames.
    
    Strategi:
    1. Finn felles kolonner (potensielle merge-nøkler)
    2. Hvis felles kolonner: outer join
    3. Hvis ingen felles: concat (union)
    """
    if len(input_dfs) == 1:
        return input_dfs[0].copy()
    
    # Normaliser kolonnenavn
    normalized_dfs = []
    for df in input_dfs:
        df_norm = df.copy()
        df_norm.columns = df_norm.columns.str.lower()
        normalized_dfs.append(df_norm)
    
    # Finn felles kolonner
    common_cols = set(normalized_dfs[0].columns)
    for df in normalized_dfs[1:]:
        common_cols &= set(df.columns)
    
    common_cols = list(common_cols)
    
    if common_cols:
        print(f"  Simulerer MERGE på felles kolonner: {common_cols}")
        df_merged = normalized_dfs[0]
        for df in normalized_dfs[1:]:
            df_merged = df_merged.merge(df, on=common_cols, how='outer', suffixes=('', '_dup'))
        df_merged = df_merged[[col for col in df_merged.columns if not col.endswith('_dup')]]
    else:
        print(f"  Simulerer UNION (ingen felles kolonner)")
        df_merged = pd.concat(normalized_dfs, ignore_index=True, sort=False)
    
    return df_merged


def identify_common_keys(input_dfs: list, all_mappings: list = None) -> dict:
    """Identifiser felles nøkkelkolonner på tvers av flere input-dataframes."""
    if not input_dfs:
        return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0}

    # Hvis ingen mappings, fall tilbake til original logikk
    if not all_mappings:
        lower_sets = [set(c.lower() for c in df.columns) for df in input_dfs]
        common_lower = set.intersection(*lower_sets)
        if not common_lower:
            return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0}
        
        first_cols_map = {c.lower(): c for c in input_dfs[0].columns}
        common_cols = [first_cols_map[l] for l in common_lower]
    else:
        # Bruk standardnavnene fra mappings
        standardized_cols = []
        for i, (df, mapping_info) in enumerate(zip(input_dfs, all_mappings)):
            mapping = mapping_info.get('mappings', {})
            std_cols = [mapping.get(col, col) for col in df.columns]
            standardized_cols.append(set(c.lower() for c in std_cols))
        
        common_lower = set.intersection(*standardized_cols)
        if not common_lower:
            return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0}
        
        first_mapping = all_mappings[0].get('mappings', {})
        std_cols_map = {std.lower(): std for std in first_mapping.values()}
        first_cols_map = {c.lower(): c for c in input_dfs[0].columns}
        common_cols = [std_cols_map.get(l, first_cols_map.get(l, l)) for l in common_lower]

    # Filtrer ut åpenbare målekolonner
    measure_candidates = {'antall', 'value', 'count', 'beløp', 'sum'}
    filtered = [c for c in common_cols if c.lower() not in measure_candidates]

    # Vurder uniqueness
    key_quality = {}
    df0 = input_dfs[0]
    
    for col in filtered:
        if col in df0.columns:
            nunique = df0[col].nunique(dropna=True)
            ratio = nunique / max(len(df0), 1)
            key_quality[col] = ratio
        else:
            key_quality[col] = 0.0

    candidate = [c for c in filtered if key_quality.get(c, 0) > 0.2] or filtered

    # Test composite uniqueness
    composite_uniqueness = 0.0
    valid_cols = [c for c in candidate if c in df0.columns]
    if valid_cols:
        subset = df0[valid_cols]
        composite_uniqueness = subset.drop_duplicates().shape[0] / max(len(df0), 1)

    return {
        'candidate_keys': candidate,
        'key_quality': key_quality,
        'composite_uniqueness': composite_uniqueness
    }


def generate_prep_script(
    input_files: list,
    output_file: str,
    table_code: str,
    input_sheets: list = None,
    output_sheet: str = None
):
    """
    Generer prep-script som håndterer flere input-filer.
    
    Args:
        input_files: List av input Excel-filer
        output_file: Output Excel-fil (referanse)
        table_code: Tabellkode (f.eks. OK-SYS001)
        input_sheets: List av sheet-navn for hver input-fil
        output_sheet: Output sheet-navn
    """
    
    # Last kodelister og kontrollskjema
    codelist_mgr = CodelistManager()
    kontrollskjema = load_kontrollskjema()
    
    # STEG 1: Les input-filer
    print("=== STEG 1: Les input-filer ===")
    input_dfs = []
    for i, input_file in enumerate(input_files):
        sheet = input_sheets[i] if input_sheets and i < len(input_sheets) else 0
        df = pd.read_excel(input_file, sheet_name=sheet)
        df.columns = df.columns.str.lower().str.strip()
        
        # XML-dekoding
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.replace(' -', '-').str.replace('  ', ' ').str.strip()
        
        input_dfs.append(df)
        print(f"Input {i+1}: {input_file}")
        print(f"  Kolonner: {df.columns.tolist()}")
        print(f"  Rader: {len(df)}\n")
    
    # Les output
    df_output = pd.read_excel(output_file, sheet_name=output_sheet or 0)
    print(f"Output: {output_file}")
    print(f"  Kolonner: {df_output.columns.tolist()}")
    print(f"  Rader: {len(df_output)}\n")
    
    # STEG 2: Merge hvis multi-input
    print("=== STEG 2: MERGE ===")
    is_multi_input = len(input_dfs) > 1
    if is_multi_input:
        analysis_df = simulate_merge(input_dfs)
        print(f"✅ Merged {len(input_dfs)} inputs → {len(analysis_df)} rader\n")
    else:
        analysis_df = input_dfs[0].copy()
        print(f"Single-input\n")
    
    # STEG 3: Variabel-par deteksjon
    print("=== STEG 3: Variabel-par ===")
    variable_pairs_all = []
    value_columns_all = []
    
    pairs = detect_variable_pairs(analysis_df)
    value_info = detect_value_columns(analysis_df, pairs)
    
    for _ in input_dfs:
        variable_pairs_all.append(pairs)
        value_columns_all.append(value_info)
    
    if pairs:
        for p in pairs:
            print(f"  - {p['base']} / {p['label']} ({p['pattern']})")
    else:
        print("  Ingen funnet")
    print()
    
    # STEG 4: Kolonnemapping
    print("=== STEG 4: Kolonnemapping ===")
    all_mappings = []
    all_transformations = []
    all_geographic_suggestions = []
    
    result = find_column_mapping_with_codelists(
        analysis_df, df_output, codelist_mgr, kontrollskjema, table_code,
        known_pairs=pairs
    )
    
    for _ in input_dfs:
        all_mappings.append({
            'mappings': result['mappings'],
            'unmapped_input': result['unmapped_input'],
            'unmapped_output': result['unmapped_output']
        })
        all_transformations.append(result['value_transformations'])
        all_geographic_suggestions.append(result['geographic_suggestions'])
    
    print(f"Mappings: {len(result['mappings'])}")
    print(f"Kodeliste-transformasjoner: {len(result['value_transformations'])}")
    print(f"Umappede: {result['unmapped_input']}\n")
    
    # STEG 5: Nøkkelanalyse
    print("=== STEG 5: Nøkkelanalyse ===")
    if is_multi_input:
        common_keys_info = identify_common_keys(input_dfs, all_mappings)
        print(f"Felles nøkler: {common_keys_info['candidate_keys']}\n")
    else:
        common_keys_info = None
        print("Single-input\n")
    
    # STEG 6: Aggregeringsanalyse
    print("=== STEG 6: Aggregering ===")
    aggregation_insights = []
    try:
        agg_result = detect_aggregation_patterns_v2(
            analysis_df, df_output, all_mappings[0]['mappings']
        )
        aggregation_insights.append(agg_result)
        
        if agg_result['aggregations']:
            for agg in agg_result['aggregations']:
                print(f"  - {agg['description']}")
        else:
            print("  Ingen detektert")
    except Exception as e:
        print(f"  Feil: {e}")
        aggregation_insights.append({'aggregations': []})
    print()
    
    # Generer script
    script_name = f"{table_code}_prep.py"
    
    script_content = generate_script_content(
        input_files, all_mappings, all_transformations, all_geographic_suggestions,
        aggregation_insights, df_output.columns.tolist(), table_code,
        common_keys_info, variable_pairs_all, value_columns_all
    )
    
    with open(script_name, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Generert: {script_name}")
    print(f"\n💡 Neste steg:")
    print(f"1. Gjennomgå scriptet og juster TODO-seksjoner")
    print(f"2. Test: python {script_name} <input_files> <output.xlsx>")
