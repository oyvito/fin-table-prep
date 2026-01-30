"""
Aggregeringsmodul for DataTransformationTool.

Inneholder logikk for å utføre aggregeringer (totalkategorier) på DataFrames.
Brukes av genererte prep-scripts.

STRATEGI: Parallell aggregering med eksplisitt kryssaggregering
- Hver enkelt-dimensjon aggregeres fra basis
- Kryssaggregeringer (kombinasjoner av totalkategorier) genereres eksplisitt
- Transparent og kontrollerbar
"""

import pandas as pd
from itertools import combinations


def apply_aggregeringer(df_base, aggregeringer, value_cols=None):
    """
    Utfører en liste med aggregeringer på df_base.
    
    Strategi: Parallell aggregering med eksplisitt kryssaggregering
    1. Hver aggregering gjøres fra basis-data
    2. Alle kombinasjoner av totalkategorier (kryssaggregeringer) genereres
    3. Alt kombineres til ett resultat
    
    Args:
        df_base (pd.DataFrame): DataFrame å aggregere
        aggregeringer (list): Liste med aggregeringsbeskrivelser, hver med:
            - 'kolonne': Kolonnenavn å aggregere
            - 'total_verdi': Verdi for totalkategorien
            - 'total_label': Label for totalkategorien
            - 'type': (valgfri) Type aggregering for dokumentasjon
        value_cols (list): Liste med kolonner som skal summeres.
                          Hvis None, auto-detekterer numeriske kolonner.
        
    Returns:
        pd.DataFrame: df_base + alle aggregeringer
        
    Eksempel:
        >>> aggregeringer = [
        ...     {'kolonne': 'bosted', 'total_verdi': 301, 'total_label': '0301 Oslo'},
        ...     {'kolonne': 'kjønn', 'total_verdi': 3, 'total_label': 'Begge kjønn'}
        ... ]
        >>> df_result = apply_aggregeringer(df_base, aggregeringer)
    """
    if not aggregeringer:
        return df_base.copy()
    
    # Auto-detekter value-kolonner hvis ikke spesifisert
    if value_cols is None:
        # Finn numeriske kolonner som ikke er dimensjoner eller labels
        dim_cols = set()
        for agg in aggregeringer:
            dim_cols.add(agg['kolonne'])
            dim_cols.add(f"{agg['kolonne']}.1")
        
        # Keywords som indikerer måltall
        value_keywords = [
            'antall', 'count', 'value', 'verdi', 'beløp', 'sum', 'total', 
            'inntekt', 'utgift', 'pris', 'kr', 'prosent', 'andel', 'rate',
            'kostnad', 'lønn', 'skatt', 'avgift', 'bestand', 'saldo'
        ]
        
        # Keywords som indikerer dimensjoner (IKKE value_cols)
        dimension_keywords = [
            'år', 'aar', 'year', 'dato', 'date', 'tid', 'time',
            'id', 'kode', 'code', 'nr', 'nummer', 'number',
            'alder', 'age', 'måned', 'month', 'dag', 'day',
            'uke', 'week', 'kvartal', 'quarter'
        ]
        
        value_cols = []
        for c in df_base.columns:
            if c in dim_cols or c.endswith('.1'):
                continue
            
            if df_base[c].dtype in ['int64', 'float64', 'int32', 'float32', 'int16', 'float16']:
                col_lower = c.lower()
                
                # Sjekk keywords
                is_value_keyword = any(keyword in col_lower for keyword in value_keywords)
                is_dimension_keyword = any(keyword in col_lower for keyword in dimension_keywords)
                
                # Eksplisitt value-keyword → inkluder
                if is_value_keyword and not is_dimension_keyword:
                    value_cols.append(c)
                # Eksplisitt dimension-keyword → ekskluder
                elif is_dimension_keyword:
                    continue
                # Høy kardinalitet (> 20% av rader) → sannsynligvis måltall
                elif df_base[c].nunique() > len(df_base) * 0.2:
                    value_cols.append(c)
                # Default: Ekskluder (konservativ tilnærming)
    
    # Bygg aggregeringsdictionary for pandas
    agg_dict = {col: 'sum' for col in value_cols}
    
    agg_results = []
    
    # 1. Lag hver enkelt-dimensjon aggregering fra basis
    for agg in aggregeringer:
        kolonne = agg['kolonne']
        total_verdi = agg['total_verdi']
        total_label = agg['total_label']
        
        # Gruppér på alle dimensjoner UNNTATT denne kolonnen
        group_cols = [c for c in df_base.columns 
                     if c not in [kolonne] + value_cols and not c.endswith('.1')]
        
        df_total = df_base.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
        df_total[kolonne] = total_verdi
        
        # Legg til label hvis den eksisterer
        label_col = f'{kolonne}.1'
        if label_col in df_base.columns:
            df_total[label_col] = total_label
        
        agg_results.append(df_total)
    
    # 2. Lag alle kryssaggregeringer (kombinasjoner av 2 eller flere dimensjoner)
    if len(aggregeringer) >= 2:
        # Generer alle kombinasjoner (2-veis, 3-veis, osv.)
        for r in range(2, len(aggregeringer) + 1):
            for agg_combo in combinations(aggregeringer, r):
                # Gruppér på dimensjoner som IKKE er i denne kombinasjonen
                agg_kolonner = [agg['kolonne'] for agg in agg_combo]
                group_cols = [c for c in df_base.columns 
                             if c not in agg_kolonner + value_cols and not c.endswith('.1')]
                
                # Hvis det ikke er noen group_cols igjen, aggreger over ALT (grand total)
                if not group_cols:
                    # Summer bare value-kolonnene
                    df_cross = pd.DataFrame({col: [df_base[col].sum()] for col in value_cols})
                else:
                    df_cross = df_base.groupby(group_cols, dropna=False).agg(agg_dict).reset_index()
                
                # Sett totalkategorier for alle aggregerte dimensjoner
                for agg in agg_combo:
                    df_cross[agg['kolonne']] = agg['total_verdi']
                    label_col = f"{agg['kolonne']}.1"
                    if label_col in df_base.columns:
                        df_cross[label_col] = agg['total_label']
                
                agg_results.append(df_cross)
    
    # 3. Kombiner basis + alle aggregeringer
    df_final = pd.concat([df_base] + agg_results, ignore_index=True)
    
    return df_final


def apply_single_aggregering(df_base, kolonne, total_verdi, total_label, value_cols=None):
    """
    Enklere funksjon for å utføre én enkelt aggregering.
    
    Args:
        df_base (pd.DataFrame): DataFrame å aggregere
        kolonne (str): Kolonnenavn å aggregere
        total_verdi: Verdi for totalkategorien
        total_label: Label for totalkategorien
        value_cols (list): Liste med kolonner som skal summeres
        
    Returns:
        pd.DataFrame: df_base + aggregert data
    """
    aggregeringer = [{
        'kolonne': kolonne,
        'total_verdi': total_verdi,
        'total_label': total_label
    }]
    
    return apply_aggregeringer(df_base, aggregeringer, value_cols)
