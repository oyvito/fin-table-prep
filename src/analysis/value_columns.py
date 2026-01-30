"""
Deteksjon av statistikkvariable (value columns) vs dimensjonsvariabler.

Statistikkvariable er kolonner som inneholder måltall som skal summeres
ved aggregering (f.eks. 'antall', 'beløp', 'sysselsatte').

Dimensjonsvariabler er kategoriske kolonner som definerer grupper
(f.eks. 'år', 'kjønn', 'bydel').
"""

import pandas as pd


# Keywords som indikerer måltall (positiv match)
VALUE_KEYWORDS = [
    'antall', 'count', 'value', 'verdi', 'beløp', 'sum', 'total', 
    'inntekt', 'utgift', 'pris', 'kr', 'prosent', 'andel', 'rate',
    'kostnad', 'lønn', 'skatt', 'avgift', 'bestand', 'saldo'
]

# Keywords som indikerer dimensjoner (negativ match for value_cols)
DIMENSION_KEYWORDS = [
    'år', 'aar', 'year', 'dato', 'date', 'tid', 'time',
    'id', 'kode', 'code', 'nr', 'nummer', 'number',
    'alder', 'age', 'måned', 'month', 'dag', 'day',
    'uke', 'week', 'kvartal', 'quarter'
]


def detect_value_columns(df: pd.DataFrame, variable_pairs: list[dict] = None) -> dict:
    """
    Detekter statistikkvariable (kolonner som skal summeres ved aggregering).
    
    Skiller mellom:
    - Value columns: Måltall som summeres (antall, beløp, etc.)
    - Dimension columns: Kategoriske variabler for gruppering
    - Label columns: Tekstkolonner som hører til variabel-par
    
    Args:
        df: DataFrame å analysere
        variable_pairs: Liste av variabel-par (fra detect_variable_pairs)
        
    Returns:
        dict med:
            - 'value_columns': [kolonnenavn for statistikkvariable]
            - 'dimension_columns': [kolonnenavn for dimensjonsvariabler]
            - 'label_columns': [kolonnenavn for label-kolonner]
    
    Example:
        >>> df = pd.DataFrame({
        ...     'år': [2024, 2024],
        ...     'kjønn': [1, 2],
        ...     'antall': [100, 200]
        ... })
        >>> result = detect_value_columns(df)
        >>> result['value_columns']
        ['antall']
    """
    # Bygg sett av label-kolonner og base-kolonner fra variable_pairs
    label_cols = set()
    base_cols = set()
    if variable_pairs:
        for pair in variable_pairs:
            label_cols.add(pair['label'])
            base_cols.add(pair['base'])
    
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
            is_value_keyword = any(keyword in col_lower for keyword in VALUE_KEYWORDS)
            is_dimension_keyword = any(keyword in col_lower for keyword in DIMENSION_KEYWORDS)
            
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
            else:
                # Høy kardinalitet - sjekk coefficient of variation
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
