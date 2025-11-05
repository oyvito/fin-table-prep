"""
Forbedret versjon av generate_prep_script.py
- Støtter flere input-filer (for joins/beregninger)
- Integrerer kodeliste-systemet
- Lærer fra eksisterende eksempler i training_data/
- Bruker kontrollskjema for standardisering
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from codelist_manager import CodelistManager


def similarity(a, b):
    """Beregn likhet mellom to strenger (0-1)."""
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def load_training_examples():
    """Last inn eksisterende eksempler fra training_data/."""
    training_data = Path("training_data")
    examples = []
    
    if not training_data.exists():
        return examples
    
    for example_dir in training_data.iterdir():
        if not example_dir.is_dir():
            continue
        
        # Sjekk om det finnes metadata
        metadata_file = example_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                examples.append({
                    "table_code": example_dir.name,
                    "path": example_dir,
                    "metadata": metadata
                })
    
    return examples


def load_kontrollskjema():
    """Last inn kontrollskjema for standardisering."""
    kontrollskjema_path = Path("kontrollskjema.json")
    if kontrollskjema_path.exists():
        with open(kontrollskjema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def suggest_geographic_column_name(input_col_name, table_code=None, df_input=None):
    """
    Foreslå geografisk kolonnenavn basert på kontekst.
    
    Args:
        input_col_name: Navn på input-kolonne
        table_code: Tabellkode (f.eks. OK-BEF001, OK-SYS001)
        df_input: Input dataframe for å analysere innhold
    
    Returns:
        tuple: (suggested_code_col, suggested_label_col, reasoning)
    """
    col_lower = input_col_name.lower()
    
    # Detekter kontekst fra kolonnenavn
    is_work = any(word in col_lower for word in ['arb', 'arbeid', 'work', 'job', 'sysselset'])
    is_home = any(word in col_lower for word in ['bo', 'bost', 'home', 'resident', 'bosatt'])
    
    # Detekter nivå
    is_grunnkrets = 'krets' in col_lower or 'gkrets' in col_lower
    is_delbydel = 'delbydel' in col_lower
    is_bydel = 'bydel' in col_lower and not is_delbydel
    
    # Detekter fra tabellkode
    domain = None
    if table_code:
        if table_code.startswith('OK-BEF'):
            domain = 'befolkning'
        elif table_code.startswith('OK-SYS'):
            domain = 'sysselsetting'
        elif table_code.startswith('OK-UTD'):
            domain = 'utdanning'
        elif table_code.startswith('OK-NAE'):
            domain = 'næring'
        elif table_code.startswith('OK-VAL'):
            domain = 'valg'
    
    # Bestem navn basert på kontekst
    reasoning = []
    
    if is_grunnkrets:
        code_col = 'grunnkrets_'
        label_col = 'grunnkrets'
        reasoning.append("Grunnkretsnivå detektert fra kolonnenavn")
    elif is_delbydel:
        code_col = 'delbydel_'
        label_col = 'delbydel'
        reasoning.append("Delbydelsnivå detektert fra kolonnenavn")
    elif is_work:
        code_col = 'arbeidssted_'
        label_col = 'arbeidssted'
        reasoning.append("Arbeidssted detektert (arb/arbeid i kolonnenavn)")
    elif is_home or domain in ['befolkning', 'valg']:
        code_col = 'bosted_'
        label_col = 'bosted'
        if is_home:
            reasoning.append("Bosted detektert (bo/bost i kolonnenavn)")
        if domain in ['befolkning', 'valg']:
            reasoning.append(f"Domene '{domain}' indikerer bostedsdata")
    elif is_bydel:
        # Bydel kan være både bosted og generisk
        if domain == 'befolkning':
            code_col = 'bosted_'
            label_col = 'bosted'
            reasoning.append("Befolkningsdata med bydel → bruk 'bosted'")
            reasoning.append("MERK: Hvis Marka aggregeres til admin. bydel, vurder 'bydel' i stedet")
        else:
            code_col = 'bydel_'
            label_col = 'bydel'
            reasoning.append("Bydelsnivå, domene ikke befolkning → bruk 'bydel'")
    else:
        # Fallback til generisk geografi
        code_col = 'geografi_'
        label_col = 'geografi'
        reasoning.append("Generisk geografisk kolonne - vurder spesifikt navn basert på innhold")
    
    return code_col, label_col, reasoning


def find_column_mapping_with_codelists(df_input, df_output, codelist_manager, 
                                      kontrollskjema=None, table_code=None, similarity_threshold=0.6):
    """
    Finn kolonnemappings mellom input og output, med kodeliste-støtte og standardisering.
    
    Args:
        df_input: Input DataFrame
        df_output: Output DataFrame
        codelist_manager: CodelistManager instans
        kontrollskjema: Kontrollskjema dict
        table_code: Tabellkode for kontekstuell forståelse (f.eks. OK-BEF001)
        similarity_threshold: Minimum likhet for matching (0-1)
    """
    input_cols = df_input.columns.tolist()
    output_cols = df_output.columns.tolist()
    
    mappings = {}
    value_transformations = {}  # Kodeliste-transformasjoner
    standardization_suggestions = {}  # Forslag til standardisering
    geographic_suggestions = {}  # Forslag til geografiske kolonner
    used_output_cols = set()
    
    # Last standard variabler fra kontrollskjema
    standard_vars = {}
    if kontrollskjema:
        standard_vars = kontrollskjema.get('standard_variables', {})
    
    # 1. Sjekk mot kontrollskjema først
    if standard_vars:
        for in_col in input_cols:
            in_col_lower = in_col.lower().strip()
            
            # Sjekk om input-kolonne matcher standard variabel eller alternativt navn
            for std_name, std_info in standard_vars.items():
                alt_names = [name.lower() for name in std_info.get('alternative_names', [])]
                
                if in_col_lower == std_name or in_col_lower in alt_names:
                    # Spesialhåndtering for geografiske kolonner
                    if std_name == 'geografi' or 'geografi' in str(std_info.get('description', '')).lower():
                        # Foreslå kontekstuelt navn
                        code_col, label_col, reasoning = suggest_geographic_column_name(
                            in_col, table_code, df_input
                        )
                        geographic_suggestions[in_col] = {
                            'code_column': code_col,
                            'label_column': label_col,
                            'reasoning': reasoning
                        }
                        # Prøv å matche mot output
                        if code_col in output_cols:
                            mappings[in_col] = code_col
                            used_output_cols.add(code_col)
                        elif label_col in output_cols:
                            mappings[in_col] = label_col
                            used_output_cols.add(label_col)
                        break
                    else:
                        # Standard matching for ikke-geografiske kolonner
                        # Se om output har standard-navnet
                        if std_name in output_cols:
                            mappings[in_col] = std_name
                            used_output_cols.add(std_name)
                            if in_col != std_name:
                                standardization_suggestions[in_col] = std_name
                            break
    
    # 2. Eksakte match (for kolonner ikke fanget av kontrollskjema)
    for in_col in input_cols:
        in_col_clean = in_col.lower().strip().replace(' ', '').replace('_', '')
        for out_col in output_cols:
            out_col_clean = out_col.lower().strip().replace(' ', '').replace('_', '')
            if in_col_clean == out_col_clean and out_col not in used_output_cols:
                mappings[in_col] = out_col
                used_output_cols.add(out_col)
                break
    
    # 2. Sjekk kodelister for umappede kolonner
    for in_col in input_cols:
        if in_col in mappings:
            continue
            
        in_values = set(df_input[in_col].dropna().astype(str).unique()[:100])
        
        for out_col in output_cols:
            if out_col in used_output_cols:
                continue
            
            out_values = set(df_output[out_col].dropna().astype(str).unique()[:100])
            
            # Finn matching kodeliste
            codelist = codelist_manager.find_matching_codelist(
                in_col, out_col, in_values, out_values
            )
            
            if codelist:
                mappings[in_col] = out_col
                value_transformations[in_col] = {
                    'target_col': out_col,
                    'codelist': codelist['name'],
                    'type': 'codelist_mapping'
                }
                used_output_cols.add(out_col)
                break
    
    # 3. Likhet i kolonnenavn
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
    
    # 4. Datainnhold-basert mapping
    for in_col in input_cols:
        if in_col in mappings:
            continue
        
        in_unique = df_input[in_col].nunique()
        
        for out_col in output_cols:
            if out_col in used_output_cols:
                continue
            
            out_unique = df_output[out_col].nunique()
            
            if in_unique > 0 and out_unique > 0:
                unique_ratio = min(in_unique, out_unique) / max(in_unique, out_unique)
                
                in_vals = set(df_input[in_col].dropna().astype(str).unique()[:20])
                out_vals = set(df_output[out_col].dropna().astype(str).unique()[:20])
                
                if in_vals and out_vals:
                    overlap = len(in_vals & out_vals) / max(len(in_vals), len(out_vals))
                    
                    if overlap > 0.3 or unique_ratio > 0.8:
                        mappings[in_col] = out_col
                        used_output_cols.add(out_col)
                        break
    
    unmapped_input = [col for col in input_cols if col not in mappings]
    unmapped_output = [col for col in output_cols if col not in used_output_cols]
    
    return {
        'mappings': mappings,
        'value_transformations': value_transformations,
        'standardization_suggestions': standardization_suggestions,
        'geographic_suggestions': geographic_suggestions,
        'unmapped_input': unmapped_input,
        'unmapped_output': unmapped_output
    }


def generate_multi_input_script(input_files, output_file, table_code, 
                                input_sheets=None, output_sheet=None):
    """
    Generer prep-script som håndterer flere input-filer.
    
    Args:
        input_files: List av input Excel-filer
        output_file: Output Excel-fil (referanse)
        table_code: Tabellkode (f.eks. OK-SYS001)
        input_sheets: List av sheet-navn for hver input-fil
        output_sheet: Output sheet-navn
    """
    
    # Last kodelister
    codelist_mgr = CodelistManager()
    
    # Last kontrollskjema
    kontrollskjema = load_kontrollskjema()
    
    # Last treningseksempler
    training_examples = load_training_examples()
    
    # Les input-filer
    input_dfs = []
    for i, input_file in enumerate(input_files):
        sheet = input_sheets[i] if input_sheets and i < len(input_sheets) else 0
        df = pd.read_excel(input_file, sheet_name=sheet)
        input_dfs.append(df)
        print(f"Input fil {i+1}: {input_file}")
        print(f"  Kolonner: {df.columns.tolist()}")
        print(f"  Rader: {len(df)}\n")
    
    # Les output-fil
    df_output = pd.read_excel(output_file, sheet_name=output_sheet or 0)
    print(f"Output fil: {output_file}")
    print(f"  Kolonner: {df_output.columns.tolist()}")
    print(f"  Rader: {len(df_output)}\n")
    
    # Analyser mappings for hver input-fil
    all_mappings = []
    all_transformations = []
    all_standardizations = []
    all_geographic_suggestions = []
    
    for i, df_input in enumerate(input_dfs):
        result = find_column_mapping_with_codelists(
            df_input, df_output, codelist_mgr, kontrollskjema, table_code
        )
        
        all_mappings.append({
            'file_index': i,
            'mappings': result['mappings'],
            'unmapped_input': result['unmapped_input'],
            'unmapped_output': result['unmapped_output']
        })
        
        all_transformations.append(result['value_transformations'])
        all_standardizations.append(result['standardization_suggestions'])
        all_geographic_suggestions.append(result['geographic_suggestions'])
        
        print(f"=== Input fil {i+1} ===")
        print(f"Mappings funnet: {len(result['mappings'])}")
        print(f"Kodeliste-transformasjoner: {len(result['value_transformations'])}")
        if result['standardization_suggestions']:
            print(f"Standardiserings-forslag: {result['standardization_suggestions']}")
        if result['geographic_suggestions']:
            print(f"\n🗺️  GEOGRAFISKE FORSLAG:")
            for col, suggestion in result['geographic_suggestions'].items():
                print(f"  {col} →")
                print(f"    Kode-kolonne: {suggestion['code_column']}")
                print(f"    Navn-kolonne: {suggestion['label_column']}")
                print(f"    Begrunnelse:")
                for reason in suggestion['reasoning']:
                    print(f"      - {reason}")
        print(f"Umappede input-kolonner: {result['unmapped_input']}")
        print(f"Umappede output-kolonner: {result['unmapped_output']}\n")
    
    # Generer script
    script_name = f"{table_code}_prep.py"
    
    script_content = generate_script_content_multi_input(
        input_files, all_mappings, all_transformations, all_geographic_suggestions,
        df_output.columns.tolist(), table_code
    )
    
    with open(script_name, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Generert: {script_name}")
    print(f"\n💡 Neste steg:")
    print(f"1. Gjennomgå scriptet og juster TODO-seksjoner")
    print(f"2. Test: python {script_name} <input_files> <output.xlsx>")
    print(f"3. Lagre korrekt versjon i training_data/{table_code}/")


def generate_script_content_multi_input(input_files, all_mappings, 
                                       all_transformations, all_geographic_suggestions,
                                       output_columns, table_code):
    """Generer selve Python-scriptet for multi-input transformasjon."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    num_inputs = len(input_files)
    
    # Samle geografiske forslag for kommentarer
    geo_comments = []
    for i, geo_sugg in enumerate(all_geographic_suggestions):
        if geo_sugg:
            geo_comments.append(f"\nInput fil {i+1} - Geografiske kolonneforslag:")
            for col, suggestion in geo_sugg.items():
                geo_comments.append(f"  {col}:")
                geo_comments.append(f"    → Kode: {suggestion['code_column']}, Navn: {suggestion['label_column']}")
                for reason in suggestion['reasoning']:
                    geo_comments.append(f"       {reason}")
    
    geo_comment_block = "\n".join(geo_comments) if geo_comments else ""
    
    script = f'''"""
Prep-script for {table_code}
Generert: {timestamp}
Antall input-filer: {num_inputs}

Dette scriptet tar {num_inputs} input-fil(er) og transformerer til output-format.

VIKTIG - Geografiske kolonner:
Kontrollskjemaet er en GUIDE, ikke en rigid mal. Velg geografinavn som 
reflekterer tabellens innhold:
- bosted: Befolkningsdata - hvor folk bor
- arbeidssted: Sysselsettingsdata - arbeidsplassens beliggenhet  
- bydel: Administrativ bydel (inkl. Marka aggregert til admin. bydel)
- geografi: Generisk når kontekst er uklar
{geo_comment_block}
"""

import pandas as pd
import sys
from pathlib import Path


def load_codelists():
    """Last inn relevante kodelister."""
    import json
    codelists = {{}}
    
'''
    
    # Finn unike kodelister som brukes
    used_codelists = set()
    for transformations in all_transformations:
        for trans in transformations.values():
            if trans.get('type') == 'codelist_mapping':
                used_codelists.add(trans['codelist'])
    
    for codelist_name in used_codelists:
        script += f'''    # {codelist_name}
    try:
        with open('kodelister/{codelist_name}.json', 'r', encoding='utf-8') as f:
            codelists['{codelist_name}'] = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Kodeliste ikke funnet: {codelist_name}.json")
    
'''
    
    script += '''    return codelists


def transform_data('''
    
    # Argumenter for hver input-fil
    for i in range(num_inputs):
        script += f'input_file{i+1}, '
    script += '''output_file):
    """
    Hovedtransformasjon.
    """
    
    # Last kodelister
    codelists = load_codelists()
    
'''
    
    # Les input-filer
    for i in range(num_inputs):
        script += f'''    # Les input fil {i+1}
    print(f"Leser {{input_file{i+1}}}...")
    df{i+1} = pd.read_excel(input_file{i+1})
    print(f"  {{len(df{i+1})}} rader, {{len(df{i+1}.columns)}} kolonner")
    
'''
    
    # Generer transformasjonslogikk for hver fil
    for i, mapping_info in enumerate(all_mappings, 1):
        mappings = mapping_info['mappings']
        transformations = all_transformations[i-1]
        
        if mappings:
            script += f'''    # Transformer data fra input {i}
    df{i}_transformed = df{i}.copy()
    
'''
            
            # Kolonnenavn-endringer
            rename_dict = {k: v for k, v in mappings.items() if k not in transformations}
            if rename_dict:
                script += f'''    # Endre kolonnenavn
    df{i}_transformed = df{i}_transformed.rename(columns={{
'''
                for old_col, new_col in rename_dict.items():
                    script += f'''        '{old_col}': '{new_col}',
'''
                script += '''    })
    
'''
            
            # Kodeliste-transformasjoner
            for in_col, trans_info in transformations.items():
                codelist_name = trans_info['codelist']
                target_col = trans_info['target_col']
                script += f'''    # Transformer '{in_col}' → '{target_col}' med {codelist_name}
    if '{codelist_name}' in codelists:
        codelist = codelists['{codelist_name}']
        mapping = codelist.get('mappings', {{}})
        
        # TODO: Velg riktig mapping (tknr_to_px, tknr_to_ssb, eller standard mappings)
        # df{i}_transformed['{target_col}'] = df{i}_transformed['{in_col}'].map(mapping)
        
        # Legg til labels hvis nødvendig
        # labels = codelist.get('labels', {{}})
        # df{i}_transformed['{target_col}_navn'] = df{i}_transformed['{target_col}'].map(labels)
    
'''
    
    script += f'''    
    # TODO: Kombiner data fra flere input-filer
    # Eksempel joins, beregninger, etc.
    '''
    
    if num_inputs > 1:
        script += f'''
    # Eksempel på join:
    # df_combined = df1_transformed.merge(
    #     df2_transformed, 
    #     on=['felles_kolonne'], 
    #     how='left'
    # )
    
    # Eksempel på beregning (sysselsettingsandel):
    # df_combined['sysselsettingsandel'] = (
    #     df_combined['antall_sysselsatte'] / df_combined['befolkning'] * 100
    # )
    '''
    
    script += f'''
    # TODO: Velg endelig datasett
    df_final = df1_transformed  # ENDRE DETTE
    
    # Velg og sorter output-kolonner
    output_columns = {output_columns}
    
    # TODO: Fjern kolonner som ikke finnes i df_final
    available_cols = [col for col in output_columns if col in df_final.columns]
    df_final = df_final[available_cols]
    
    # Lagre output
    print(f"Lagrer {{output_file}}...")
    df_final.to_excel(output_file, index=False)
    print(f"✅ Ferdig! {{len(df_final)}} rader lagret.")


if __name__ == "__main__":
    if len(sys.argv) < {num_inputs + 2}:
        print("Bruk: python {table_code}_prep.py '''
    
    for i in range(1, num_inputs + 1):
        script += f'<input{i}.xlsx> '
    
    script += f'''<output.xlsx>")
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


def main():
    parser = argparse.ArgumentParser(
        description="Generer prep-script med støtte for flere input-filer"
    )
    parser.add_argument('input_files', nargs='+', help='Input Excel-filer')
    parser.add_argument('--output', '-o', required=True, help='Output Excel-fil (referanse)')
    parser.add_argument('--table-code', '-t', required=True, help='Tabellkode (f.eks. OK-SYS001)')
    parser.add_argument('--input-sheets', nargs='+', help='Sheet-navn for input-filer')
    parser.add_argument('--output-sheet', help='Sheet-navn for output-fil')
    
    args = parser.parse_args()
    
    print(f"=== Genererer prep-script for {args.table_code} ===\n")
    
    generate_multi_input_script(
        args.input_files,
        args.output,
        args.table_code,
        args.input_sheets,
        args.output_sheet
    )


if __name__ == "__main__":
    main()
