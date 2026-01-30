"""
Mal-generering for prep-scripts.

Genererer Python-kode basert på analyse-resultater.
"""

from datetime import datetime


def generate_script_content(
    input_files: list,
    all_mappings: list,
    all_transformations: list,
    all_geographic_suggestions: list,
    aggregation_insights: list,
    output_columns: list,
    table_code: str,
    common_keys_info: dict = None,
    variable_pairs_all: list = None,
    value_columns_all: list = None
) -> str:
    """
    Generer Python-script for multi-input transformasjon.

    Args:
        input_files: Liste av input filstier
        all_mappings: Liste med mapping-info per input
        all_transformations: Liste med kodeliste-transformasjoner per input
        all_geographic_suggestions: Liste med geografiske forslag per input
        aggregation_insights: Liste med aggregeringsinfo
        output_columns: Output kolonne-navn
        table_code: Tabellkode
        common_keys_info: Info om felles nøkler for merge
        variable_pairs_all: Liste av variabel-par per input
        value_columns_all: Liste av statistikkvariabel-info per input
        
    Returns:
        str: Komplett Python-script som streng
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    num_inputs = len(input_files)
    
    # Samle geografiske forslag
    geo_comments = _build_geo_comments(all_geographic_suggestions)
    
    # Samle aggregeringsforslag
    agg_comments = _build_aggregation_comments(aggregation_insights)
    
    # Samle nøkkel-info
    keys_comments = _build_keys_comments(common_keys_info)
    
    # Samle variabel-par info
    pairs_comments = _build_pairs_comments(variable_pairs_all)

    # Bygg script
    script = _build_header(table_code, timestamp, num_inputs, 
                          geo_comments, agg_comments, keys_comments, pairs_comments)
    script += _build_imports()
    script += _build_helper_functions()
    script += _build_transform_function(num_inputs, all_mappings, all_transformations, 
                                        output_columns, table_code, aggregation_insights,
                                        common_keys_info)
    script += _build_main(num_inputs, table_code)
    
    return script


def _build_geo_comments(all_geographic_suggestions: list) -> str:
    """Bygg kommentarblokk for geografiske forslag."""
    lines = []
    for i, geo_sugg in enumerate(all_geographic_suggestions):
        if geo_sugg:
            lines.append(f"\nInput fil {i+1} - Geografiske kolonneforslag:")
            for col, suggestion in geo_sugg.items():
                lines.append(f"  {col}:")
                lines.append(f"    → Kode: {suggestion['code_column']}, Navn: {suggestion['label_column']}")
                for reason in suggestion['reasoning']:
                    lines.append(f"       {reason}")
    return "\n".join(lines) if lines else ""


def _build_aggregation_comments(aggregation_insights: list) -> str:
    """Bygg kommentarblokk for aggregeringer."""
    lines = []
    if aggregation_insights:
        for insight in aggregation_insights:
            aggregations = insight.get('aggregations', [])
            if aggregations:
                lines.append("\nOppdagede AGGREGERINGS-operasjoner:")
                for agg in aggregations:
                    desc = agg.get('description', 'Ukjent aggregering')
                    col_in = agg.get('input_column', '?')
                    col_out = agg.get('column', '?')
                    new_vals = agg.get('new_values', [])
                    agg_type = agg.get('type', 'other')
                    
                    lines.append(f"  - {desc}")
                    lines.append(f"    Kolonne: {col_in} → {col_out}")
                    lines.append(f"    Nye verdier: {new_vals}")
                    lines.append(f"    Type: {agg_type}")
    return "\n".join(lines) if lines else ""


def _build_keys_comments(common_keys_info: dict) -> str:
    """Bygg kommentarblokk for felles nøkler."""
    if not common_keys_info:
        return ""
    
    ck = common_keys_info.get('candidate_keys', [])
    uq = common_keys_info.get('composite_uniqueness', 0.0)
    key_quality = common_keys_info.get('key_quality', {})
    
    if ck:
        quality_lines = [f"    - {k}: uniqueness={key_quality.get(k,0):.3f}" for k in ck]
        return (
            "\nMULTI-INPUT NØKLER:\n" +
            f"  Felles nøkkelkolonner: {ck}\n" +
            f"  Kompositt unikhet: {uq:.3f}\n" +
            "  Kolonnekvalitet:\n" +
            "\n".join(quality_lines)
        )
    return "\nMULTI-INPUT NØKLER:\n  Ingen felles kolonner identifisert."


def _build_pairs_comments(variable_pairs_all: list) -> str:
    """Bygg kommentarblokk for variabel-par."""
    if not variable_pairs_all:
        return ""
    
    lines = []
    for i, pairs in enumerate(variable_pairs_all, 1):
        if not pairs:
            lines.append(f"  Input {i}: Ingen variabel-par funnet")
        else:
            lines.append(f"  Input {i}:")
            for p in pairs:
                lines.append(f"    - base={p['base']} label={p['label']} pattern={p['pattern']}")
    return "\nVARIABEL-PAR (kode+tekst):\n" + "\n".join(lines)


def _build_header(table_code: str, timestamp: str, num_inputs: int,
                 geo_comments: str, agg_comments: str, 
                 keys_comments: str, pairs_comments: str) -> str:
    """Bygg script header med dokumentasjon."""
    return f'''"""
Prep-script for {table_code}
Generert: {timestamp}
Antall input-filer: {num_inputs}

Dette scriptet tar {num_inputs} input-fil(er) og transformerer til output-format.
{geo_comments}
{agg_comments}
{keys_comments}
{pairs_comments}
"""

'''


def _build_imports() -> str:
    """Bygg import-seksjonen."""
    return '''import pandas as pd
import sys
import io
from pathlib import Path

# Sikre UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


'''


def _build_helper_functions() -> str:
    """Bygg hjelpefunksjoner."""
    return '''def normalize_column_names(df):
    """Normaliser kolonnenavn til lowercase."""
    df.columns = df.columns.str.lower()
    return df


def decode_xml_strings(df):
    """Dekoder XML-encoded strings i Excel-filer."""
    import re
    
    def decode_string(val):
        if not isinstance(val, str):
            return val
        decoded = re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), val)
        decoded = ' '.join(decoded.split())
        decoded = decoded.replace(' -', '-')
        return decoded
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(decode_string)
    
    return df


def load_codelists():
    """Last inn relevante kodelister."""
    import json
    codelists = {}
    
    codelist_dir = Path(__file__).parent / 'kodelister'
    if not codelist_dir.exists():
        codelist_dir = Path('kodelister')
    
    if codelist_dir.exists():
        for json_file in codelist_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    codelists[data.get('name', json_file.stem)] = data
            except Exception as e:
                print(f"Kunne ikke laste {json_file}: {e}")
    
    return codelists


'''


def _build_transform_function(num_inputs: int, all_mappings: list,
                              all_transformations: list, output_columns: list,
                              table_code: str, aggregation_insights: list,
                              common_keys_info: dict) -> str:
    """Bygg hovedtransformasjonsfunksjonen."""
    
    # Argumenter
    args = ', '.join([f'input_file{i+1}' for i in range(num_inputs)])
    
    script = f'''def transform_data({args}, output_file):
    """Hovedtransformasjon."""
    
    codelists = load_codelists()
    
'''
    
    # Les input-filer
    for i in range(num_inputs):
        script += f'''    # Les input fil {i+1}
    print(f"Leser {{input_file{i+1}}}...")
    df{i+1} = pd.read_excel(input_file{i+1})
    df{i+1} = normalize_column_names(df{i+1})
    df{i+1} = decode_xml_strings(df{i+1})
    print(f"  {{len(df{i+1})}} rader, {{len(df{i+1}.columns)}} kolonner")
    
'''
    
    # Transformasjoner
    for i, mapping_info in enumerate(all_mappings, 1):
        script += f'''    # Input {i}: Kopier data
    df{i}_transformed = df{i}.copy()
    
'''
    
    # Multi-input merge
    if num_inputs > 1:
        common_keys = common_keys_info.get('candidate_keys', []) if common_keys_info else []
        script += f'''    # MULTI-INPUT: Merge på felles nøkler
    # Foreslåtte nøkler: {common_keys}
    df_merged = df1_transformed.copy()
'''
        for i in range(2, num_inputs + 1):
            script += f'''    # TODO: Tilpass merge-logikk
    # df_merged = df_merged.merge(df{i}_transformed, on={common_keys}, how='outer')
'''
        script += '''    df_final_candidate = df_merged
    
'''
    else:
        script += '''    df_final_candidate = df1_transformed
    
'''
    
    # Aggregeringer
    if aggregation_insights and aggregation_insights[0].get('aggregations'):
        script += '''    # AGGREGERINGER
    from aggregering import apply_aggregeringer
    
    aggregeringer = [
'''
        for agg in aggregation_insights[0]['aggregations']:
            col = agg.get('input_column', agg['column']).lower()
            new_vals = agg['new_values']
            label = 'Total'
            if 'kjønn' in col or 'kjonn' in col:
                label = 'Begge kjønn'
            elif new_vals[0] in ['301', '0301']:
                label = '0301 Oslo'
            
            val = f"'{new_vals[0]}'" if isinstance(new_vals[0], str) else new_vals[0]
            script += f'''        {{'kolonne': '{col}', 'total_verdi': {val}, 'total_label': '{label}'}},
'''
        script += '''    ]
    
    df_final = apply_aggregeringer(df_final_candidate, aggregeringer)
    
'''
    else:
        script += '''    df_final = df_final_candidate
    
'''
    
    # Rename og output
    script += f'''    # Rename kolonner
    rename_dict = {{
'''
    for mapping_info in all_mappings:
        for orig, output in mapping_info['mappings'].items():
            script += f'''        '{orig.lower()}': '{output}',
'''
    script += '''    }
    df_final = df_final.rename(columns=rename_dict)
    
'''
    
    script += f'''    # Velg output-kolonner
    output_columns = {output_columns}
    available_cols = [col for col in output_columns if col in df_final.columns]
    df_final = df_final[available_cols]
    
    # Lagre
    print(f"Lagrer {{output_file}}...")
    df_final.to_excel(output_file, index=False)
    print(f"✅ Ferdig! {{len(df_final)}} rader lagret.")


'''
    
    return script


def _build_main(num_inputs: int, table_code: str) -> str:
    """Bygg main-seksjonen."""
    args_usage = ' '.join([f'<input{i+1}.xlsx>' for i in range(num_inputs)])
    args_check = num_inputs + 2
    
    script = f'''if __name__ == "__main__":
    if len(sys.argv) < {args_check}:
        print("Bruk: python {table_code}_prep.py {args_usage} <output.xlsx>")
        sys.exit(1)
    
'''
    
    for i in range(1, num_inputs + 1):
        script += f'''    input_file{i} = sys.argv[{i}]
'''
    
    script += f'''    output_file = sys.argv[{num_inputs + 1}]
    
    transform_data('''
    
    for i in range(1, num_inputs + 1):
        script += f'input_file{i}, '
    
    script += '''output_file)
'''
    
    return script
