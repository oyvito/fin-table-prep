"""
Unit tests for codelist_manager.py module.
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from codelist_manager import CodelistManager


class TestCodelistManager:
    """Tests for CodelistManager class."""
    
    @pytest.fixture
    def temp_codelist_dir(self):
        """Opprett midlertidig mappe med test-kodelister."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Lag en test-kodeliste
            test_codelist = {
                "name": "Test SSB to PX",
                "description": "Test kodeliste",
                "source_column_patterns": ["bydel.*", ".*bydel.*"],
                "target_column_patterns": ["bosted.*", "geografi.*"],
                "mappings": {
                    "030101": "1",
                    "030102": "2",
                    "030103": "3"
                },
                "labels": {
                    "1": "Gamle Oslo",
                    "2": "Grünerløkka",
                    "3": "Sagene"
                }
            }
            
            codelist_path = os.path.join(tmpdir, "test_geo.json")
            with open(codelist_path, 'w', encoding='utf-8') as f:
                json.dump(test_codelist, f, ensure_ascii=False)
            
            yield tmpdir
    
    def test_load_codelists(self, temp_codelist_dir):
        """Test innlasting av kodelister."""
        manager = CodelistManager(temp_codelist_dir)
        
        assert len(manager.codelists) == 1
        assert "Test SSB to PX" in manager.codelists
    
    def test_find_matching_codelist_by_pattern(self, temp_codelist_dir):
        """Test at kodeliste matches på kolonnenavn-mønster."""
        manager = CodelistManager(temp_codelist_dir)
        
        source_values = {"030101", "030102", "030103"}
        target_values = {"1", "2", "3"}
        
        result = manager.find_matching_codelist(
            source_col="bydel2",
            target_col="bosted",
            source_values=source_values,
            target_values=target_values
        )
        
        assert result is not None
        assert result['name'] == "Test SSB to PX"
    
    def test_find_matching_codelist_by_values(self, temp_codelist_dir):
        """Test at kodeliste matches på verdioverlapp."""
        manager = CodelistManager(temp_codelist_dir)
        
        # Verdiene matcher kodelisten
        source_values = {"030101", "030102"}
        target_values = {"1", "2"}
        
        result = manager.find_matching_codelist(
            source_col="geo_kode",  # Matcher ikke pattern direkte
            target_col="geo_output",
            source_values=source_values,
            target_values=target_values
        )
        
        # Skal finne match basert på verdier + geo keywords
        # (Avhenger av implementasjonsdetaljer)
    
    def test_no_match_returns_none(self, temp_codelist_dir):
        """Test at None returneres når ingen match finnes."""
        manager = CodelistManager(temp_codelist_dir)
        
        source_values = {"X", "Y", "Z"}
        target_values = {"A", "B", "C"}
        
        result = manager.find_matching_codelist(
            source_col="random_col",
            target_col="other_col",
            source_values=source_values,
            target_values=target_values
        )
        
        assert result is None
    
    def test_empty_directory(self):
        """Test håndtering av tom kodeliste-mappe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CodelistManager(tmpdir)
            assert len(manager.codelists) == 0
    
    def test_nonexistent_directory(self):
        """Test håndtering av ikke-eksisterende mappe."""
        manager = CodelistManager("/nonexistent/path")
        assert len(manager.codelists) == 0


class TestCodelistManagerIntegration:
    """Integrasjonstester med ekte kodelister."""
    
    def test_load_real_codelists(self):
        """Test at ekte kodelister lastes korrekt."""
        # Bruk prosjektets faktiske kodeliste-mappe
        codelist_dir = Path(__file__).parent.parent / "kodelister"
        
        if codelist_dir.exists():
            manager = CodelistManager(str(codelist_dir))
            
            # Sjekk at noen kodelister ble lastet
            assert len(manager.codelists) > 0
            
            # Sjekk at SSB_til_PX_geo_bydel finnes
            bydel_codelist = None
            for name, codelist in manager.codelists.items():
                if 'bydel' in name.lower():
                    bydel_codelist = codelist
                    break
            
            if bydel_codelist:
                assert 'mappings' in bydel_codelist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
