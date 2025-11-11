"""
Encoding-utilities for DataTransformationTool.

Håndterer ulike encoding-utfordringer fra Excel og andre kilder.
"""

import re
import pandas as pd
from typing import Any


def decode_xml_entities(text: str) -> str:
    """
    Dekoder XML-encoded entities fra Excel.
    
    Excel lagrer noen spesialtegn som XML-entities:
    - _x0032_025 → '2025'
    - _x0031_5-24_x0020_år → '15-24 år'
    - _x0036_0_x0020_-74_x0020_år → '60-74 år'
    
    Args:
        text: Tekst med potensielle XML-entities
    
    Returns:
        Dekoded tekst
    
    Eksempel:
        >>> decode_xml_entities('_x0032_025')
        '2025'
        >>> decode_xml_entities('_x0031_5-24_x0020_år')
        '15-24 år'
    """
    if not isinstance(text, str):
        return text
    
    # Regex: _x[4-digit hex]_ → tilsvarende Unicode-tegn
    decoded = re.sub(
        r'_x([0-9A-Fa-f]{4})_',
        lambda m: chr(int(m.group(1), 16)),
        text
    )
    
    return decoded


def normalize_whitespace(text: str) -> str:
    """
    Normaliser whitespace i tekst.
    
    - Fjerner doble mellomrom
    - Fjerner mellomrom før bindestreker i aldersgrupper (60 -74 → 60-74)
    - Trimmer start/slutt
    
    Args:
        text: Tekst å normalisere
    
    Returns:
        Normalisert tekst
    
    Eksempel:
        >>> normalize_whitespace('60  -74  år')
        '60-74 år'
        >>> normalize_whitespace('  Oslo   i   alt  ')
        'Oslo i alt'
    """
    if not isinstance(text, str):
        return text
    
    # Fjern doble mellomrom
    normalized = ' '.join(text.split())
    
    # Fjern mellomrom før bindestrek (aldersgrupper)
    normalized = normalized.replace(' -', '-')
    
    return normalized


def decode_and_normalize(text: str) -> str:
    """
    Dekoder XML-entities og normaliserer whitespace i én operasjon.
    
    Args:
        text: Tekst å behandle
    
    Returns:
        Dekoded og normalisert tekst
    
    Eksempel:
        >>> decode_and_normalize('_x0036_0_x0020_-74_x0020_år')
        '60-74 år'
    """
    if not isinstance(text, str):
        return text
    
    decoded = decode_xml_entities(text)
    normalized = normalize_whitespace(decoded)
    
    return normalized


def clean_dataframe_strings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dekoder og normaliserer alle tekstkolonner i en DataFrame.
    
    Bruker decode_and_normalize() på alle object-kolonner.
    
    Args:
        df: DataFrame å rense
    
    Returns:
        DataFrame med rensede tekstkolonner
    
    Eksempel:
        >>> df = pd.DataFrame({'år': ['_x0032_025'], 'alder': ['60  -74 år']})
        >>> df_clean = clean_dataframe_strings(df)
        >>> df_clean['år'][0]
        '2025'
        >>> df_clean['alder'][0]
        '60-74 år'
    """
    df_cleaned = df.copy()
    
    for col in df_cleaned.columns:
        if df_cleaned[col].dtype == 'object':
            df_cleaned[col] = df_cleaned[col].apply(decode_and_normalize)
    
    return df_cleaned


# Alias for bakoverkompatibilitet
decode_xml_strings = clean_dataframe_strings
