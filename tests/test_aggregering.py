"""
Unit tests for aggregering.py module.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from aggregering import apply_aggregeringer, apply_single_aggregering


class TestApplyAggregeringer:
    """Tests for apply_aggregeringer function."""
    
    def test_single_binary_aggregation(self):
        """Test aggregering av binær dimensjon (f.eks. kjønn)."""
        df = pd.DataFrame({
            'år': [2024, 2024, 2024, 2024],
            'kjønn': [1, 2, 1, 2],
            'kjønn.1': ['Mann', 'Kvinne', 'Mann', 'Kvinne'],
            'bydel': [1, 1, 2, 2],
            'antall': [100, 150, 200, 250]
        })
        
        aggregeringer = [
            {'kolonne': 'kjønn', 'total_verdi': 3, 'total_label': 'Begge kjønn'}
        ]
        
        result = apply_aggregeringer(df, aggregeringer, value_cols=['antall'])
        
        # Original: 4 rader, Aggregert: 2 rader (per bydel)
        assert len(result) == 6
        
        # Sjekk at "Begge kjønn" er lagt til
        begge_kjonn = result[result['kjønn'] == 3]
        assert len(begge_kjonn) == 2
        
        # Sjekk at antall er summert korrekt
        bydel1_total = begge_kjonn[begge_kjonn['bydel'] == 1]['antall'].values[0]
        assert bydel1_total == 250  # 100 + 150
    
    def test_geography_aggregation(self):
        """Test geografisk aggregering (bydel → Oslo i alt)."""
        df = pd.DataFrame({
            'år': [2024, 2024, 2024],
            'bydel': [1, 2, 3],
            'bydel.1': ['Gamle Oslo', 'Grünerløkka', 'Sagene'],
            'antall': [1000, 2000, 1500]
        })
        
        aggregeringer = [
            {'kolonne': 'bydel', 'total_verdi': 301, 'total_label': '0301 Oslo'}
        ]
        
        result = apply_aggregeringer(df, aggregeringer, value_cols=['antall'])
        
        # Original: 3 rader, Aggregert: 1 rad (Oslo i alt)
        assert len(result) == 4
        
        oslo_total = result[result['bydel'] == 301]['antall'].values[0]
        assert oslo_total == 4500  # 1000 + 2000 + 1500
    
    def test_cross_aggregation(self):
        """Test kryssaggregering (kjønn + bydel)."""
        df = pd.DataFrame({
            'år': [2024, 2024, 2024, 2024],
            'kjønn': [1, 2, 1, 2],
            'bydel': [1, 1, 2, 2],
            'antall': [100, 150, 200, 250]
        })
        
        aggregeringer = [
            {'kolonne': 'kjønn', 'total_verdi': 3, 'total_label': 'Begge kjønn'},
            {'kolonne': 'bydel', 'total_verdi': 301, 'total_label': 'Oslo i alt'}
        ]
        
        result = apply_aggregeringer(df, aggregeringer, value_cols=['antall'])
        
        # Original: 4 rader
        # Kjønn-aggregering: 2 rader (per bydel)
        # Bydel-aggregering: 2 rader (per kjønn)
        # Kryss-aggregering: 1 rad (begge kjønn + Oslo i alt)
        # Total: 4 + 2 + 2 + 1 = 9 rader
        assert len(result) == 9
        
        # Sjekk grand total
        grand_total = result[(result['kjønn'] == 3) & (result['bydel'] == 301)]
        assert len(grand_total) == 1
        assert grand_total['antall'].values[0] == 700  # Sum av alle
    
    def test_empty_aggregation_list(self):
        """Test med tom aggregeringsliste."""
        df = pd.DataFrame({
            'år': [2024],
            'antall': [100]
        })
        
        result = apply_aggregeringer(df, [], value_cols=['antall'])
        
        # Skal returnere kopi av original
        assert len(result) == 1
        assert result['antall'].values[0] == 100
    
    def test_auto_detect_value_columns(self):
        """Test automatisk deteksjon av value-kolonner."""
        df = pd.DataFrame({
            'år': [2024, 2024],
            'kjønn': [1, 2],
            'antall': [100, 200],  # Skal detekteres som value
            'beløp': [5000.0, 7500.0]  # Skal detekteres som value
        })
        
        aggregeringer = [
            {'kolonne': 'kjønn', 'total_verdi': 3, 'total_label': 'Begge'}
        ]
        
        # Ikke spesifiser value_cols - skal auto-detekteres
        result = apply_aggregeringer(df, aggregeringer)
        
        assert len(result) == 3  # 2 original + 1 aggregert
        
        total_row = result[result['kjønn'] == 3]
        # Sjekk at begge value-kolonner er summert
        assert total_row['antall'].values[0] == 300


class TestApplySingleAggregering:
    """Tests for apply_single_aggregering helper function."""
    
    def test_single_aggregering_helper(self):
        """Test helper-funksjonen for én aggregering."""
        df = pd.DataFrame({
            'år': [2024, 2024],  # Trenger minst én gruppe-kolonne
            'kjønn': [1, 2],
            'antall': [100, 200]
        })
        
        result = apply_single_aggregering(
            df, 
            kolonne='kjønn',
            total_verdi=3,
            total_label='Begge',
            value_cols=['antall']
        )
        
        assert len(result) == 3
        assert result[result['kjønn'] == 3]['antall'].values[0] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
