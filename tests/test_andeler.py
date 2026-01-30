"""
Unit tests for andeler.py module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from andeler import beregn_andeler, beregn_flere_andeler


class TestBeregnAndeler:
    """Tests for beregn_andeler function."""
    
    def test_basic_percentage(self):
        """Test grunnleggende prosentberegning."""
        df = pd.DataFrame({
            'sysselsatte': [100, 200, 300],
            'befolkning': [500, 800, 1000]
        })
        
        result = beregn_andeler(
            df,
            teller_col='sysselsatte',
            nevner_col='befolkning',
            andel_col='andel_pst',
            multiplier=100,
            decimals=1
        )
        
        assert 'andel_pst' in result.columns
        assert result['andel_pst'].tolist() == [20.0, 25.0, 30.0]
    
    def test_promille(self):
        """Test promille-beregning (per 1000)."""
        df = pd.DataFrame({
            'tilfeller': [5, 10],
            'total': [10000, 20000]
        })
        
        result = beregn_andeler(
            df,
            teller_col='tilfeller',
            nevner_col='total',
            andel_col='rate_promille',
            multiplier=1000,
            decimals=2
        )
        
        assert result['rate_promille'].tolist() == [0.5, 0.5]
    
    def test_division_by_zero_nan(self):
        """Test håndtering av divisjon med null (gir NaN)."""
        df = pd.DataFrame({
            'teller': [100, 200],
            'nevner': [0, 400]
        })
        
        result = beregn_andeler(
            df,
            teller_col='teller',
            nevner_col='nevner',
            andel_col='andel'
        )
        
        # Første rad: divisjon med 0 → inf, som beholdes som inf når fill_na=None
        assert pd.isna(result['andel'].iloc[0]) or result['andel'].iloc[0] == float('inf')
        assert result['andel'].iloc[1] == 50.0
    
    def test_fill_na_value(self):
        """Test at fill_na erstatter NaN/inf."""
        df = pd.DataFrame({
            'teller': [100, 200],
            'nevner': [0, 400]
        })
        
        result = beregn_andeler(
            df,
            teller_col='teller',
            nevner_col='nevner',
            andel_col='andel',
            fill_na=0.0
        )
        
        assert result['andel'].iloc[0] == 0.0
        assert result['andel'].iloc[1] == 50.0
    
    def test_preserves_other_columns(self):
        """Test at andre kolonner bevares."""
        df = pd.DataFrame({
            'år': [2024, 2024],
            'bydel': ['Gamle Oslo', 'Grünerløkka'],
            'sysselsatte': [5000, 6000],
            'befolkning': [10000, 12000]
        })
        
        result = beregn_andeler(df, 'sysselsatte', 'befolkning', 'andel')
        
        assert 'år' in result.columns
        assert 'bydel' in result.columns
        assert result['bydel'].tolist() == ['Gamle Oslo', 'Grünerløkka']


class TestBeregnFlereAndeler:
    """Tests for beregn_flere_andeler function."""
    
    def test_multiple_shares(self):
        """Test beregning av flere andeler samtidig."""
        df = pd.DataFrame({
            'sysselsatte': [1000, 2000],
            'studenter': [200, 400],
            'befolkning': [5000, 8000],
            'ungdom': [1000, 2000]
        })
        
        specs = [
            {'teller_col': 'sysselsatte', 'nevner_col': 'befolkning', 'andel_col': 'syss_andel'},
            {'teller_col': 'studenter', 'nevner_col': 'ungdom', 'andel_col': 'stud_andel'}
        ]
        
        result = beregn_flere_andeler(df, specs, multiplier=100)
        
        assert 'syss_andel' in result.columns
        assert 'stud_andel' in result.columns
        assert result['syss_andel'].tolist() == [20.0, 25.0]
        assert result['stud_andel'].tolist() == [20.0, 20.0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
