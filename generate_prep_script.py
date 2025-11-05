"""
Genererer Python-script for datatransformasjon basert på analyse av input/output-filer.
Lager tabellkode_prep.py med validering.
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import argparse
import sys
from pathlib import Path
from datetime import datetime


def similarity(a, b):
    """Beregn likhet mellom to strenger (0-1)."""
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def find_column_mapping(df_input, df_output, similarity_threshold=0.6):
    """Finn kolonnemappings mellom input og output."""
    input_cols = df_input.columns.tolist()
    output_cols = df_output.columns.tolist()
    
    mappings = {}
    used_output_cols = set()
    
    # Eksakte match først
    for in_col in input_cols:
        in_col_clean = in_col.lower().strip().replace(' ', '').replace('_', '')
        for out_col in output_cols:
            out_col_clean = out_col.lower().strip().replace(' ', '').replace('_', '')
            if in_col_clean == out_col_clean and out_col not in used_output_cols:
                mappings[in_col] = out_col
                used_output_cols.add(out_col)
                break
    
    # Likhet i kolonnenavn
    for in_col in input_cols:
        if in_col in mappings:
            continue
        best_match = None
        best_score = similarity_threshold
        for out_col in output_cols:
            if out_col in used_output_cols:
                continue
            score = similarity(in_col, out_col)
            if score > best_score:
                best_score = score
                best_match = out_col
        if best_match:
            mappings[in_col] = best_match
            used_output_cols.add(best_match)
    
    # Datainnhold-basert mapping for gjenvaerende
    for in_col in input_cols:
        if in_col in mappings:
            continue
        
        in_dtype = df_input[in_col].dtype
        in_unique = df_input[in_col].nunique()
        
        for out_col in output_cols:
            if out_col in used_output_cols:
                continue
            
            out_dtype = df_output[out_col].dtype
            out_unique = df_output[out_col].nunique()
            
            # Sammenlign unike verdier
            if in_unique > 0 and out_unique > 0:
                unique_ratio = min(in_unique, out_unique) / max(in_unique, out_unique)
                
                # Sjekk overlap i verdier
                in_vals = set(df_input[in_col].dropna().astype(str).unique()[:20])
                out_vals = set(df_output[out_col].dropna().astype(str).unique()[:20])
                
                if in_vals and out_vals:
                    overlap = len(in_vals & out_vals) / max(len(in_vals), len(out_vals))
                    
                    # Hvis god match på innhold
                    if overlap > 0.3 or unique_ratio > 0.8:
                        mappings[in_col] = out_col
                        used_output_cols.add(out_col)
                        break
    
    unmapped_input = [col for col in input_cols if col not in mappings]
    unmapped_output = [col for col in output_cols if col not in used_output_cols]
    
    return mappings, unmapped_input, unmapped_output


def analyze_value_mapping(df_input, in_col, df_output, out_col, max_unique=50):
    """Analyser verdimappings mellom kolonner."""
    in_values = df_input[in_col].dropna().unique()
    out_values = df_output[out_col].dropna().unique()
    
    if len(in_values) > max_unique or len(out_values) > max_unique:
        return None, "for_mange_unike_verdier"
    
    value_mappings = {}
    used_output_values = set()
    
    # Eksakte match
    for in_val in in_values:
        if in_val in out_values:
            value_mappings[in_val] = in_val
            used_output_values.add(in_val)
    
    # String-likhet
    for in_val in in_values:
        if in_val in value_mappings:
            continue
        in_val_str = str(in_val)
        best_match = None
        best_score = 0.7
        for out_val in out_values:
            if out_val in used_output_values:
                continue
            out_val_str = str(out_val)
            score = similarity(in_val_str, out_val_str)
            len_ratio = min(len(in_val_str), len(out_val_str)) / max(len(in_val_str), len(out_val_str))
            adjusted_score = score * len_ratio
            if adjusted_score > best_score:
                best_score = adjusted_score
                best_match = out_val
        if best_match:
            value_mappings[in_val] = best_match
            used_output_values.add(best_match)
    
    mapped_ratio = len(value_mappings) / len(in_values) if len(in_values) > 0 else 0
    
    if mapped_ratio > 0.7:
        return value_mappings, "mapping_funnet"
    else:
        return None, "ingen_klar_mapping"


def generate_prep_script(table_code, input_file, output_file, 
                         col_mapping, unmapped_input, unmapped_output,
                         df_input, df_output, input_sheet, output_sheet):
    """
    Generer komplett _prep.py script med validering.
    """
    
    script_name = f"{table_code}_prep.py"
    
    lines = []
    lines.append('"""')
    lines.append(f'Dataprep script for {table_code}')
    lines.append(f'Auto-generert: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('"""')
    lines.append('')
    lines.append('import pandas as pd')
    lines.append('import sys')
    lines.append('from pathlib import Path')
    lines.append('')
    lines.append('')
    lines.append('def validate_input(df):')
    lines.append('    """Valider input-data."""')
    lines.append('    required_cols = [')
    for col in df_input.columns:
        lines.append(f'        "{col}",')
    lines.append('    ]')
    lines.append('    ')
    lines.append('    missing = set(required_cols) - set(df.columns)')
    lines.append('    if missing:')
    lines.append(f'        raise ValueError(f"Mangler kolonner i input: {{missing}}")')
    lines.append('    ')
    lines.append(f'    print(f"[OK] Input validert: {{len(df)}} rader, {{len(df.columns)}} kolonner")')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('def validate_output(df):')
    lines.append('    """Valider output-data."""')
    lines.append('    required_cols = [')
    for col in df_output.columns:
        lines.append(f'        "{col}",')
    lines.append('    ]')
    lines.append('    ')
    lines.append('    missing = set(required_cols) - set(df.columns)')
    lines.append('    if missing:')
    lines.append(f'        raise ValueError(f"Mangler kolonner i output: {{missing}}")')
    lines.append('    ')
    lines.append('    # Sjekk for None-verdier i kritiske kolonner')
    lines.append('    for col in required_cols:')
    lines.append('        null_count = df[col].isna().sum()')
    lines.append('        if null_count > 0:')
    lines.append(f'            print(f"[!] Advarsel: {{col}} har {{null_count}} manglende verdier")')
    lines.append('    ')
    lines.append(f'    print(f"[OK] Output validert: {{len(df)}} rader, {{len(df.columns)}} kolonner")')
    lines.append('    return True')
    lines.append('')
    lines.append('')
    lines.append('def transform_data(df):')
    lines.append('    """Utfoer datatransformasjon."""')
    lines.append('    ')
    lines.append('    # Steg 1: Endre kolonnenavn')
    
    rename_map = {k: v for k, v in col_mapping.items() if k != v}
    if rename_map:
        lines.append('    column_mapping = {')
        for in_col, out_col in sorted(rename_map.items()):
            lines.append(f'        "{in_col}": "{out_col}",')
        lines.append('    }')
        lines.append('    df = df.rename(columns=column_mapping)')
        lines.append(f'    print(f"[OK] Endret {{len(column_mapping)}} kolonnenavn")')
    else:
        lines.append('    # Ingen kolonnenavn-endringer noedvendig')
    
    lines.append('    ')
    lines.append('    # Steg 2: Transformere kategoriverdier')
    
    # Analyser verdimappings
    has_value_mappings = False
    for in_col, out_col in col_mapping.items():
        in_dtype = df_input[in_col].dtype
        out_dtype = df_output[out_col].dtype
        
        if pd.api.types.is_object_dtype(in_dtype) or pd.api.types.is_object_dtype(out_dtype):
            value_mapping, status = analyze_value_mapping(df_input, in_col, df_output, out_col)
            
            if value_mapping and any(k != v for k, v in value_mapping.items()):
                has_value_mappings = True
                safe_col_name = out_col.replace(' ', '_').replace('-', '_').replace('/', '_')
                lines.append(f'    ')
                lines.append(f'    # {out_col}')
                lines.append(f'    {safe_col_name}_mapping = {{')
                for in_val, out_val in sorted(value_mapping.items(), key=lambda x: str(x[0])):
                    if in_val != out_val:
                        lines.append(f'        "{in_val}": "{out_val}",')
                    else:
                        lines.append(f'        "{in_val}": "{out_val}",  # Uendret')
                lines.append(f'    }}')
                lines.append(f'    df["{out_col}"] = df["{out_col}"].map({safe_col_name}_mapping)')
                lines.append(f'    ')
                lines.append(f'    # Sjekk for umappede verdier')
                lines.append(f'    unmapped = df["{out_col}"].isna().sum()')
                lines.append(f'    if unmapped > 0:')
                lines.append(f'        print(f"[!] Advarsel: {{unmapped}} verdier i {out_col} ble ikke mappet")')
    
    if not has_value_mappings:
        lines.append('    # Ingen verdimappings noedvendig')
    
    lines.append('    ')
    lines.append('    # Steg 3: Fjern unnoedvendige kolonner')
    if unmapped_input:
        lines.append(f'    cols_to_drop = {unmapped_input}')
        lines.append('    df = df.drop(columns=cols_to_drop, errors="ignore")')
        lines.append(f'    print(f"[OK] Fjernet {{len(cols_to_drop)}} kolonner")')
    else:
        lines.append('    # Ingen kolonner aa fjerne')
    
    lines.append('    ')
    lines.append('    # Steg 4: Legg til manglende kolonner')
    if unmapped_output:
        lines.append('    # MANUELL HANDLING NOEDVENDIG:')
        for col in unmapped_output:
            lines.append(f'    # df["{col}"] = ...  # TODO: Implementer logikk for {col}')
            lines.append(f'    df["{col}"] = None  # Placeholder')
        lines.append(f'    print(f"[!] Advarsel: {{len({unmapped_output})}} kolonner maa fylles manuelt")')
    else:
        lines.append('    # Alle noedvendige kolonner er tilstede')
    
    lines.append('    ')
    lines.append('    return df')
    lines.append('')
    lines.append('')
    lines.append('def main(input_file, output_file):')
    lines.append('    """Hovedfunksjon."""')
    lines.append('    print("=" * 80)')
    lines.append(f'    print("DATAPREP: {table_code}")')
    lines.append('    print("=" * 80)')
    lines.append('    ')
    lines.append('    # Les input')
    lines.append(f'    print(f"\\nLeser input: {{input_file}}")')
    if input_sheet != 0:
        lines.append(f'    df = pd.read_excel(input_file, sheet_name="{input_sheet}")')
    else:
        lines.append(f'    df = pd.read_excel(input_file)')
    lines.append('    print(f"  {{len(df)}} rader, {{len(df.columns)}} kolonner")')
    lines.append('    ')
    lines.append('    # Valider input')
    lines.append('    validate_input(df)')
    lines.append('    ')
    lines.append('    # Transformer')
    lines.append('    print("\\nUtfoerer transformasjon...")')
    lines.append('    df_transformed = transform_data(df)')
    lines.append('    ')
    lines.append('    # Valider output')
    lines.append('    validate_output(df_transformed)')
    lines.append('    ')
    lines.append('    # Lagre')
    lines.append('    print(f"\\nLagrer output: {{output_file}}")')
    if output_sheet != 0:
        lines.append(f'    df_transformed.to_excel(output_file, sheet_name="{output_sheet}", index=False)')
    else:
        lines.append(f'    df_transformed.to_excel(output_file, index=False)')
    lines.append('    ')
    lines.append('    print("\\n" + "=" * 80)')
    lines.append('    print("FULLFOERT!")')
    lines.append('    print("=" * 80)')
    lines.append('    print(f"Output: {{output_file}}")')
    lines.append('    print(f"Rader: {{len(df_transformed)}}")')
    lines.append('    print(f"Kolonner: {{list(df_transformed.columns)}}")')
    lines.append('    ')
    lines.append('    return df_transformed')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    import argparse')
    lines.append('    ')
    lines.append('    parser = argparse.ArgumentParser(description=f"Dataprep for {table_code}")')
    lines.append('    parser.add_argument("input_file", help="Input Excel-fil")')
    lines.append('    parser.add_argument("output_file", help="Output Excel-fil")')
    lines.append('    ')
    lines.append('    args = parser.parse_args()')
    lines.append('    ')
    lines.append('    try:')
    lines.append('        main(args.input_file, args.output_file)')
    lines.append('    except Exception as e:')
    lines.append('        print(f"\\n[FEIL] {{e}}", file=sys.stderr)')
    lines.append('        sys.exit(1)')
    
    return '\n'.join(lines), script_name


def main():
    parser = argparse.ArgumentParser(
        description='Generer Python prep-script basert på input/output analyse',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Eksempel:
  %(prog)s ok-sos002_input.xlsx OK-SOS002_prep_output.xlsx --table-code OK-SOS002 --input-sheet a --output-sheet ark1
  
Dette genererer: OK-SOS002_prep.py
        """
    )
    
    parser.add_argument('input_file', help='Input Excel-fil')
    parser.add_argument('output_file', help='Output Excel-fil (referanse)')
    parser.add_argument('--table-code', required=True, help='Tabellkode (f.eks. OK-SOS002)')
    parser.add_argument('--input-sheet', default=0, help='Input ark-navn eller indeks')
    parser.add_argument('--output-sheet', default=0, help='Output ark-navn eller indeks')
    parser.add_argument('--output-dir', default='.', help='Mappe for generert script')
    parser.add_argument('--similarity-threshold', type=float, default=0.6,
                       help='Terskelverdi for kolonnenavn-likhet (0-1)')
    
    args = parser.parse_args()
    
    # Konverter sheet-parametere
    input_sheet = args.input_sheet
    output_sheet = args.output_sheet
    try:
        input_sheet = int(input_sheet)
    except (ValueError, TypeError):
        pass
    try:
        output_sheet = int(output_sheet)
    except (ValueError, TypeError):
        pass
    
    # Les filer
    print(f"Leser {args.input_file}...", file=sys.stderr)
    df_input = pd.read_excel(args.input_file, sheet_name=input_sheet)
    
    print(f"Leser {args.output_file}...", file=sys.stderr)
    df_output = pd.read_excel(args.output_file, sheet_name=output_sheet)
    
    # Analyser
    print("Analyserer transformasjoner...", file=sys.stderr)
    col_mapping, unmapped_input, unmapped_output = find_column_mapping(
        df_input, df_output, args.similarity_threshold
    )
    
    # Generer script
    print(f"Genererer prep-script...", file=sys.stderr)
    script_content, script_name = generate_prep_script(
        args.table_code, args.input_file, args.output_file,
        col_mapping, unmapped_input, unmapped_output,
        df_input, df_output, input_sheet, output_sheet
    )
    
    # Lagre
    output_path = Path(args.output_dir) / script_name
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"GENERERT SCRIPT: {output_path}", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    print(f"Kolonner mappet: {len(col_mapping)}", file=sys.stderr)
    print(f"Kolonner fjernet: {len(unmapped_input)}", file=sys.stderr)
    print(f"Kolonner lagt til: {len(unmapped_output)}", file=sys.stderr)
    
    if unmapped_output:
        print(f"\n[!] ADVARSEL: {len(unmapped_output)} kolonner maa fylles manuelt:", file=sys.stderr)
        for col in unmapped_output:
            print(f"  - {col}", file=sys.stderr)
    
    print(f"\nKjoer scriptet med:", file=sys.stderr)
    print(f"  python {script_name} input.xlsx output.xlsx", file=sys.stderr)


if __name__ == '__main__':
    main()
