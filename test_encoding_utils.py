"""
Test encoding_utils modul.
"""

from encoding_utils import (
    decode_xml_entities,
    normalize_whitespace,
    decode_and_normalize,
    clean_dataframe_strings
)
import pandas as pd


def test_decode_xml_entities():
    """Test XML entity decoding."""
    print("\n=== TEST 1: XML Entity Decoding ===")
    
    tests = [
        ('_x0032_025', '2025'),
        ('_x0031_5-24_x0020_år', '15-24 år'),
        ('_x0036_0_x0020_-74_x0020_år', '60 -74 år'),  # Note: whitespace not normalized yet
        ('Normal text', 'Normal text'),
    ]
    
    for input_text, expected in tests:
        result = decode_xml_entities(input_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_text}' → '{result}' (expected: '{expected}')")
        assert result == expected, f"Failed: {input_text}"
    
    print("✅ All XML decoding tests passed!")


def test_normalize_whitespace():
    """Test whitespace normalization."""
    print("\n=== TEST 2: Whitespace Normalization ===")
    
    tests = [
        ('60  -74  år', '60-74 år'),
        ('  Oslo   i   alt  ', 'Oslo i alt'),
        ('60 -74 år', '60-74 år'),
        ('Normal text', 'Normal text'),
    ]
    
    for input_text, expected in tests:
        result = normalize_whitespace(input_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_text}' → '{result}' (expected: '{expected}')")
        assert result == expected, f"Failed: {input_text}"
    
    print("✅ All whitespace tests passed!")


def test_decode_and_normalize():
    """Test combined decode + normalize."""
    print("\n=== TEST 3: Combined Decode + Normalize ===")
    
    tests = [
        ('_x0036_0_x0020_-74_x0020_år', '60-74 år'),
        ('_x0032_025', '2025'),
        ('  _x0031_5-24_x0020_år  ', '15-24 år'),
    ]
    
    for input_text, expected in tests:
        result = decode_and_normalize(input_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_text}' → '{result}' (expected: '{expected}')")
        assert result == expected, f"Failed: {input_text}"
    
    print("✅ All combined tests passed!")


def test_clean_dataframe():
    """Test DataFrame cleaning."""
    print("\n=== TEST 4: DataFrame Cleaning ===")
    
    df = pd.DataFrame({
        'aargang': ['_x0032_025', '_x0032_024'],
        'aldersgruppe': ['_x0036_0_x0020_-74_x0020_år', '_x0031_5-24_x0020_år'],
        'antall': [100, 200]  # Numeric column
    })
    
    print("Before:")
    print(df)
    
    df_clean = clean_dataframe_strings(df)
    
    print("\nAfter:")
    print(df_clean)
    
    assert df_clean['aargang'].tolist() == ['2025', '2024']
    assert df_clean['aldersgruppe'].tolist() == ['60-74 år', '15-24 år']
    assert df_clean['antall'].tolist() == [100, 200]  # Unchanged
    
    print("✅ DataFrame cleaning test passed!")


if __name__ == "__main__":
    test_decode_xml_entities()
    test_normalize_whitespace()
    test_decode_and_normalize()
    test_clean_dataframe()
    
    print("\n" + "="*50)
    print("✅ ALL ENCODING TESTS PASSED!")
    print("="*50)
