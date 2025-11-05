"""
Kodeliste-håndtering for Data Transformation Tool.
Laster og anvender kodelister når relevante kolonner oppdages.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CodelistManager:
    """Håndterer innlasting og bruk av kodelister."""
    
    def __init__(self, codelist_dir: str = "kodelister"):
        self.codelist_dir = Path(codelist_dir)
        self.codelists = {}
        self.load_codelists()
    
    def load_codelists(self):
        """Last inn alle JSON-kodelister fra mappen."""
        if not self.codelist_dir.exists():
            return
        
        for json_file in self.codelist_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    codelist = json.load(f)
                    name = codelist.get('name', json_file.stem)
                    self.codelists[name] = codelist
            except Exception as e:
                print(f"Kunne ikke laste {json_file}: {e}")
    
    def find_matching_codelist(self, source_col: str, target_col: str, 
                              source_values: set, target_values: set) -> Optional[dict]:
        """
        Finn kodeliste som matcher source/target kolonner.
        
        Sjekker:
        1. Kolonnenavn-mønstre
        2. Overlap i verdier
        """
        best_match = None
        best_score = 0
        
        for name, codelist in self.codelists.items():
            score = 0
            
            # Sjekk kolonnenavn-mønstre
            source_patterns = codelist.get('source_column_patterns', [])
            target_patterns = codelist.get('target_column_patterns', [])
            
            for pattern in source_patterns:
                if re.search(pattern, source_col, re.IGNORECASE):
                    score += 2
            
            for pattern in target_patterns:
                if re.search(pattern, target_col, re.IGNORECASE):
                    score += 2
            
            # Sjekk overlap i faktiske verdier
            mappings = codelist.get('mappings', {})
            if mappings:
                mapping_keys = set(str(k) for k in mappings.keys())
                
                # Sammenlign med source_values
                source_overlap = len(mapping_keys & source_values)
                if source_overlap > 0:
                    overlap_ratio = source_overlap / len(source_values) if source_values else 0
                    score += overlap_ratio * 10
                
                # Sjekk om mapping-verdiene finnes i target
                if isinstance(list(mappings.values())[0], dict):
                    # Format: {"code": "...", "name": "..."}
                    mapping_codes = set(str(v.get('code', v)) for v in mappings.values())
                else:
                    mapping_codes = set(str(v) for v in mappings.values())
                
                target_overlap = len(mapping_codes & target_values)
                if target_overlap > 0:
                    overlap_ratio = target_overlap / len(target_values) if target_values else 0
                    score += overlap_ratio * 10
            
            if score > best_score and score > 5:  # Minimum terskel
                best_score = score
                best_match = codelist
        
        return best_match
    
    def get_mapping_code(self, codelist: dict, for_column: str) -> Tuple[str, str]:
        """
        Generer Python-kode for å anvende kodelisten.
        
        Returns:
            (mapping_dict_code, transformation_code)
        """
        mappings = codelist.get('mappings', {})
        name = codelist.get('name', 'mapping').lower().replace(' ', '_').replace('-', '_')
        
        # Generer mapping-dictionary
        dict_lines = [f"{name}_mapping = {{"]
        
        for key, value in mappings.items():
            if isinstance(value, dict):
                # Format: {"code": "...", "name": "..."}
                code = value.get('code', key)
                dict_lines.append(f'    "{key}": "{code}",')
            else:
                dict_lines.append(f'    "{key}": "{value}",')
        
        dict_lines.append("}")
        dict_code = '\n'.join(dict_lines)
        
        # Generer transformasjonskode
        safe_col = for_column.replace(' ', '_').replace('-', '_')
        transform_code = f'df["{for_column}"] = df["{for_column}"].astype(str).map({name}_mapping)'
        
        # Legg til navne-mapping hvis det finnes
        name_mappings = codelist.get('name_mappings', {})
        if name_mappings:
            dict_lines_name = [f"\n{name}_name_mapping = {{"]
            for key, value in name_mappings.items():
                dict_lines_name.append(f'    "{key}": "{value}",')
            dict_lines_name.append("}")
            dict_code += '\n' + '\n'.join(dict_lines_name)
        
        return dict_code, transform_code
    
    def list_available_codelists(self) -> List[str]:
        """Returner liste over tilgjengelige kodelister."""
        return list(self.codelists.keys())


# Eksempel på bruk
if __name__ == "__main__":
    manager = CodelistManager()
    print(f"Lastet {len(manager.codelists)} kodelister:")
    for name in manager.list_available_codelists():
        print(f"  - {name}")
