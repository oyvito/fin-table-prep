"""
Navne-uavhengig aggregeringsdeteksjon.

Detekterer aggregeringsmønstre mellom input og output ved å sammenligne
verdier i kolonner, uavhengig av kolonnenavn.

Aggregeringstyper:
- binary_total: 2→3 verdier (f.eks. Mann/Kvinne → Begge kjønn)
- geography_rollup: Detaljert→Total (f.eks. Bydel → Oslo i alt)
- category_grouping: Mange→Få kategorier
"""

import pandas as pd


def detect_aggregation_patterns_v2(
    df_input: pd.DataFrame, 
    df_output: pd.DataFrame, 
    mappings: dict
) -> dict:
    """
    Navne-uavhengig aggregeringsdeteksjon.
    
    Bruker mappings fra kolonnemapping i stedet for fuzzy matching.
    Klassifiserer basert på verdimønstre, ikke kolonnenavn.
    
    Args:
        df_input: Input DataFrame
        df_output: Output DataFrame  
        mappings: Dict {input_col: output_col}
    
    Returns:
        dict med:
            'aggregations': Liste av aggregeringsbeskrivelser, hver med:
                - 'column': Output kolonnenavn
                - 'input_column': Input kolonnenavn
                - 'new_values': Liste av nye verdier i output
                - 'type': Aggregeringstype
                - 'description': Tekstbeskrivelse
    
    Example:
        >>> mappings = {'kjoenn': 'kjønn'}
        >>> result = detect_aggregation_patterns_v2(df_in, df_out, mappings)
        >>> result['aggregations'][0]['type']
        'binary_total'
    """
    aggregations = []
    
    for col_in, col_out in mappings.items():
        # Skip label-kolonner
        if col_in.endswith('_fmt') or '.1' in col_out or '.2' in col_out:
            continue
        
        # Skip kolonner som ikke finnes
        if col_in not in df_input.columns or col_out not in df_output.columns:
            continue
        
        # Kun kolonner med lav kardinalitet (typiske dimensjoner)
        if df_output[col_out].nunique() > 50:
            continue
        
        # Sammenlign verdier
        vals_in = set(df_input[col_in].dropna().astype(str).unique())
        vals_out = set(df_output[col_out].dropna().astype(str).unique())
        
        new_vals = vals_out - vals_in
        
        if new_vals:
            # Klassifiser basert på verdimønstre
            num_input = len(vals_in)
            num_new = len(new_vals)
            
            # Heuristikk 1: Binær dimensjon som får én ny verdi
            if num_input == 2 and num_new == 1:
                agg_type = 'binary_total'
                description = 'Binær aggregering (2→3): Trolig "Total/Begge" kategori'
            
            # Heuristikk 2: Geografisk kode som forkortes
            elif all(len(str(v)) <= 3 for v in new_vals) and all(len(str(v)) > 3 for v in vals_in):
                agg_type = 'geography_rollup'
                description = 'Geografisk aggregering: Detaljert nivå → Totalnivå'
            
            # Heuristikk 3: Mange input-verdier, få nye
            elif num_input > 10 and num_new < 5:
                agg_type = 'category_grouping'
                description = f'Kategori-gruppering: {num_input} verdier → {len(vals_out)} (inkl. {num_new} aggregerte)'
            
            # Fallback: Navn-basert
            elif 'kjønn' in col_out.lower() or 'kjonn' in col_out.lower():
                agg_type = 'gender'
                description = 'Kjønnsaggregering (Begge kjønn)'
            elif any(g in col_out.lower() for g in ['geo', 'bydel', 'bosted', 'arbeidssted']):
                agg_type = 'geography'
                description = 'Geografisk aggregering'
            else:
                agg_type = 'other'
                description = f'Aggregering i {col_out}'
            
            aggregations.append({
                'column': col_out,
                'input_column': col_in,
                'new_values': sorted(new_vals),
                'type': agg_type,
                'description': description,
                'input_values': sorted(vals_in),
                'output_values': sorted(vals_out)
            })
    
    return {'aggregations': aggregations}
