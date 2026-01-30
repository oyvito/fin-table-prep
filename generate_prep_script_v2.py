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

# Sikre UTF-8 encoding for alle fil-operasjoner
import locale
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


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
        
        example = {
            "table_code": example_dir.name,
            "path": example_dir,
            "metadata": None,
            "learning_outcomes": None
        }
        
        # Last metadata.json hvis den finnes
        metadata_file = example_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                example["metadata"] = json.load(f)
        
        # Last learning_outcomes.json hvis den finnes
        learning_file = example_dir / "learning_outcomes.json"
        if learning_file.exists():
            with open(learning_file, 'r', encoding='utf-8') as f:
                example["learning_outcomes"] = json.load(f)
        
        examples.append(example)
    
    return examples


def find_similar_tables(table_code, training_examples):
    """
    Finn lignende tabeller basert på tabellkode og learning outcomes.
    
    Args:
        table_code: Tabellkode å finne likhet med (f.eks. OK-SYS002)
        training_examples: Liste av training examples
    
    Returns:
        Liste av relevante learning outcomes
    """
    similar = []
    
    # Først: Samme tabellkategori (f.eks. OK-SYS)
    table_category = table_code.rsplit('-', 1)[0] if '-' in table_code else None
    
    for example in training_examples:
        if not example.get('learning_outcomes'):
            continue
        
        learning = example['learning_outcomes']
        
        # Sjekk om denne tabellen er relevant
        is_similar = False
        
        # 1. Samme kategori
        if table_category and example['table_code'].startswith(table_category):
            is_similar = True
        
        # 2. Eksplisitt listet som "reusable_for_tables"
        reusable_for = learning.get('learning_outcomes', {}).get('reusable_for_tables', [])
        if table_code in reusable_for:
            is_similar = True
        
        if is_similar:
            similar.append({
                'table_code': example['table_code'],
                'learning': learning,
                'relevance': 'same_category' if table_category in example['table_code'] else 'explicit'
            })
    
    return similar


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


def find_duplicate_column_variants(column_name, columns):
    """
    Finn alle varianter av en kolonne med .1, .2 suffixer.
    
    Args:
        column_name: Base kolonnenavn (f.eks. 'alder')
        columns: Liste av alle kolonner
    
    Returns:
        list: Alle varianter ['alder', 'alder.1', 'alder.2'] som finnes
    """
    variants = []
    
    # Sjekk base-navnet
    if column_name in columns:
        variants.append(column_name)
    
    # Sjekk .1, .2, .3, etc.
    i = 1
    while f"{column_name}.{i}" in columns:
        variants.append(f"{column_name}.{i}")
        i += 1
    
    return variants


def resolve_duplicate_mappings(mappings, output_cols):
    """
    Løs situasjoner der flere input-kolonner mapper til samme output-kolonne.
    Prøv å fordele dem på .1, .2 varianter hvis de finnes.
    
    Args:
        mappings: Dict {input_col: output_col}
        output_cols: Liste av alle output-kolonner
    
    Returns:
        dict: Oppdaterte mappings
    """
    # Finn duplikate mappings (flere inputs → samme output)
    output_usage = {}
    for in_col, out_col in mappings.items():
        if out_col not in output_usage:
            output_usage[out_col] = []
        output_usage[out_col].append(in_col)
    
    # Finn og løs duplikater
    updated_mappings = mappings.copy()
    
    for out_col, in_cols in output_usage.items():
        if len(in_cols) > 1:
            # Flere inputs mapper til samme output
            # Finn alle varianter (.1, .2, etc.)
            variants = find_duplicate_column_variants(out_col, output_cols)
            
            if len(variants) >= len(in_cols):
                # Vi har nok varianter - fordel mappings
                # Sorter input-kolonner for konsistens (kode først, så _fmt)
                in_cols_sorted = sorted(in_cols, key=lambda x: (
                    '_fmt' in x.lower(),  # _fmt-kolonner sist
                    x
                ))
                
                for i, in_col in enumerate(in_cols_sorted):
                    if i < len(variants):
                        updated_mappings[in_col] = variants[i]
    
    return updated_mappings


def identify_common_keys(input_dfs, output_df=None, all_mappings=None):
    """Identifiser felles nøkkelkolonner på tvers av flere input-dataframes.

    VIKTIG: Bruker de foreslåtte standardnavnene fra mappings for å finne
    felles kolonner, siden originale navn kan være forskjellige
    (f.eks. 'arb_gkrets_a' vs 'ny_krets_b' → begge mapper til 'arbeidssted_grunnkrets')

    Heuristikk:
      - Konverter kolonnenavn til standardnavn (via mappings)
      - Finn interseksjon av standardnavn (case-insensitive)
      - Ekskluder åpenbare målekolonner (antall, value, count)
      - Prioriter kolonner som virker kategoriske (dtype ikke float kontinuerlig)
      - Verifiser at nøklene sammen gir unikhet eller nær-unikhet (<5% duplikat)

    Args:
        input_dfs: Liste av DataFrames (med originale kolonnenavn)
        output_df: Valgfri referanse for validering
        all_mappings: Liste av mapping-dicts [{'mappings': {...}}, ...] per input
    Returns:
        dict med 'candidate_keys': liste av standardiserte kolonnenavn
              'key_quality': dict per kolonne med uniqueness-ratio
              'composite_uniqueness': float for samlet nøkkel
              'original_to_standard': dict med mapping per input
    """
    if not input_dfs:
        return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0, 
                'original_to_standard': []}

    # Hvis ingen mappings gitt, fall tilbake til original logikk
    if not all_mappings:
        # Finn interseksjon av originale navn
        lower_sets = [set(c.lower() for c in df.columns) for df in input_dfs]
        common_lower = set.intersection(*lower_sets)
        if not common_lower:
            return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0,
                   'original_to_standard': []}
        
        first_cols_map = {c.lower(): c for c in input_dfs[0].columns}
        common_cols = [first_cols_map[l] for l in common_lower]
    else:
        # NYTT: Bruk standardnavnene fra mappings
        standardized_cols = []
        original_to_standard = []
        
        for i, (df, mapping_info) in enumerate(zip(input_dfs, all_mappings)):
            mapping = mapping_info.get('mappings', {})
            # Konverter alle kolonner til standardnavn (eller behold original hvis ikke mappet)
            std_cols = [mapping.get(col, col) for col in df.columns]
            standardized_cols.append(set(c.lower() for c in std_cols))
            
            # Lagre reverse mapping for denne input-filen
            reverse_map = {std.lower(): orig for orig, std in mapping.items()}
            original_to_standard.append(reverse_map)
        
        # Finn felles standardnavn
        common_lower = set.intersection(*standardized_cols)
        if not common_lower:
            return {'candidate_keys': [], 'key_quality': {}, 'composite_uniqueness': 0.0,
                   'original_to_standard': original_to_standard}
        
        # Bruk standardnavn (ta fra første mapping for konsistent case)
        first_mapping = all_mappings[0].get('mappings', {})
        # Reverse for å finne standardnavn
        std_cols_map = {std.lower(): std for std in first_mapping.values()}
        # Fallback til original hvis ikke funnet
        first_cols_map = {c.lower(): c for c in input_dfs[0].columns}
        common_cols = [std_cols_map.get(l, first_cols_map.get(l, l)) for l in common_lower]

    measure_candidates = {'antall', 'value', 'count', 'beløp', 'sum'}
    filtered = [c for c in common_cols if c.lower() not in measure_candidates]

    # Vurder uniqueness per kolonne (gjør på første DF for hastighet)
    key_quality = {}
    df0 = input_dfs[0]
    
    for std_col in filtered:
        # Finn original kolonnenavn i første DF
        if all_mappings:
            mapping = all_mappings[0].get('mappings', {})
            # Finn original kolonne som mapper til std_col
            orig_col = None
            for orig, std in mapping.items():
                if std.lower() == std_col.lower():
                    orig_col = orig
                    break
            if not orig_col:
                orig_col = std_col  # Fallback
        else:
            orig_col = std_col
        
        if orig_col in df0.columns:
            nunique = df0[orig_col].nunique(dropna=True)
            ratio = nunique / max(len(df0), 1)
            key_quality[std_col] = ratio
        else:
            key_quality[std_col] = 0.0

    # Start med kolonner med ratio > 0.2 (ikke helt lav-kardinalitet)
    candidate = [c for c in filtered if key_quality.get(c, 0) > 0.2]
    if not candidate:
        candidate = filtered  # fall back

    # Test composite uniqueness
    composite_uniqueness = 0.0
    if candidate and all_mappings:
        # Finn originale kolonner for composite test
        mapping = all_mappings[0].get('mappings', {})
        orig_cols = []
        for std_col in candidate:
            for orig, std in mapping.items():
                if std.lower() == std_col.lower():
                    orig_cols.append(orig)
                    break
            else:
                orig_cols.append(std_col)  # Fallback
        
        valid_cols = [c for c in orig_cols if c in df0.columns]
        if valid_cols:
            subset = df0[valid_cols]
            composite_uniqueness = subset.drop_duplicates().shape[0] / max(len(df0), 1)
    elif candidate:
        valid_cols = [c for c in candidate if c in df0.columns]
        if valid_cols:
            subset = df0[valid_cols]
            composite_uniqueness = subset.drop_duplicates().shape[0] / max(len(df0), 1)

    result = {
        'candidate_keys': candidate,
        'key_quality': key_quality,
        'composite_uniqueness': composite_uniqueness
    }
    
    if all_mappings:
        result['original_to_standard'] = original_to_standard
    
    return result


def detect_variable_pairs(df):
    """Finn variabel-par (kode + tekst) som representerer samme konsept.

    Mønster:
      - Kolonnenavn med suffix _fmt
      - Kolonnenavn med .1 variant
      - Kolonnenavn der basekolonnen er numerisk og variant er tekst

    Returnerer liste av dicts:
      {'base': 'alder', 'label': 'alder.1', 'pattern': '.1_variant'}
    """
    cols = df.columns.tolist()
    pairs = []
    used = set()
    for c in cols:
        cl = c.lower()
        # _fmt mønster
        if cl.endswith('_fmt'):
            base = c[:-4]
            if base in df.columns and base not in used and c not in used:
                # Avslappet heuristikk: sjekk en-til-en mellom base og label
                subset = df[[base, c]].dropna().drop_duplicates()
                base_unique = df[base].nunique(dropna=True)
                label_unique = df[c].nunique(dropna=True)
                pair_unique = subset.shape[0]
                # En-til-en hvis alle tre tall er like
                if base_unique == label_unique == pair_unique:
                    pairs.append({'base': base, 'label': c, 'pattern': '_fmt'})
                    used.update({base, c})
                    continue
                # Alternativ: base er numerisk og label er tekst (original betingelse)
                if not pd.api.types.is_string_dtype(df[base]) and pd.api.types.is_string_dtype(df[c]):
                    pairs.append({'base': base, 'label': c, 'pattern': '_fmt'})
                    used.update({base, c})
        # .1 variant
        if c.endswith('.1'):
            base = c[:-2]
            if base in df.columns and base not in used and c not in used:
                subset = df[[base, c]].dropna().drop_duplicates()
                base_unique = df[base].nunique(dropna=True)
                label_unique = df[c].nunique(dropna=True)
                pair_unique = subset.shape[0]
                if base_unique == label_unique == pair_unique:
                    pairs.append({'base': base, 'label': c, 'pattern': '.1_variant'})
                    used.update({base, c})
                    continue
                if not pd.api.types.is_string_dtype(df[base]) and pd.api.types.is_string_dtype(df[c]):
                    pairs.append({'base': base, 'label': c, 'pattern': '.1_variant'})
                    used.update({base, c})
    return pairs


def detect_value_columns(df, variable_pairs=None):
    """
    Detekter statistikkvariable (kolonner som skal summeres ved aggregering).
    
    Identifiserer numeriske kolonner som representerer måltall/verdier,
    og skiller dem fra dimensjonsvariabler (kategoriske kolonner).
    
    Forbedret heuristikk:
    - Kolonnenavn med nøkkelord som indikerer måltall
    - Høy kardinalitet eller stor spredning
    - IKKE år, dato, eller ID-lignende kolonner
    - IKKE base-kolonner i variabel-par (de er dimensjoner)
    
    Args:
        df: DataFrame å analysere
        variable_pairs: Liste av variabel-par (fra detect_variable_pairs)
        
    Returns:
        dict: {
            'value_columns': [kolonnenavn for statistikkvariable],
            'dimension_columns': [kolonnenavn for dimensjonsvariabler],
            'label_columns': [kolonnenavn for label-kolonner]
        }
    """
    # Bygg sett av label-kolonner og base-kolonner fra variable_pairs
    label_cols = set()
    base_cols = set()
    if variable_pairs:
        for pair in variable_pairs:
            label_cols.add(pair['label'])
            base_cols.add(pair['base'])
    
    # Keywords som indikerer måltall (positiv match)
    value_keywords = [
        'antall', 'count', 'value', 'verdi', 'beløp', 'sum', 'total', 
        'inntekt', 'utgift', 'pris', 'kr', 'prosent', 'andel', 'rate',
        'kostnad', 'lønn', 'skatt', 'avgift', 'bestand', 'saldo'
    ]
    
    # Keywords som indikerer dimensjoner (negativ match for value_cols)
    dimension_keywords = [
        'år', 'aar', 'year', 'dato', 'date', 'tid', 'time',
        'id', 'kode', 'code', 'nr', 'nummer', 'number',
        'alder', 'age', 'måned', 'month', 'dag', 'day',
        'uke', 'week', 'kvartal', 'quarter'
    ]
    
    value_columns = []
    dimension_columns = []
    
    n_rows = len(df)
    
    for col in df.columns:
        # Skip label-kolonner
        if col in label_cols:
            continue
        
        col_lower = col.lower()
        
        # Sjekk om kolonnen er numerisk
        if df[col].dtype in ['int64', 'float64', 'int32', 'float32', 'int16', 'float16']:
            nunique = df[col].nunique(dropna=True)
            
            # 1. Sjekk nøkkelord først
            is_value_keyword = any(keyword in col_lower for keyword in value_keywords)
            is_dimension_keyword = any(keyword in col_lower for keyword in dimension_keywords)
            
            # 2. Base-kolonner i variabel-par er dimensjoner
            if col in base_cols:
                dimension_columns.append(col)
                continue
            
            # 3. Eksplisitt value-keyword → value column
            if is_value_keyword and not is_dimension_keyword:
                value_columns.append(col)
                continue
            
            # 4. Eksplisitt dimension-keyword → dimension
            if is_dimension_keyword:
                dimension_columns.append(col)
                continue
            
            # 5. Heuristikk basert på kardinalitet og spredning
            # Lav kardinalitet (< 5% av rader eller < 200 unike) = sannsynligvis dimensjon
            if nunique < max(n_rows * 0.05, 1) or nunique < 200:
                dimension_columns.append(col)
            # Høy kardinalitet = sannsynligvis måltall
            else:
                # Ekstra sjekk: Beregn spredning (coefficient of variation)
                try:
                    mean_val = df[col].mean()
                    std_val = df[col].std()
                    if mean_val > 0:
                        cv = std_val / mean_val
                        # Høy variasjon (CV > 0.5) indikerer måltall
                        if cv > 0.5:
                            value_columns.append(col)
                        else:
                            dimension_columns.append(col)
                    else:
                        value_columns.append(col)
                except:
                    value_columns.append(col)
        
        # Ikke-numeriske kolonner (og ikke labels) = dimensjoner
        elif col not in label_cols:
            dimension_columns.append(col)
    
    return {
        'value_columns': value_columns,
        'dimension_columns': dimension_columns,
        'label_columns': list(label_cols)
    }


def detect_aggregation_patterns(df_input, df_output, mappings):
    """Detekter typiske aggregeringsmønstre mellom input og output.

    Mønstre vi ser etter:
      - Nye kategoriverdier i output som ikke finnes i input (f.eks. kjønn=3 'Begge kjønn')
      - Nye geografiske koder (f.eks. 301 'Oslo i alt') basert på roll-up av mer detaljerte koder
      - Radantall øker signifikant (tyder på union av granular + aggregert nivå)

    Args:
        df_input: Original input DataFrame
        df_output: Output DataFrame (referanse)
        mappings: Dict over kolonne-mappings input->output (etter duplikat-håndtering)

    Returns:
        dict med nøkler:
          'gender_aggregation': info om Begge kjønn
          'geo_rollup': info om Oslo i alt
          'row_expansion': bool om rader øker
          'suggested_operations': liste av operation dicts med 'type', 'description', 'code_snippet'
    """
    results = {
        'gender_aggregation': None,
        'geo_rollup': None,
        'row_expansion': False,
        'suggested_operations': []
    }

    # Try to identify measure column
    measure_cols = [c for c in df_input.columns if c.lower() in ['antall', 'value', 'count']]
    measure_col = measure_cols[0] if measure_cols else None

    # Map input column names to output names for easier reasoning
    reverse_mapping = {v: k for k, v in mappings.items()}

    # Row expansion detection
    if len(df_output) > len(df_input) * 1.05:  # >5% flere rader
        results['row_expansion'] = True

    # Gender aggregation detection
    # Finn kolonner i output som representerer kjønn (kode + navn)
    gender_code_col = None
    gender_name_col = None
    for col in df_output.columns:
        lc = col.lower()
        if lc in ['kjønn', 'kjoenn', 'kjonn'] and df_output[col].dtype != object:
            gender_code_col = col
        elif lc.startswith('kjønn') or lc.startswith('kjoenn'):
            # Pick name column containing strings
            if df_output[col].dtype == object:
                gender_name_col = col
    # Hvis vi finner en kodekolonne og verdier som ikke fantes i input → aggregering
    if gender_code_col and measure_col:
        input_gender_col = None
        # Finn opprinnelig kjønn-kolonne i input
        for k, v in mappings.items():
            if v == gender_code_col:
                input_gender_col = k
                break
        if input_gender_col and input_gender_col in df_input.columns:
            input_gender_values = set(df_input[input_gender_col].dropna().astype(str).unique())
            output_gender_values = set(df_output[gender_code_col].dropna().astype(str).unique())
            new_gender_values = output_gender_values - input_gender_values
            # Typisk '3' for Begge kjønn
            if any(val in new_gender_values for val in ['3', '9']):
                # Verifiser at antall for ny kategori ≈ sum av underkategorier
                sample = df_output[df_output[gender_code_col].astype(str).isin(list(new_gender_values))]
                # Begrens test for ytelse
                sample_rows = sample.head(25)
                plausible = True if len(sample_rows) > 0 else False
                if plausible:
                    results['gender_aggregation'] = {
                        'new_values': list(new_gender_values),
                        'code_col': gender_code_col,
                        'name_col': gender_name_col,
                        'description': 'Ny kjønnskategori (f.eks. Begge kjønn) indikert som aggregert fra underkategorier.'
                    }
                    code_snippet = f"""# AGGREGERING: Legg til 'Begge kjønn'
df_begge = df_input.groupby(['år', '{mappings.get('bydel2','bosted')}', '{mappings.get('alderu','alder')}']).agg({{'{measure_col}':'sum'}}).reset_index()
df_begge['{gender_code_col}'] = 3
df_begge['{gender_name_col}'] = 'Begge kjønn'
# df_final = pd.concat([df_final, df_begge], ignore_index=True)"""
                    results['suggested_operations'].append({
                        'type': 'gender_aggregation',
                        'description': 'Legg til aggregert kjønnskategori (Begge kjønn).',
                        'code_snippet': code_snippet
                    })

    # Geographic roll-up detection (Oslo i alt)
    geo_col = None
    geo_name_col = None
    # Heuristisk: kolonner med navn 'bosted', 'geografi', 'bydel'
    for col in df_output.columns:
        lc = col.lower()
        if lc in ['bosted', 'geografi', 'bydel'] and df_output[col].dtype != object:
            geo_col = col
        elif (lc in ['bosted', 'geografi', 'bydel'] or lc.startswith('bosted') or lc.startswith('geografi')) and df_output[col].dtype == object:
            geo_name_col = col
    if geo_col and measure_col and geo_col in df_output.columns:
        # Finn opprinnelig geo-kolonne i input
        input_geo_col = None
        for k, v in mappings.items():
            if v == geo_col:
                input_geo_col = k
                break
        if input_geo_col and input_geo_col in df_input.columns:
            input_geo_values = set(df_input[input_geo_col].dropna().astype(str).unique())
            output_geo_values = set(df_output[geo_col].dropna().astype(str).unique())
            new_geo_values = output_geo_values - input_geo_values
            # Oslo i alt typisk '301' når input har '30101' etc.
            oslo_candidates = [val for val in new_geo_values if len(val) <= 3]
            if oslo_candidates:
                results['geo_rollup'] = {
                    'new_values': oslo_candidates,
                    'code_col': geo_col,
                    'name_col': geo_name_col,
                    'description': 'Ny geografisk kode (kommune-nivå) indikert som aggregert fra bydeler.'
                }
                code_snippet = f"""# AGGREGERING: Legg til 'Oslo i alt'
df_oslo = df_input.groupby(['år', '{mappings.get('kjoenn','kjønn')}', '{mappings.get('alderu','alder')}']).agg({{'{measure_col}':'sum'}}).reset_index()
df_oslo['{geo_col}'] = 301
df_oslo['{geo_name_col}'] = '0301 Oslo i alt'
# df_final = pd.concat([df_final, df_oslo], ignore_index=True)"""
                results['suggested_operations'].append({
                    'type': 'geo_rollup',
                    'description': 'Legg til aggregert geografisk nivå (Oslo i alt).',
                    'code_snippet': code_snippet
                })

    return results


def detect_aggregation_patterns_v2(df_input, df_output, mappings):
    """
    Navne-uavhengig aggregeringsdeteksjon (forbedret versjon).
    
    Bruker mappings fra kolonnemapping i stedet for fuzzy matching.
    Klassifiserer basert på verdimønstre, ikke kolonnenavn.
    
    Args:
        df_input: Input DataFrame
        df_output: Output DataFrame  
        mappings: Dict {input_col: output_col}
    
    Returns:
        dict: {'aggregations': [{'column': ..., 'type': ..., ...}, ...]}
    """
    aggregations = []
    
    # Bruk mappings direkte - NAVNE-UAVHENGIG!
    for col_in, col_out in mappings.items():
        # Skip label-kolonner
        if col_in.endswith('_fmt') or '.1' in col_out or '.2' in col_out:
            continue
        
        # Kun kolonner med lav kardinalitet
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


def find_column_mapping_with_codelists(df_input, df_output, codelist_manager, 
                                      kontrollskjema=None, table_code=None, similarity_threshold=0.6,
                                      known_pairs=None):
    """
    Finn kolonnemappings mellom input og output, med kodeliste-støtte og standardisering.
    
    Args:
        df_input: Input DataFrame
        df_output: Output DataFrame
        codelist_manager: CodelistManager instans
        kontrollskjema: Kontrollskjema dict
        table_code: Tabellkode for kontekstuell forståelse (f.eks. OK-BEF001)
        similarity_threshold: Minimum likhet for matching (0-1)
        known_pairs: Liste av variabel-par dicts [{'base': 'bydel', 'label': 'bydel_fmt'}, ...]
                     Brukes for å unngå å mappe begge kolonner i et par
    """
    input_cols = df_input.columns.tolist()
    output_cols = df_output.columns.tolist()
    
    mappings = {}
    value_transformations = {}  # Kodeliste-transformasjoner
    standardization_suggestions = {}  # Forslag til standardisering
    geographic_suggestions = {}  # Forslag til geografiske kolonner
    used_output_cols = set()
    
    # Bygg sett av label-kolonner fra known_pairs for å hoppe over dem i første runde
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
            # Hopp over label-kolonner i første runde (de mappes via base-kolonnen)
            if in_col in skip_label_cols:
                continue
                
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
        # Hopp over label-kolonner og allerede mappede kolonner
        if in_col in skip_label_cols or in_col in mappings:
            continue
            
        in_col_clean = in_col.lower().strip().replace(' ', '').replace('_', '')
        for out_col in output_cols:
            out_col_clean = out_col.lower().strip().replace(' ', '').replace('_', '')
            if in_col_clean == out_col_clean and out_col not in used_output_cols:
                mappings[in_col] = out_col
                used_output_cols.add(out_col)
                break
    
    # 2. Sjekk kodelister for ALLE kolonner (inkludert allerede mappede)
    # Dette er viktig fordi kolonnenavn kan matche, men verdier trenger transformasjon
    # Eksempel: bydel2 → bosted (navn matcher via kontrollskjema, men verdier trenger SSB→PX kodeliste)
    for in_col in input_cols:
        # Finn ut-kolonne (enten allerede mappet eller søk)
        out_col = mappings.get(in_col)
        
        if out_col:
            # Allerede mappet - sjekk om verdiene trenger kodeliste-transformasjon
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
            # Ikke mappet ennå - søk etter kodeliste-basert mapping
            in_values = set(df_input[in_col].dropna().astype(str).unique()[:100])
            
            for out_col_candidate in output_cols:
                if out_col_candidate in used_output_cols:
                    continue
                
                out_values = set(df_output[out_col_candidate].dropna().astype(str).unique()[:100])
                
                # Finn matching kodeliste
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
    
    # 5. Løs duplikate mappings (flere inputs → samme output)
    # Dette håndterer situasjoner som: alderu → alder, alderu_fmt → alder
    # Når output har både 'alder' og 'alder.1'
    mappings = resolve_duplicate_mappings(mappings, output_cols)
    
    # Oppdater used_output_cols basert på nye mappings
    used_output_cols = set(mappings.values())
    
    # 6. Mapper label-kolonner basert på known_pairs
    # Nå som base-kolonner er mappet, kan vi mappe label-kolonner
    if known_pairs:
        for pair in known_pairs:
            base_col = pair['base']
            label_col = pair['label']
            
            # Hvis base er mappet, prøv å mappe label til tilsvarende _fmt kolonne
            if base_col in mappings:
                base_mapped = mappings[base_col]
                # Søk etter output-kolonne med samme navn + _fmt eller _navn suffix
                potential_labels = [
                    base_mapped + '_fmt',
                    base_mapped + '_navn',
                    base_mapped.replace('_', '') + '_fmt',
                    base_mapped.replace('_', '') + '_navn'
                ]
                
                for potential_label in potential_labels:
                    if potential_label in output_cols and potential_label not in used_output_cols:
                        mappings[label_col] = potential_label
                        used_output_cols.add(potential_label)
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


def simulate_merge(input_dfs):
    """
    Simuler merge av multiple input DataFrames for å få merged struktur.
    
    Strategi:
    1. Finn felles kolonner (potensielle merge-nøkler)
    2. Hvis felles kolonner: outer join
    3. Hvis ingen felles: concat (union)
    
    Args:
        input_dfs: List av input DataFrames
    
    Returns:
        df_merged: Simulert merged DataFrame (tomme verdier ok, bare struktur matters)
    """
    if len(input_dfs) == 1:
        return input_dfs[0].copy()
    
    # Normaliser kolonnenavn til lowercase for sammenligning
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
        # Merge strategi: outer join på felles kolonner
        print(f"  Simulerer MERGE på felles kolonner: {common_cols}")
        df_merged = normalized_dfs[0]
        for df in normalized_dfs[1:]:
            df_merged = df_merged.merge(df, on=common_cols, how='outer', suffixes=('', '_dup'))
        
        # Fjern duplikat-kolonner (fra suffixes)
        df_merged = df_merged[[col for col in df_merged.columns if not col.endswith('_dup')]]
    else:
        # Concat strategi: union (alle kolonner fra alle inputs)
        print(f"  Simulerer UNION (ingen felles kolonner)")
        df_merged = pd.concat(normalized_dfs, ignore_index=True, sort=False)
    
    return df_merged


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
    
    # STEG 1: Les input-filer med encoding/normalisering
    print("=== STEG 1: Les og ENCODE input-filer ===")
    input_dfs = []
    for i, input_file in enumerate(input_files):
        sheet = input_sheets[i] if input_sheets and i < len(input_sheets) else 0
        df = pd.read_excel(input_file, sheet_name=sheet)
        
        # Lowercase kolonnenavn
        df.columns = df.columns.str.lower().str.strip()
        
        # Simuler XML-dekoding (whitespace normalisering)
        # Dette er kritisk for merge-matching!
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.replace(' -', '-').str.replace('  ', ' ').str.strip()
        
        input_dfs.append(df)
        print(f"Input fil {i+1}: {input_file}")
        print(f"  Kolonner: {df.columns.tolist()}")
        print(f"  Rader: {len(df)}\n")
    
    # Les output-fil
    df_output = pd.read_excel(output_file, sheet_name=output_sheet or 0)
    print(f"Output fil: {output_file}")
    print(f"  Kolonner: {df_output.columns.tolist()}")
    print(f"  Rader: {len(df_output)}\n")
    
    # STEG 2: MERGE hvis multi-input (eller bruk single input direkte)
    print("=== STEG 2: MERGE (hvis multi-input) ===")
    if len(input_dfs) > 1:
        # Multi-input: simuler merge for analyse
        analysis_df = simulate_merge(input_dfs)
        print(f"✅ Merged {len(input_dfs)} inputs → {len(analysis_df)} rader")
        print(f"   Merged kolonner: {analysis_df.columns.tolist()}\n")
        is_multi_input = True
    else:
        # Single-input: analyser direkte
        analysis_df = input_dfs[0].copy()
        print(f"Single-input tabell: Analyserer direkte\n")
        is_multi_input = False
    
    # STEG 3: Variabel-par og statistikkvariabel-deteksjon (på merged/single input)
    print("=== STEG 3: Variabel-par og statistikkvariabel-deteksjon ===")
    variable_pairs_all = []
    value_columns_all = []
    
    if is_multi_input:
        # For multi-input: analyser merged df
        pairs = detect_variable_pairs(analysis_df)
        value_info = detect_value_columns(analysis_df, pairs)
        
        # Lagre samme info for alle inputs (brukes av template-generator)
        for i in range(len(input_dfs)):
            variable_pairs_all.append(pairs)
            value_columns_all.append(value_info)
        
        print(f"=== Merged DataFrame ===")
        if pairs:
            print(f"Variabel-par funnet:")
            for p in pairs:
                print(f"  - {p['base']} / {p['label']} ({p['pattern']})")
        else:
            print(f"Ingen variabel-par funnet")
        
        print(f"\nStatistikkvariable (skal summeres):")
        for col in value_info['value_columns']:
            print(f"  - {col}")
        
        print(f"\nDimensjonsvariabler (kategoriske):")
        for col in value_info['dimension_columns'][:5]:
            print(f"  - {col}")
        if len(value_info['dimension_columns']) > 5:
            print(f"  ... og {len(value_info['dimension_columns']) - 5} til")
        print()
    else:
        # For single-input: analyser som før
        for i, df_in in enumerate(input_dfs, 1):
            pairs = detect_variable_pairs(df_in)
            variable_pairs_all.append(pairs)
            
            value_info = detect_value_columns(df_in, pairs)
            value_columns_all.append(value_info)
            
            print(f"=== Input {i} ===")
            if pairs:
                print(f"Variabel-par funnet:")
                for p in pairs:
                    print(f"  - {p['base']} / {p['label']} ({p['pattern']})")
            else:
                print(f"Ingen variabel-par funnet")
            
            print(f"\nStatistikkvariable (skal summeres):")
            for col in value_info['value_columns']:
                print(f"  - {col}")
            
            print(f"\nDimensjonsvariabler (kategoriske):")
            for col in value_info['dimension_columns'][:5]:
                print(f"  - {col}")
            if len(value_info['dimension_columns']) > 5:
                print(f"  ... og {len(value_info['dimension_columns']) - 5} til")
            print()
    
    # STEG 4: Kolonnemapping (analysis_df → output)
    print("=== STEG 4: Kolonnemapping ===")
    all_mappings = []
    all_transformations = []
    all_standardizations = []
    all_geographic_suggestions = []
    
    if is_multi_input:
        # Multi-input: map merged df → output
        result = find_column_mapping_with_codelists(
            analysis_df, df_output, codelist_mgr, kontrollskjema, table_code,
            known_pairs=variable_pairs_all[0]
        )
        
        # Lagre samme mapping for alle inputs (brukes av template-generator)
        for i in range(len(input_dfs)):
            all_mappings.append({
                'file_index': i,
                'mappings': result['mappings'],
                'unmapped_input': result['unmapped_input'],
                'unmapped_output': result['unmapped_output']
            })
            all_transformations.append(result['value_transformations'])
            all_standardizations.append(result['standardization_suggestions'])
            all_geographic_suggestions.append(result['geographic_suggestions'])
        
        print(f"=== Merged DataFrame → Output ===")
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
    else:
        # Single-input: map hver input → output (som før)
        for i, df_input in enumerate(input_dfs):
            result = find_column_mapping_with_codelists(
                df_input, df_output, codelist_mgr, kontrollskjema, table_code,
                known_pairs=variable_pairs_all[i]
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

    # STEG 5: Multi-input nøkkelanalyse (hvis relevant)
    print("=== STEG 5: Multi-input nøkkelanalyse ===")
    if is_multi_input:
        # VIKTIG: Analyser ORIGINAL input-filer for felles nøkler (ikke merged!)
        # Vi trenger å vite hvilke kolonner er felles for merge-operasjonen
        common_keys_info = identify_common_keys(input_dfs, df_output, all_mappings)
        print(f"Foreslåtte felles nøkkelkolonner (standardnavn): {common_keys_info['candidate_keys']}")
        print(f"Unikhetsratio per kolonne: {common_keys_info['key_quality']}")
        print(f"Kompositt unikhet (approx): {common_keys_info['composite_uniqueness']:.3f}\n")
    else:
        common_keys_info = None
        print("Single-input: Ingen nøkkelanalyse nødvendig\n")

    # STEG 6: Aggregeringsanalyse (analysis_df → output)
    print("=== STEG 6: Aggregeringsanalyse ===")
    aggregation_insights = []
    
    try:
        # Bruk den forbedrede interne versjonen på analysis_df (merged eller single)
        agg_result = detect_aggregation_patterns_v2(
            analysis_df, df_output, all_mappings[0]['mappings']
        )
        aggregation_insights.append(agg_result)
        
        if agg_result['aggregations']:
            print("🔍 Oppdaget aggregeringsmønstre (navne-uavhengig deteksjon):")
            for agg in agg_result['aggregations']:
                print(f"  - {agg['description']}")
                print(f"    {agg['input_column']} → {agg['column']}: nye verdier {agg['new_values']}")
    except Exception as e:
        print(f"⚠️  Kunne ikke kjøre v2-aggregering: {e}")
        # Fallback til gammel metode
        try:
            agg_result = detect_aggregation_patterns(
                analysis_df, df_output, all_mappings[0]['mappings']
            )
            aggregation_insights.append(agg_result)
            if agg_result['suggested_operations']:
                print("🔍 Oppdaget mulige aggregeringsmønstre (fallback):")
                for op in agg_result['suggested_operations']:
                    print(f"  - {op['description']}")
        except Exception as e2:
            print(f"⚠️  Aggregeringsanalyse feilet helt: {e2}")
            aggregation_insights.append({'aggregations': []})
    
    # Generer script
    script_name = f"{table_code}_prep.py"
    
    script_content = generate_script_content_multi_input(
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
    print(f"3. Lagre korrekt versjon i training_data/{table_code}/")


def generate_script_content_multi_input(input_files, all_mappings, 
                                       all_transformations, all_geographic_suggestions,
                                       aggregation_insights, output_columns, table_code,
                                       common_keys_info=None, variable_pairs_all=None,
                                       value_columns_all=None):
    """Generer selve Python-scriptet for multi-input transformasjon.

    Args:
        input_files: Liste av input filstier
        all_mappings: Liste med mapping-info per input
        all_transformations: Liste med kodeliste-transformasjoner per input
        all_geographic_suggestions: Liste med geografiske forslag per input
        aggregation_insights: Liste med aggregeringsinfo
        output_columns: Output kolonne-navn
        table_code: Tabellkode
        common_keys_info: Info om felles nøkler for merge (valgfri)
        variable_pairs_all: Liste av variabel-par per input (valgfri)
        value_columns_all: Liste av statistikkvariabel-info per input (valgfri)
    """
    
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

    # Samle aggregeringsforslag (fra forbedret navne-uavhengig deteksjon)
    agg_comment_lines = []
    if aggregation_insights:
        for insight in aggregation_insights:
            # Nytt format: {'aggregations': [...]}
            aggregations = insight.get('aggregations', [])
            
            # Gammel format fallback: {'suggested_operations': [...]}
            old_ops = insight.get('suggested_operations', [])
            
            if aggregations:
                agg_comment_lines.append("\nOppdagede AGGREGERINGS-operasjoner (navne-uavhengig deteksjon):")
                for agg in aggregations:
                    desc = agg.get('description', 'Ukjent aggregering')
                    col_in = agg.get('input_column', '?')
                    col_out = agg.get('column', '?')
                    new_vals = agg.get('new_values', [])
                    agg_type = agg.get('type', 'other')
                    
                    agg_comment_lines.append(f"  - {desc}")
                    agg_comment_lines.append(f"    Kolonne: {col_in} → {col_out}")
                    agg_comment_lines.append(f"    Nye verdier: {new_vals}")
                    agg_comment_lines.append(f"    Type: {agg_type}")
                    
                    # TODO: Generer konkret kode basert på type
                    if agg_type == 'binary_total':
                        agg_comment_lines.append("    # Foreslått kode:")
                        agg_comment_lines.append(f"    # df_total = df.groupby([group_cols]).agg({{'antall': 'sum'}}).reset_index()")
                        agg_comment_lines.append(f"    # df_total['{col_out}'] = {new_vals[0]}  # Total-kategori")
                        agg_comment_lines.append(f"    # df_final = pd.concat([df_final, df_total], ignore_index=True)")
                    
                    elif agg_type == 'geography_rollup':
                        agg_comment_lines.append("    # Foreslått kode:")
                        agg_comment_lines.append(f"    # df_total = df.groupby([other_dims]).agg({{'antall': 'sum'}}).reset_index()")
                        agg_comment_lines.append(f"    # df_total['{col_out}'] = {new_vals[0]}  # Oslo i alt")
                        agg_comment_lines.append(f"    # df_final = pd.concat([df_final, df_total], ignore_index=True)")
            
            elif old_ops:
                # Fallback til gammelt format
                agg_comment_lines.append("\nOppdagede mulige AGGREGERINGS-operasjoner:")
                for op in old_ops:
                    desc = op.get('description', 'Ingen beskrivelse')
                    snippet = op.get('code_snippet', '').strip()
                    agg_comment_lines.append(f"  - {desc}")
                    if snippet:
                        commented_snippet = '\n'.join([f"    # {line}" if line.strip() else "" for line in snippet.split('\n')])
                        agg_comment_lines.append("    # Forslag til kode:")
                        agg_comment_lines.append(commented_snippet)

    aggregation_comment_block = "\n".join(agg_comment_lines) if agg_comment_lines else ""

    # Bygg kommentarblokker for felles nøkler og variabel-par
    common_keys_block = ""
    if common_keys_info is not None:
        ck = common_keys_info.get('candidate_keys', [])
        uq = common_keys_info.get('composite_uniqueness', 0.0)
        key_quality = common_keys_info.get('key_quality', {})
        if ck:
            quality_lines = [f"    - {k}: uniqueness={key_quality.get(k,0):.3f}" for k in ck]
            common_keys_block = (
                "\nMULTI-INPUT NØKLER:\n" +
                f"  Felles nøkkelkolonner (foreslått): {ck}\n" +
                f"  Kompositt unikhet (≈): {uq:.3f}\n" +
                "  Kolonnekvalitet:\n" +
                "\n".join(quality_lines)
            )
        else:
            common_keys_block = "\nMULTI-INPUT NØKLER:\n  Ingen felles kolonner identifisert automatisk – vurder manuelt."

    variable_pairs_block = ""
    if variable_pairs_all is not None:
        lines = []
        for i, pairs in enumerate(variable_pairs_all, 1):
            if not pairs:
                lines.append(f"  Input {i}: Ingen variabel-par funnet")
            else:
                lines.append(f"  Input {i}:")
                for p in pairs:
                    lines.append(f"    - base={p['base']} label={p['label']} pattern={p['pattern']}")
        variable_pairs_block = "\nVARIABEL-PAR (kode+tekst):\n" + "\n".join(lines)

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
{aggregation_comment_block}
{common_keys_block}
{variable_pairs_block}
"""

import pandas as pd
import sys
import io
from pathlib import Path

# Sikre UTF-8 encoding for print-statements
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def normalize_column_names(df):
    """
    Normaliser kolonnenavn til lowercase for å unngå case-sensitivity problemer.
    Eksempel: 'KJOENN' → 'kjoenn', 'Aargang' → 'aargang'
    """
    df.columns = df.columns.str.lower()
    return df


def decode_xml_strings(df):
    """
    Dekoder XML-encoded strings i Excel-filer.
    Eksempel: '_x0032_025' → '2025', '_x0031_5-24_x0020_år' → '15-24 år'
    
    Normaliserer også whitespace for å unngå match-problemer.
    """
    import re
    
    def decode_string(val):
        if not isinstance(val, str):
            return val
        # Regex: _x[4-digit hex]_ → tilsvarende Unicode-tegn
        decoded = re.sub(r'_x([0-9A-Fa-f]{{4}})_', lambda m: chr(int(m.group(1), 16)), val)
        # Normaliser whitespace (fjern doble mellomrom, ' -' → '-')
        decoded = ' '.join(decoded.split())
        decoded = decoded.replace(' -', '-')
        return decoded
    
    for col in df.columns:
        if df[col].dtype == 'object':  # Kun tekstkolonner
            df[col] = df[col].apply(decode_string)
    
    return df


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
    
    # Les input-filer og normaliser kolonnenavn
    for i in range(num_inputs):
        script += f'''    # Les input fil {i+1}
    print(f"Leser {{input_file{i+1}}}...")
    df{i+1} = pd.read_excel(input_file{i+1})
    df{i+1} = normalize_column_names(df{i+1})  # Normaliser til lowercase
    df{i+1} = decode_xml_strings(df{i+1})  # Dekoder XML-encoding
    print(f"  {{len(df{i+1})}} rader, {{len(df{i+1}.columns)}} kolonner")
    
'''
    
    # Generer transformasjonslogikk for hver fil
    # VIKTIG: Behold originale kolonnenavn til SLUTTEN
    # All transformasjonslogikk bruker originale navn
    for i, mapping_info in enumerate(all_mappings, 1):
        mappings = mapping_info['mappings']
        transformations = all_transformations[i-1]
        
        # Konverter mappings til lowercase (siden vi normaliserer kolonnenavn til lowercase)
        mappings_lower = {k.lower(): v for k, v in mappings.items()}
        
        script += f'''    # Input {i}: Behold originale kolonnenavn (transformeres senere)
    df{i}_transformed = df{i}.copy()
    
'''
        
        # Kodeliste-transformasjoner (på originale kolonnenavn!)
        for in_col, trans_info in transformations.items():
            codelist_name = trans_info['codelist']
            target_col = trans_info['target_col']
            
            # Verifiser at kodeliste-navnet er riktig format (case-insensitive)
            codelist_lower = codelist_name.lower()
            if not codelist_lower.startswith('ssb_til_px') and not codelist_lower.startswith('nav_tknr'):
                # Skip kodelister med feil navn (f.eks. 'geo_bydel')
                continue
            
            # Bruk ORIGINAL kolonnenavn i transformasjonen
            in_col_lower = in_col.lower()
            
            # Spesialhåndtering for NAV_TKNR (krever to output-kolonner)
            if codelist_lower.startswith('nav_tknr'):
                script += f'''    # TKNR-mapping fra kodeliste {codelist_name}
    if '{codelist_name}' in codelists:
        tknr_to_ssb = {{int(k): int(v) for k, v in codelists['{codelist_name}']['mappings']['tknr_to_ssb'].items()}}
        tknr_to_px = codelists['{codelist_name}']['mappings']['tknr_to_px']
        labels = codelists['{codelist_name}']['labels']
        
        # Bygg label-mapping: TKNR → bydelsnavn
        tknr_to_label = {{int(tknr): labels[px_code] for tknr, px_code in tknr_to_px.items()}}
        
        # Opprett to kolonner: geografi (SSB 5-sifret) og geografi_ (navn)
        # Finn output-kolonnenavn fra mapping
        # TODO: Oppdater med faktiske output-kolonnenavn fra mappings
        df{i}_transformed['geografi'] = df{i}_transformed['{in_col_lower}'].map(tknr_to_ssb)
        df{i}_transformed['geografi_'] = df{i}_transformed['{in_col_lower}'].map(tknr_to_label)
    else:
        print("⚠️  Kunne ikke mappe TKNR - kodeliste mangler")
    
'''
            else:
                # Vanlig kodeliste-transformasjon
                script += f'''    # Transformer '{in_col_lower}' med kodeliste {codelist_name}
    if '{codelist_name}' in codelists:
        codelist = codelists['{codelist_name}']
        mapping = codelist.get('mappings', {{}})
        
        # TODO: Bruk kodeliste for å transformere verdier
        # df{i}_transformed['{in_col_lower}'] = df{i}_transformed['{in_col_lower}'].astype(str).map(mapping)
        
        # Legg til labels hvis nødvendig
        # labels = codelist.get('labels', {{}})
        # df{i}_transformed['{in_col_lower}_navn'] = df{i}_transformed['{in_col_lower}'].map(labels)
    
'''
    
    script += f'''    
    # MULTI-INPUT FUSJON / UNION
    # Hvis flere input-filer: bygg union/merge basert på felles nøkkelkolonner.
    # VIKTIG: Bruker originale kolonnenavn i merge!
    '''
    
    if num_inputs > 1:
        # Hent foreslåtte felles nøkler fra ORIGINAL kolonnenavn
        # Må konvertere tilbake fra standardnavn til originale navn
        common_keys_orig = []
        if common_keys_info and common_keys_info.get('candidate_keys'):
            std_keys = common_keys_info.get('candidate_keys')
            # Reverser mappings for å finne originale kolonnenavn
            reverse_mappings = []
            for mapping_info in all_mappings:
                mappings = mapping_info['mappings']
                mappings_lower = {k.lower(): v.lower() for k, v in mappings.items()}
                reverse = {v: k for k, v in mappings_lower.items()}
                reverse_mappings.append(reverse)
            
            # Finn originale navn som mapper til standard-nøklene
            for std_key in std_keys:
                std_key_lower = std_key.lower()
                # Sjekk om dette er et mappet navn
                if std_key_lower in reverse_mappings[0]:
                    common_keys_orig.append(reverse_mappings[0][std_key_lower])
                else:
                    # Hvis ikke mappet, bruk som det er
                    common_keys_orig.append(std_key_lower)
        
        script += "\n    # Foreslåtte felles nøkkelkolonner (originale navn): " + str(common_keys_orig) + "\n"
        script += "    if not " + str(common_keys_orig) + ":\n"
        script += "        print(\"⚠️ Ingen automatiske felles nøkler funnet – vurder manuell merge.\")\n"
        script += "    else:\n"
        script += "        # Verifiser tilstedeværelse i alle datasett\n"
        for i in range(1, num_inputs+1):
            script += f"        missing_{i} = [k for k in {common_keys_orig} if k not in df{i}_transformed.columns]\n"
            script += f"        if missing_{i}: print(\"⚠️ Input {i} mangler kolonner:\", missing_{i})\n"
        # Start med første dataframe
        script += "        df_merged = df1_transformed.copy()\n"
        for i in range(2, num_inputs+1):
            script += f"        df_merged = df_merged.merge(df{i}_transformed, on={common_keys_orig}, how='outer')\n"
        script += "\n        # Hvis duplikater oppstår (samme nøkkel flere ganger), aggreger målekolonner ved sum\n"
        script += "        measure_cols = [c for c in df_merged.columns if c.lower() in ['antall','value','count','sysselsatte','befolkning']]\n"
        script += "        if df_merged.shape[0] > df_merged.drop_duplicates(subset=" + str(common_keys_orig) + ").shape[0]:\n"
        script += "            df_merged = df_merged.groupby(" + str(common_keys_orig) + ", dropna=False)[measure_cols].sum().reset_index()\n"
        script += "\n        # Sett df_final til merged resultat\n        df_final_candidate = df_merged\n"
    else:
        script += "\n    # Enkelt input – df_final_candidate settes til første transformerte dataframe\n"
        script += "    df_final_candidate = df1_transformed\n"
    
    # AGGREGERINGER - Generer kode som bruker aggregering.py modulen
    # VIKTIG: Aggregering bruker ORIGINALE kolonnenavn!
    if aggregation_insights and aggregation_insights[0].get('aggregations'):
        script += "\n    # AGGREGERINGER - Legg til totalkategorier (på originale kolonnenavn)\n"
        script += "    from aggregering import apply_aggregeringer\n\n"
        script += "    aggregeringer = [\n"
        
        # Må mappe tilbake fra output-kolonnenavn til originale kolonnenavn
        # Reverser mappings
        all_mappings_lower = {}
        for mapping_info in all_mappings:
            mappings = mapping_info['mappings']
            all_mappings_lower.update({v.lower(): k.lower() for k, v in mappings.items()})
        
        for agg in aggregation_insights[0]['aggregations']:
            col_out = agg['column']  # Dette er output-kolonnenavn
            input_col = agg.get('input_column', col_out)  # Originalt input-kolonnenavn
            new_vals = agg['new_values']
            agg_type = agg['type']
            
            # Bruk input_column hvis tilgjengelig, ellers prøv å reverse-mappe
            if input_col == col_out and col_out.lower() in all_mappings_lower:
                col_to_use = all_mappings_lower[col_out.lower()]
            else:
                col_to_use = input_col.lower()
            
            # Finn label basert på type og kolonnenavn
            label_col = col_out + '.1'
            if label_col in output_columns:
                if 'kjønn' in col_out.lower() or 'kjonn' in col_out.lower():
                    label = 'Begge kjønn'
                elif new_vals[0] in ['301', '0301']:
                    label = '0301 Oslo'
                else:
                    label = 'Total'
            else:
                label = 'Total'
            
            # Formater total_verdi basert på type
            total_val = new_vals[0]
            if isinstance(total_val, str):
                total_val_formatted = f"'{total_val}'"
            else:
                total_val_formatted = str(total_val)
            
            script += f"        {{\n"
            script += f"            'kolonne': '{col_to_use}',\n"
            script += f"            'type': '{agg_type}',\n"
            script += f"            'total_verdi': {total_val_formatted},\n"
            script += f"            'total_label': '{label}'\n"
            script += f"        }},\n"
        
        script += "    ]\n\n"
        
        # Generer kommentar med forklaring
        script += "    # Utfør aggregeringer (auto-detekterer value_columns)\n"
        script += "    df_final = apply_aggregeringer(df_final_candidate, aggregeringer)\n\n"
    else:
        script += "\n    # Ingen aggregeringer detektert\n"
        script += "    df_final = df_final_candidate\n\n"
    
    # SIST: Rename kolonner til output-navn og velg kolonner
    script += "    # SIST: Rename kolonner til output-format\n"
    script += "    # Bygg rename-mapping fra alle inputs\n"
    script += "    final_rename = {}\n"
    for mapping_info in all_mappings:
        mappings = mapping_info['mappings']
        mappings_lower = {k.lower(): v for k, v in mappings.items()}
        script += "    final_rename.update({\n"
        for orig, output in mappings_lower.items():
            script += f"        '{orig}': '{output}',\n"
        script += "    })\n"
    
    script += "\n    # Rename kun kolonner som faktisk eksisterer\n"
    script += "    rename_dict = {k: v for k, v in final_rename.items() if k in df_final.columns}\n"
    script += "    df_final = df_final.rename(columns=rename_dict)\n\n"
    
    script += f'''    # Velg og sorter output-kolonner
    output_columns = {output_columns}
    
    # Fjern kolonner som ikke finnes i df_final
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
