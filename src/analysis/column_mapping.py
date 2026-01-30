"""
Kolonnemapping mellom input og output DataFrames.

Finner hvilke input-kolonner som tilsvarer hvilke output-kolonner basert på:
1. Kontrollskjema (standardiserte variabelnavn)
2. Eksakte match (case-insensitive)
3. Kodeliste-transformasjoner
4. Fuzzy matching på kolonnenavn
5. Datainnhold-basert matching
"""

import re
import pandas as pd
from difflib import SequenceMatcher
from typing import Optional
from pathlib import Path


def similarity(a: str, b: str) -> float:
    """Beregn likhet mellom to strenger (0-1)."""
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def suggest_geographic_column_name(
    input_col_name: str, 
    table_code: Optional[str] = None, 
    df_input: Optional[pd.DataFrame] = None
) -> tuple[str, str, list[str]]:
    """
    Foreslå geografisk kolonnenavn basert på kontekst.
    
    Args:
        input_col_name: Navn på input-kolonne
        table_code: Tabellkode (f.eks. OK-BEF001, OK-SYS001)
        df_input: Input dataframe for å analysere innhold
    
    Returns:
        tuple: (code_col_suggestion, label_col_suggestion, reasoning_list)
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
        if domain == 'befolkning':
            code_col = 'bosted_'
            label_col = 'bosted'
            reasoning.append("Befolkningsdata med bydel → bruk 'bosted'")
        else:
            code_col = 'bydel_'
            label_col = 'bydel'
            reasoning.append("Bydelsnivå, domene ikke befolkning → bruk 'bydel'")
    else:
        code_col = 'geografi_'
        label_col = 'geografi'
        reasoning.append("Generisk geografisk kolonne")
    
    return code_col, label_col, reasoning


def find_duplicate_column_variants(column_name: str, columns: list[str]) -> list[str]:
    """Finn alle varianter av en kolonne med .1, .2 suffixer."""
    variants = []
    
    if column_name in columns:
        variants.append(column_name)
    
    i = 1
    while f"{column_name}.{i}" in columns:
        variants.append(f"{column_name}.{i}")
        i += 1
    
    return variants


def resolve_duplicate_mappings(mappings: dict, output_cols: list[str]) -> dict:
    """
    Løs situasjoner der flere input-kolonner mapper til samme output-kolonne.
    Prøv å fordele dem på .1, .2 varianter hvis de finnes.
    """
    output_usage = {}
    for in_col, out_col in mappings.items():
        if out_col not in output_usage:
            output_usage[out_col] = []
        output_usage[out_col].append(in_col)
    
    updated_mappings = mappings.copy()
    
    for out_col, in_cols in output_usage.items():
        if len(in_cols) > 1:
            variants = find_duplicate_column_variants(out_col, output_cols)
            
            if len(variants) >= len(in_cols):
                in_cols_sorted = sorted(in_cols, key=lambda x: (
                    '_fmt' in x.lower(),
                    x
                ))
                
                for i, in_col in enumerate(in_cols_sorted):
                    if i < len(variants):
                        updated_mappings[in_col] = variants[i]
    
    return updated_mappings


def find_column_mapping_with_codelists(
    df_input: pd.DataFrame, 
    df_output: pd.DataFrame, 
    codelist_manager,
    kontrollskjema: Optional[dict] = None, 
    table_code: Optional[str] = None, 
    similarity_threshold: float = 0.6,
    known_pairs: Optional[list[dict]] = None
) -> dict:
    """
    Finn kolonnemappings mellom input og output, med kodeliste-støtte.
    
    Args:
        df_input: Input DataFrame
        df_output: Output DataFrame
        codelist_manager: CodelistManager instans
        kontrollskjema: Kontrollskjema dict (valgfri)
        table_code: Tabellkode for kontekstuell forståelse
        similarity_threshold: Minimum likhet for matching (0-1)
        known_pairs: Liste av variabel-par dicts
    
    Returns:
        dict med:
            - 'mappings': {input_col: output_col}
            - 'value_transformations': {input_col: transformation_info}
            - 'standardization_suggestions': {input_col: standard_name}
            - 'geographic_suggestions': {input_col: suggestion_info}
            - 'unmapped_input': [kolonner uten mapping]
            - 'unmapped_output': [output-kolonner uten match]
    """
    input_cols = df_input.columns.tolist()
    output_cols = df_output.columns.tolist()
    
    mappings = {}
    value_transformations = {}
    standardization_suggestions = {}
    geographic_suggestions = {}
    used_output_cols = set()
    
    # Bygg sett av label-kolonner
    skip_label_cols = set()
    if known_pairs:
        for pair in known_pairs:
            skip_label_cols.add(pair['label'])
    
    # Last standard variabler fra kontrollskjema
    standard_vars = {}
    if kontrollskjema:
        standard_vars = kontrollskjema.get('standard_variables', {})
    
    # 1. Sjekk mot kontrollskjema først
    if standard_vars:
        for in_col in input_cols:
            if in_col in skip_label_cols:
                continue
                
            in_col_lower = in_col.lower().strip()
            
            for std_name, std_info in standard_vars.items():
                alt_names = [name.lower() for name in std_info.get('alternative_names', [])]
                
                if in_col_lower == std_name or in_col_lower in alt_names:
                    if std_name == 'geografi' or 'geografi' in str(std_info.get('description', '')).lower():
                        code_col, label_col, reasoning = suggest_geographic_column_name(
                            in_col, table_code, df_input
                        )
                        geographic_suggestions[in_col] = {
                            'code_column': code_col,
                            'label_column': label_col,
                            'reasoning': reasoning
                        }
                        if code_col in output_cols:
                            mappings[in_col] = code_col
                            used_output_cols.add(code_col)
                        elif label_col in output_cols:
                            mappings[in_col] = label_col
                            used_output_cols.add(label_col)
                        break
                    else:
                        if std_name in output_cols:
                            mappings[in_col] = std_name
                            used_output_cols.add(std_name)
                            if in_col != std_name:
                                standardization_suggestions[in_col] = std_name
                            break
    
    # 2. Eksakte match
    for in_col in input_cols:
        if in_col in skip_label_cols or in_col in mappings:
            continue
            
        in_col_clean = in_col.lower().strip().replace(' ', '').replace('_', '')
        for out_col in output_cols:
            out_col_clean = out_col.lower().strip().replace(' ', '').replace('_', '')
            if in_col_clean == out_col_clean and out_col not in used_output_cols:
                mappings[in_col] = out_col
                used_output_cols.add(out_col)
                break
    
    # 3. Kodeliste-transformasjoner
    for in_col in input_cols:
        out_col = mappings.get(in_col)
        
        if out_col:
            in_values = set(df_input[in_col].dropna().astype(str).unique()[:100])
            out_values = set(df_output[out_col].dropna().astype(str).unique()[:100])
            
            codelist = codelist_manager.find_matching_codelist(
                in_col, out_col, in_values, out_values
            )
            
            if codelist:
                value_transformations[in_col] = {
                    'target_col': out_col,
                    'codelist': codelist['name'],
                    'type': 'codelist_mapping'
                }
        else:
            in_values = set(df_input[in_col].dropna().astype(str).unique()[:100])
            
            for out_col_candidate in output_cols:
                if out_col_candidate in used_output_cols:
                    continue
                
                out_values = set(df_output[out_col_candidate].dropna().astype(str).unique()[:100])
                
                codelist = codelist_manager.find_matching_codelist(
                    in_col, out_col_candidate, in_values, out_values
                )
                
                if codelist:
                    mappings[in_col] = out_col_candidate
                    value_transformations[in_col] = {
                        'target_col': out_col_candidate,
                        'codelist': codelist['name'],
                        'type': 'codelist_mapping'
                    }
                    used_output_cols.add(out_col_candidate)
                    break
    
    # 4. Likhet i kolonnenavn
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
    
    # 5. Datainnhold-basert mapping
    for in_col in input_cols:
        if in_col in mappings:
            continue
        
        in_unique = df_input[in_col].nunique()
        
        for out_col in output_cols:
            if out_col in used_output_cols:
                continue
            
            out_unique = df_output[out_col].nunique()
            
            if in_unique > 0 and out_unique > 0:
                in_vals = set(df_input[in_col].dropna().astype(str).unique()[:20])
                out_vals = set(df_output[out_col].dropna().astype(str).unique()[:20])
                
                if in_vals and out_vals:
                    overlap = len(in_vals & out_vals) / max(len(in_vals), len(out_vals))
                    
                    if overlap > 0.3:
                        mappings[in_col] = out_col
                        used_output_cols.add(out_col)
                        break
    
    # 6. Løs duplikate mappings
    mappings = resolve_duplicate_mappings(mappings, output_cols)
    used_output_cols = set(mappings.values())
    
    # 7. Map label-kolonner fra variabel-par til .1 varianter
    if known_pairs:
        for pair in known_pairs:
            base_col = pair['base']
            label_col = pair['label']
            
            # Finn hvilken output-kolonne base mapper til
            base_output = mappings.get(base_col)
            if base_output:
                # Sjekk om .1 variant finnes i output
                label_output = f"{base_output}.1"
                if label_output in output_cols and label_output not in used_output_cols:
                    mappings[label_col] = label_output
                    used_output_cols.add(label_output)
    
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
