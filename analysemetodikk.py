"""
ANALYSEMETODIKK FOR DATATRANSFORMASJON
Strukturert 5-stegs prosess for å forstå hva som må gjøres

Basert på: 
1) Encoding
2) Multi-input deteksjon
3) Multi-input merge-logikk
4) Aggregeringer
5) Beregninger
"""

import pandas as pd
import json
import sys
import io
from pathlib import Path
from difflib import SequenceMatcher
from codelist_manager import CodelistManager

# Sikre UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def similarity(a, b):
    """Beregn likhet mellom to strenger (0-1)."""
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def steg1_encoding_og_innlasting(input_files, output_file):
    """
    STEG 1: Les input og output, håndter encoding
    
    Returns:
        dict: {'input_dfs': [df1, df2, ...], 'df_output': df, 'input_files': [...]}
    """
    print("=" * 80)
    print("STEG 1: ENCODING OG INNLASTING")
    print("=" * 80)
    
    input_dfs = []
    for i, input_file in enumerate(input_files, 1):
        df = pd.read_excel(input_file)
        input_dfs.append(df)
        print(f"\n✓ Input {i}: {Path(input_file).name}")
        print(f"  {len(df)} rader, {len(df.columns)} kolonner")
        print(f"  Kolonner: {list(df.columns)}")
    
    df_output = pd.read_excel(output_file)
    print(f"\n✓ Output: {Path(output_file).name}")
    print(f"  {len(df_output)} rader, {len(df_output.columns)} kolonner")
    print(f"  Kolonner: {list(df_output.columns)}")
    
    return {
        'input_dfs': input_dfs,
        'df_output': df_output,
        'input_files': input_files
    }


def steg2_multi_input_deteksjon(data):
    """
    STEG 2: Er det flere input-filer?
    
    Returns:
        dict: {'is_multi_input': bool, 'num_inputs': int}
    """
    print("\n\n" + "=" * 80)
    print("STEG 2: MULTI-INPUT DETEKSJON")
    print("=" * 80)
    
    num_inputs = len(data['input_dfs'])
    is_multi = num_inputs > 1
    
    if is_multi:
        print(f"\n✓ MULTI-INPUT: {num_inputs} input-filer")
        print("  → Fortsett til STEG 3 (merge-analyse)")
    else:
        print(f"\n✓ SINGLE-INPUT: 1 input-fil")
        print("  → Hopp over STEG 3, gå til STEG 4 (aggregeringer)")
    
    return {
        'is_multi_input': is_multi,
        'num_inputs': num_inputs
    }


def steg3_multi_input_merge_logikk(data):
    """
    STEG 3: Analyser multi-input merge-logikk
    
    Sjekker:
    - Felles kolonner (potensielle merge-keys)
    - År-mismatch mellom filer
    - Forskjellige geografiske nivåer
    
    Returns:
        dict: {'merge_keys': [], 'year_mismatch': bool, 'geo_mismatch': bool}
    """
    print("\n\n" + "=" * 80)
    print("STEG 3: MULTI-INPUT MERGE-LOGIKK")
    print("=" * 80)
    
    if len(data['input_dfs']) == 1:
        print("\nHoppet over (single input)")
        return None
    
    # Analyser felles kolonner
    print("\n📊 Felles kolonner mellom inputs:")
    
    input_dfs = data['input_dfs']
    
    # Finn kolonner som finnes i alle inputs
    common_cols = set(input_dfs[0].columns)
    for df in input_dfs[1:]:
        common_cols &= set(df.columns)
    
    print(f"\n  Kolonner i alle inputs: {sorted(common_cols)}")
    
    # Analyser år-kolonner
    year_cols = [c for c in common_cols if 'aar' in c.lower() or c.lower() in ['år', 'year']]
    year_mismatch = False
    
    if year_cols:
        print(f"\n  År-kolonner: {year_cols}")
        for year_col in year_cols:
            years = [sorted(df[year_col].unique()) for df in input_dfs]
            print(f"\n    {year_col}:")
            for i, y in enumerate(years, 1):
                print(f"      Input {i}: {y}")
            
            if len(set(str(years[0])) ^ set(str(years[1:]))) > 0:
                year_mismatch = True
                print(f"    ⚠️  ÅR-MISMATCH detektert!")
    
    # Analyser geografiske kolonner
    geo_cols = [c for c in common_cols if any(g in c.lower() for g in ['geo', 'bydel', 'krets', 'bosted', 'arbeidssted'])]
    geo_mismatch = False
    
    if geo_cols:
        print(f"\n  Geografiske kolonner: {geo_cols}")
        for geo_col in geo_cols:
            n_unique = [df[geo_col].nunique() for df in input_dfs]
            print(f"\n    {geo_col}:")
            for i, n in enumerate(n_unique, 1):
                print(f"      Input {i}: {n} unike verdier")
            
            if len(set(n_unique)) > 1:
                geo_mismatch = True
                print(f"    ⚠️  GEOGRAFISK NIVÅ-MISMATCH detektert!")
    
    # Foreslå merge-keys
    print(f"\n\n💡 Foreslåtte merge-keys:")
    potential_keys = [c for c in common_cols if c not in ['antall', 'value', 'count']]
    if year_mismatch:
        potential_keys = [c for c in potential_keys if 'aar' not in c.lower()]
        print(f"  (ekskluderer år pga mismatch)")
    
    print(f"  {potential_keys}")
    
    return {
        'merge_keys': potential_keys,
        'year_mismatch': year_mismatch,
        'geo_mismatch': geo_mismatch,
        'common_cols': list(common_cols)
    }


def steg4_aggregeringer(data, mappings=None):
    """
    STEG 4: Detekter aggregeringer
    
    Sjekker om output har flere kategorier enn input i samme variabel.
    Eksempel: Kjønn [Mann, Kvinne] i input → [Mann, Kvinne, Begge kjønn] i output
    
    Args:
        data: Dict med input_dfs og df_output
        mappings: Dict {input_col: output_col} fra kolonnemapping (valgfri)
    
    Returns:
        dict: {'aggregations': [{'column': ..., 'new_values': ..., 'type': ...}, ...]}
    """
    print("\n\n" + "=" * 80)
    print("STEG 4: AGGREGERINGER")
    print("=" * 80)
    
    df_input = data['input_dfs'][0]
    df_output = data['df_output']
    
    aggregations = []
    
    if mappings:
        print("\n🔍 Bruker kolonne-mappings fra tidligere analyse")
        print("(Dette gjør deteksjonen uavhengig av kolonnenavn!)")
        
        # Bruk mappings direkte - NAVNE-UAVHENGIG!
        for col_in, col_out in mappings.items():
            # Skip label-kolonner
            if col_in.endswith('_fmt') or '.1' in col_out or '.2' in col_out:
                continue
            
            # Kun kolonner med lav kardinalitet
            if df_output[col_out].nunique() > 50:
                continue
            
            print(f"\n  📊 Sjekker mapping: '{col_in}' → '{col_out}'")
            
            # Sammenlign verdier
            vals_in = set(df_input[col_in].dropna().astype(str).unique())
            vals_out = set(df_output[col_out].dropna().astype(str).unique())
            
            new_vals = vals_out - vals_in
            
            if new_vals:
                # Generisk klassifisering basert på verdiene, ikke navn!
                agg_type = classify_aggregation_type(col_out, new_vals, vals_in, vals_out)
                
                aggregations.append({
                    'column': col_out,
                    'input_column': col_in,
                    'new_values': sorted(new_vals),
                    'type': agg_type['type'],
                    'description': agg_type['description'],
                    'input_values': sorted(vals_in),
                    'output_values': sorted(vals_out)
                })
                
                print(f"      Input:  {sorted(vals_in)}")
                print(f"      Output: {sorted(vals_out)}")
                print(f"      NYE:    {sorted(new_vals)}")
                print(f"      Type:   {agg_type['description']}")
    
    else:
        print("\n🔍 Ingen mappings tilgjengelig - bruker fuzzy matching")
        print("(Anbefaler å kjøre kolonnemapping først for bedre nøyaktighet)")
        
        # Fallback: fuzzy matching (gammel metode)
        for col_out in df_output.columns:
            n_unique = df_output[col_out].nunique()
            
            if n_unique > 50:
                continue
            
            if '.1' in col_out or '.2' in col_out:
                continue
            
            print(f"\n  📊 Sjekker '{col_out}' ({n_unique} unike verdier)...")
            
            # Finn tilsvarende kolonne i input (similarity matching)
            col_in = None
            best_match = None
            best_score = 0
            
            for c in df_input.columns:
                if c.endswith('_fmt'):
                    continue
                
                score = similarity(col_out, c)
                if score > best_score:
                    best_score = score
                    best_match = c
            
            if best_score >= 0.6:
                col_in = best_match
                print(f"      Match funnet: '{col_in}' (likhet: {best_score:.2f})")
            else:
                print(f"      Ingen god match (beste: '{best_match}' = {best_score:.2f})")
                continue
            
            # Sammenlign verdier
            vals_in = set(df_input[col_in].dropna().astype(str).unique())
            vals_out = set(df_output[col_out].dropna().astype(str).unique())
            
            new_vals = vals_out - vals_in
            
            if new_vals:
                agg_type = classify_aggregation_type(col_out, new_vals, vals_in, vals_out)
                
                aggregations.append({
                    'column': col_out,
                    'input_column': col_in,
                    'new_values': sorted(new_vals),
                    'type': agg_type['type'],
                    'description': agg_type['description'],
                    'input_values': sorted(vals_in),
                    'output_values': sorted(vals_out)
                })
                
                print(f"\n  ⚡ {col_out}:")
                print(f"      Input:  {sorted(vals_in)}")
                print(f"      Output: {sorted(vals_out)}")
                print(f"      NYE:    {sorted(new_vals)}")
                print(f"      Type:   {agg_type['description']}")
    
    if not aggregations:
        print("\n  ✓ Ingen aggregeringer detektert")
    
    return {'aggregations': aggregations}


def classify_aggregation_type(col_name, new_vals, input_vals, output_vals):
    """
    Klassifiser aggregeringstype basert på VERDIER, ikke bare kolonnenavn.
    
    Dette gjør klassifiseringen mer robust og navne-uavhengig.
    """
    # Analysér karakteristika ved nye verdier
    num_input = len(input_vals)
    num_output = len(output_vals)
    num_new = len(new_vals)
    
    # Heuristikk 1: Binær dimensjon som får én ny verdi → Trolig "total/begge"
    if num_input == 2 and num_new == 1:
        return {
            'type': 'binary_total',
            'description': f'Binær aggregering (2→3): Trolig "Total/Begge" kategori'
        }
    
    # Heuristikk 2: Geografisk kode som forkortes → Oslo i alt
    # (f.eks. ['30101', '30102', ...] → ['301'])
    if all(len(str(v)) <= 3 for v in new_vals) and all(len(str(v)) > 3 for v in input_vals):
        return {
            'type': 'geography_rollup',
            'description': 'Geografisk aggregering: Detaljert nivå → Totalnivå'
        }
    
    # Heuristikk 3: Mange input-verdier, få nye → Sannsynligvis gruppe-aggregering
    if num_input > 10 and num_new < 5:
        return {
            'type': 'category_grouping',
            'description': f'Kategori-gruppering: {num_input} verdier → {num_output} (inkl. {num_new} aggregerte)'
        }
    
    # Fallback: Navn-basert klassifisering (kun hvis heuristikk feiler)
    if 'kjønn' in col_name.lower() or 'kjonn' in col_name.lower():
        return {
            'type': 'gender',
            'description': 'Kjønnsaggregering (Begge kjønn)'
        }
    elif any(g in col_name.lower() for g in ['geo', 'bydel', 'bosted', 'arbeidssted']):
        return {
            'type': 'geography',
            'description': 'Geografisk aggregering (Oslo i alt / bydel-nivå)'
        }
    else:
        return {
            'type': 'other',
            'description': f'Aggregering i {col_name}'
        }


def steg5_beregninger(data):
    """
    STEG 5: Detekter beregninger
    
    Sjekker:
    - Nye kolonner i output som ikke finnes i input
    - Potensielle beregninger (andeler, rater, etc)
    
    Returns:
        dict: {'calculations': [{'column': ..., 'formula': ..., 'type': ...}, ...]}
    """
    print("\n\n" + "=" * 80)
    print("STEG 5: BEREGNINGER")
    print("=" * 80)
    
    df_output = data['df_output']
    
    # Samle alle input-kolonner
    all_input_cols = set()
    for df in data['input_dfs']:
        all_input_cols.update(df.columns)
    
    # Finn kolonner som kun finnes i output
    new_cols = [c for c in df_output.columns if c not in all_input_cols]
    
    calculations = []
    
    if new_cols:
        print(f"\n📊 Kolonner kun i output (potensielle beregninger):")
        for col in new_cols:
            print(f"  - {col}")
            
            # Analyser type beregning
            calc_type = None
            formula = None
            
            if 'andel' in col.lower() or 'rate' in col.lower() or '%' in col:
                calc_type = 'percentage'
                formula = 'Trolig: (teller / nevner) * 100'
            elif 'sum' in col.lower() or 'total' in col.lower():
                calc_type = 'sum'
                formula = 'Trolig: SUM av andre kolonner'
            else:
                calc_type = 'unknown'
                formula = 'Ukjent beregning'
            
            calculations.append({
                'column': col,
                'type': calc_type,
                'formula': formula
            })
    else:
        print("\n  ✓ Ingen nye kolonner i output (ingen beregninger)")
    
    return {'calculations': calculations}


def kjor_full_analyse(input_files, output_file, table_code, mappings=None):
    """
    Kjør fullstendig 5-stegs analyse
    
    Args:
        input_files: Liste av input-filer
        output_file: Output-fil
        table_code: Tabellkode
        mappings: Valgfri dict {input_col: output_col} fra kolonnemapping
    
    Returns:
        dict: Komplett analyseresultat
    """
    print("\n" + "🔬" * 40)
    print(f"FULLSTENDIG ANALYSE: {table_code}")
    print("🔬" * 40)
    
    # STEG 1
    data = steg1_encoding_og_innlasting(input_files, output_file)
    
    # STEG 2
    multi_result = steg2_multi_input_deteksjon(data)
    
    # STEG 3
    merge_result = None
    if multi_result['is_multi_input']:
        merge_result = steg3_multi_input_merge_logikk(data)
    
    # STEG 4 - Send med mappings hvis tilgjengelig!
    agg_result = steg4_aggregeringer(data, mappings=mappings)
    
    # STEG 5
    calc_result = steg5_beregninger(data)
    
    # OPPSUMMERING
    print("\n\n" + "=" * 80)
    print("📋 OPPSUMMERING")
    print("=" * 80)
    
    result = {
        'table_code': table_code,
        'multi_input': multi_result,
        'merge_analysis': merge_result,
        'aggregations': agg_result,
        'calculations': calc_result
    }
    
    print(f"\n✓ Analyse fullført for {table_code}")
    print(f"\n  Multi-input: {'JA' if multi_result['is_multi_input'] else 'NEI'}")
    print(f"  Aggregeringer: {len(agg_result['aggregations'])}")
    print(f"  Beregninger: {len(calc_result['calculations'])}")
    
    if merge_result:
        print(f"  År-mismatch: {'JA' if merge_result['year_mismatch'] else 'NEI'}")
        print(f"  Geo-mismatch: {'JA' if merge_result['geo_mismatch'] else 'NEI'}")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="5-stegs analyse av datatransformasjon")
    parser.add_argument('input_files', nargs='+', help='Input Excel-filer')
    parser.add_argument('--output', '-o', required=True, help='Output Excel-fil')
    parser.add_argument('--table-code', '-t', required=True, help='Tabellkode')
    
    args = parser.parse_args()
    
    result = kjor_full_analyse(args.input_files, args.output, args.table_code)
    
    # Lagre resultat til JSON
    output_path = Path(f"training_data/{args.table_code}/analyse_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Analyseresultat lagret: {output_path}")
