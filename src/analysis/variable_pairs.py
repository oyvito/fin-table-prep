"""
Deteksjon av variabel-par (kode + tekst) i DataFrames.

Variabel-par er kolonner som representerer samme konsept i to formater:
- Kode (numerisk/ID): f.eks. 'bydel2' med verdier 030101, 030102
- Label (tekst): f.eks. 'bydel2_fmt' med verdier 'Gamle Oslo', 'Grünerløkka'

Disse parene er viktige for:
1. Kolonnemapping - unngå å mappe begge kolonner separat
2. Aggregering - bruke kode for groupby, label for output
3. Kodeliste-matching - matche på kode, hente label fra kodeliste
"""

import pandas as pd


def detect_variable_pairs(df: pd.DataFrame) -> list[dict]:
    """
    Finn variabel-par (kode + tekst) som representerer samme konsept.

    Mønster som detekteres:
      - Kolonnenavn med suffix _fmt (f.eks. bydel2 / bydel2_fmt)
      - Kolonnenavn med .1 variant (f.eks. alder / alder.1)
      - Kolonnepar der base er numerisk og variant er tekst

    Args:
        df: DataFrame å analysere
        
    Returns:
        Liste av dicts med:
            - 'base': Kolonnenavn for koden (f.eks. 'alder')
            - 'label': Kolonnenavn for teksten (f.eks. 'alder.1')
            - 'pattern': Type mønster ('_fmt' eller '.1_variant')
    
    Example:
        >>> df = pd.DataFrame({
        ...     'kjoenn': [1, 2],
        ...     'kjoenn_fmt': ['Mann', 'Kvinne'],
        ...     'antall': [100, 200]
        ... })
        >>> pairs = detect_variable_pairs(df)
        >>> pairs
        [{'base': 'kjoenn', 'label': 'kjoenn_fmt', 'pattern': '_fmt'}]
    """
    cols = df.columns.tolist()
    pairs = []
    used = set()
    
    for c in cols:
        cl = c.lower()
        
        # Mønster 1: _fmt suffix
        if cl.endswith('_fmt'):
            base = c[:-4]
            if base in df.columns and base not in used and c not in used:
                # Sjekk en-til-en forhold mellom base og label
                subset = df[[base, c]].dropna().drop_duplicates()
                base_unique = df[base].nunique(dropna=True)
                label_unique = df[c].nunique(dropna=True)
                pair_unique = subset.shape[0]
                
                # En-til-en hvis alle tre tall er like
                if base_unique == label_unique == pair_unique:
                    pairs.append({'base': base, 'label': c, 'pattern': '_fmt'})
                    used.update({base, c})
                    continue
                
                # Alternativ: base er numerisk og label er tekst
                if not pd.api.types.is_string_dtype(df[base]) and pd.api.types.is_string_dtype(df[c]):
                    pairs.append({'base': base, 'label': c, 'pattern': '_fmt'})
                    used.update({base, c})
        
        # Mønster 2: .1 variant
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
