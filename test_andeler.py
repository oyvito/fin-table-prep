"""
Test av andeler.py modul.
"""

import pandas as pd
from andeler import (
    beregn_andeler, 
    beregn_flere_andeler, 
    beregn_sysselsetting_andel,
    beregn_auto_andeler
)


def test_enkel_andel():
    """Test enkel andelsberegning."""
    print("\n=== TEST 1: Enkel andelsberegning ===")
    
    df = pd.DataFrame({
        'sysselsatte': [100, 200, 300],
        'befolkning': [500, 800, 1000]
    })
    
    df_result = beregn_andeler(
        df, 
        teller_col='sysselsatte',
        nevner_col='befolkning',
        andel_col='andel_pst',
        multiplier=100,
        decimals=1
    )
    
    print(f"Input:")
    print(df)
    print(f"\nOutput:")
    print(df_result)
    print(f"\nForventede andeler: [20.0, 25.0, 30.0]")
    print(f"Faktiske andeler: {df_result['andel_pst'].tolist()}")
    
    assert df_result['andel_pst'].tolist() == [20.0, 25.0, 30.0], "Andeler er feil!"
    print("✅ Test OK!")


def test_flere_andeler():
    """Test flere andelsberegninger samtidig."""
    print("\n=== TEST 2: Flere andeler samtidig ===")
    
    df = pd.DataFrame({
        'sysselsatte': [100, 200],
        'befolkning': [500, 800],
        'studenter': [50, 120],
        'ungdom': [100, 200]
    })
    
    specs = [
        {
            'teller_col': 'sysselsatte',
            'nevner_col': 'befolkning',
            'andel_col': 'andel_sysselsatte'
        },
        {
            'teller_col': 'studenter',
            'nevner_col': 'ungdom',
            'andel_col': 'andel_studenter'
        }
    ]
    
    df_result = beregn_flere_andeler(df, specs, multiplier=100, decimals=1)
    
    print(f"Input:")
    print(df)
    print(f"\nOutput:")
    print(df_result[['sysselsatte', 'befolkning', 'andel_sysselsatte', 
                     'studenter', 'ungdom', 'andel_studenter']])
    
    assert 'andel_sysselsatte' in df_result.columns
    assert 'andel_studenter' in df_result.columns
    print("✅ Test OK!")


def test_sysselsetting_andel():
    """Test spesialisert sysselsettingsandel."""
    print("\n=== TEST 3: Sysselsettingsandel (spesialisert) ===")
    
    df = pd.DataFrame({
        'aargang': [2024, 2024],
        'geografi': ['Oslo', 'Bergen'],
        'sysselsatte': [100000, 50000],
        'befolkning': [500000, 200000]
    })
    
    df_result = beregn_sysselsetting_andel(df)
    
    print(f"Input:")
    print(df)
    print(f"\nOutput:")
    print(df_result)
    
    assert 'andeler' in df_result.columns
    assert df_result['andeler'].tolist() == [20.0, 25.0]
    print("✅ Test OK!")


def test_auto_andeler():
    """Test auto-deteksjon av andeler."""
    print("\n=== TEST 4: Auto-deteksjon av andeler ===")
    
    df = pd.DataFrame({
        'geografi': ['Oslo', 'Bergen'],
        'sysselsatte': [100, 200],
        'befolkning': [500, 800]
    })
    
    df_result = beregn_auto_andeler(df, multiplier=100, decimals=1)
    
    print(f"Input:")
    print(df)
    print(f"\nOutput:")
    print(df_result)
    
    assert 'andel_sysselsatte' in df_result.columns
    print("✅ Test OK!")


def test_promille():
    """Test promille-beregning (per 1000)."""
    print("\n=== TEST 5: Promille-beregning ===")
    
    df = pd.DataFrame({
        'antall_døde': [5, 8],
        'befolkning': [10000, 8000]
    })
    
    df_result = beregn_andeler(
        df,
        teller_col='antall_døde',
        nevner_col='befolkning',
        andel_col='dødsrate_promille',
        multiplier=1000,  # Per 1000
        decimals=2
    )
    
    print(f"Input:")
    print(df)
    print(f"\nOutput:")
    print(df_result)
    print(f"\nDødsrate per 1000: {df_result['dødsrate_promille'].tolist()}")
    
    assert df_result['dødsrate_promille'].tolist() == [0.5, 1.0]
    print("✅ Test OK!")


if __name__ == "__main__":
    test_enkel_andel()
    test_flere_andeler()
    test_sysselsetting_andel()
    test_auto_andeler()
    test_promille()
    
    print("\n" + "="*50)
    print("✅ ALLE TESTER FULLFØRT!")
    print("="*50)
