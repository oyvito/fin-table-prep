"""
Modul for andelsberegninger i statistikktabeller.

Typiske bruksområder:
- Sysselsettingsandeler (sysselsatte/befolkning)
- Prosentandeler av totaler
- Rate-beregninger (per 1000/10000)

Eksempel:
    from andeler import beregn_andeler
    
    df = beregn_andeler(
        df,
        teller_col='sysselsatte',
        nevner_col='befolkning',
        andel_col='andel_sysselsatte',
        multiplier=100,  # Prosent
        decimals=1
    )
"""

import pandas as pd
from typing import Optional


def beregn_andeler(
    df: pd.DataFrame,
    teller_col: str,
    nevner_col: str,
    andel_col: str = 'andel',
    multiplier: float = 100.0,
    decimals: int = 1,
    fill_na: Optional[float] = None
) -> pd.DataFrame:
    """
    Beregn andeler (teller/nevner * multiplier).
    
    Args:
        df: DataFrame med data
        teller_col: Kolonnenavn for teller (f.eks. 'sysselsatte')
        nevner_col: Kolonnenavn for nevner (f.eks. 'befolkning')
        andel_col: Navn på ny kolonne med andeler (default: 'andel')
        multiplier: Multiplier for andel (100 for prosent, 1000 for promille)
        decimals: Antall desimaler (default: 1)
        fill_na: Verdi for å erstatte NaN/inf (None = behold NaN)
    
    Returns:
        DataFrame med ny andelskolonne
    
    Eksempel:
        >>> df = pd.DataFrame({
        ...     'sysselsatte': [100, 200, 300],
        ...     'befolkning': [500, 800, 1000]
        ... })
        >>> df = beregn_andeler(df, 'sysselsatte', 'befolkning', 'andel_pst')
        >>> df['andel_pst']
        0    20.0
        1    25.0
        2    30.0
    """
    df = df.copy()
    
    # Beregn andel
    df[andel_col] = (df[teller_col] / df[nevner_col] * multiplier).round(decimals)
    
    # Håndter NaN/inf hvis ønsket
    if fill_na is not None:
        df[andel_col] = df[andel_col].fillna(fill_na)
        df[andel_col] = df[andel_col].replace([float('inf'), float('-inf')], fill_na)
    
    return df


def beregn_flere_andeler(
    df: pd.DataFrame,
    andel_specs: list[dict],
    multiplier: float = 100.0,
    decimals: int = 1
) -> pd.DataFrame:
    """
    Beregn flere andeler i én operasjon.
    
    Args:
        df: DataFrame med data
        andel_specs: Liste med spesifikasjoner for hver andel
            Hvert element er en dict med:
                - teller_col: str
                - nevner_col: str
                - andel_col: str
                - multiplier: float (optional, bruker default hvis ikke spesifisert)
                - decimals: int (optional)
        multiplier: Default multiplier
        decimals: Default antall desimaler
    
    Returns:
        DataFrame med alle nye andelskolonner
    
    Eksempel:
        >>> specs = [
        ...     {'teller_col': 'sysselsatte', 'nevner_col': 'befolkning', 
        ...      'andel_col': 'andel_sysselsatte'},
        ...     {'teller_col': 'studenter', 'nevner_col': 'ungdom_15_24', 
        ...      'andel_col': 'andel_studenter'}
        ... ]
        >>> df = beregn_flere_andeler(df, specs)
    """
    df_result = df.copy()
    
    for spec in andel_specs:
        teller = spec['teller_col']
        nevner = spec['nevner_col']
        andel = spec['andel_col']
        mult = spec.get('multiplier', multiplier)
        dec = spec.get('decimals', decimals)
        fill = spec.get('fill_na', None)
        
        df_result = beregn_andeler(
            df_result,
            teller_col=teller,
            nevner_col=nevner,
            andel_col=andel,
            multiplier=mult,
            decimals=dec,
            fill_na=fill
        )
    
    return df_result


def beregn_auto_andeler(
    df: pd.DataFrame,
    multiplier: float = 100.0,
    decimals: int = 1,
    exclude_cols: Optional[list[str]] = None
) -> pd.DataFrame:
    """
    Auto-detekter potensielle andelsberegninger basert på kolonnenavn.
    
    Søker etter mønstre som:
    - 'antall_X' + 'antall_Y' → 'andel_X' (X/Y)
    - 'X' + 'befolkning' → 'andel_X'
    - 'sysselsatte' + 'befolkning' → 'andel_sysselsatte'
    
    Args:
        df: DataFrame med data
        multiplier: Multiplier for andeler (100 for prosent)
        decimals: Antall desimaler
        exclude_cols: Kolonner som skal ekskluderes fra auto-deteksjon
    
    Returns:
        DataFrame med auto-detekterte andelskolonner
    
    NOTE: Dette er eksperimentelt og kan gi falske positiver.
          Bruk beregn_andeler() for eksplisitt kontroll.
    """
    df_result = df.copy()
    exclude = set(exclude_cols or [])
    
    # Mønster 1: 'sysselsatte' + 'befolkning' → 'andel_sysselsatte'
    if 'sysselsatte' in df.columns and 'befolkning' in df.columns:
        if 'sysselsatte' not in exclude and 'befolkning' not in exclude:
            print("  Auto: sysselsatte/befolkning → andel_sysselsatte")
            df_result = beregn_andeler(
                df_result, 'sysselsatte', 'befolkning', 
                'andel_sysselsatte', multiplier, decimals
            )
    
    # Mønster 2: 'antall_X' der X ikke er 'total' eller 'i_alt'
    antall_cols = [c for c in df.columns if c.startswith('antall_') and c not in exclude]
    if 'befolkning' in df.columns and 'befolkning' not in exclude:
        for col in antall_cols:
            kategori = col.replace('antall_', '')
            if kategori not in ['total', 'i_alt', 'sum']:
                andel_navn = f'andel_{kategori}'
                if andel_navn not in df.columns:
                    print(f"  Auto: {col}/befolkning → {andel_navn}")
                    df_result = beregn_andeler(
                        df_result, col, 'befolkning',
                        andel_navn, multiplier, decimals
                    )
    
    return df_result


# Domenekunnskap for spesifikke tabelltyper
SYSSELSETTING_ANDEL = {
    'teller_col': 'sysselsatte',
    'nevner_col': 'befolkning',
    'andel_col': 'andeler',  # Standard navn i sysselsettingstabeller
    'multiplier': 100,
    'decimals': 1,
    'domain': 'sysselsetting'
}


def beregn_sysselsetting_andel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Spesialisert funksjon for sysselsettingsandeler.
    
    Følger standard konvensjoner:
    - Teller: 'sysselsatte'
    - Nevner: 'befolkning'
    - Resultat: 'andeler' (prosent med 1 desimal)
    
    Args:
        df: DataFrame med 'sysselsatte' og 'befolkning' kolonner
    
    Returns:
        DataFrame med 'andeler' kolonne
    """
    return beregn_andeler(
        df,
        teller_col='sysselsatte',
        nevner_col='befolkning',
        andel_col='andeler',
        multiplier=100.0,
        decimals=1
    )
