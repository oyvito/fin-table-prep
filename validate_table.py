"""
Validator og standardiserer for statistikktabeller basert på kontrollskjema.
Sikrer konsistent navngiving, koding og struktur på tvers av alle tabeller.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple


class TableValidator:
    """Validerer og standardiserer tabeller basert på kontrollskjema."""
    
    def __init__(self, kontrollskjema_path: str = "kontrollskjema.json"):
        with open(kontrollskjema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        
        self.standard_vars = self.schema['standard_variables']
        self.geo_coding = self.schema['geographic_coding']
    
    def suggest_column_standardization(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Foreslå standardisering av kolonnenavn basert på kontrollskjema.
        
        Returns:
            Dict med mapping: {current_name: suggested_standard_name}
        """
        suggestions = {}
        
        for col in df.columns:
            col_lower = col.lower().strip()
            
            # Sjekk mot hver standard variabel
            for std_name, std_info in self.standard_vars.items():
                # Sjekk eksakte match (case-insensitive)
                if col_lower == std_name:
                    if col != std_name:  # Feil case
                        suggestions[col] = std_name
                    continue
                
                # Sjekk alternative navn
                alt_names = std_info.get('alternative_names', [])
                alt_names_lower = [name.lower() for name in alt_names]
                
                if col_lower in alt_names_lower:
                    suggestions[col] = std_name
                    break
        
        return suggestions
    
    def validate_data_types(self, df: pd.DataFrame) -> List[Dict]:
        """
        Valider at datatyper stemmer med kontrollskjema.
        
        Returns:
            Liste med warnings/errors
        """
        issues = []
        
        for col in df.columns:
            col_lower = col.lower().strip()
            
            if col_lower in self.standard_vars:
                std_info = self.standard_vars[col_lower]
                expected_type = std_info.get('data_type')
                
                if expected_type == 'integer':
                    if not pd.api.types.is_integer_dtype(df[col]):
                        try:
                            # Sjekk om det kan konverteres
                            pd.to_numeric(df[col], errors='coerce').astype('Int64')
                        except:
                            issues.append({
                                'column': col,
                                'issue': f'Forventet integer, fant {df[col].dtype}',
                                'severity': 'warning'
                            })
                
                elif expected_type == 'float':
                    if not pd.api.types.is_float_dtype(df[col]) and not pd.api.types.is_integer_dtype(df[col]):
                        issues.append({
                            'column': col,
                            'issue': f'Forventet numeric, fant {df[col].dtype}',
                            'severity': 'warning'
                        })
        
        return issues
    
    def validate_geographic_coding(self, df: pd.DataFrame) -> List[Dict]:
        """
        Valider at geografisk koding følger standard.
        
        Returns:
            Liste med issues
        """
        issues = []
        
        # Sjekk om det finnes geografiske kolonner
        geo_cols = [col for col in df.columns if any(
            geo_term in col.lower() 
            for geo_term in ['geografi', 'bydel', 'grunnkrets', 'kommune', 'tknr']
        )]
        
        if not geo_cols:
            return issues
        
        # Sjekk at kodelister er brukt
        for col in geo_cols:
            sample_values = df[col].dropna().unique()[:10]
            
            # TODO: Sjekk mot kodelister
            # For nå, bare warn hvis verdiene ser ut som SSB-koder
            for val in sample_values:
                val_str = str(val)
                if val_str.startswith('030') and len(val_str) == 5:
                    issues.append({
                        'column': col,
                        'issue': 'Mulig SSB-kode funnet. Skal være PX-kode.',
                        'example': val_str,
                        'severity': 'warning'
                    })
                    break
        
        return issues
    
    def validate_value_ranges(self, df: pd.DataFrame) -> List[Dict]:
        """
        Valider at verdier er innenfor gyldige områder.
        
        Returns:
            Liste med issues
        """
        issues = []
        
        for col in df.columns:
            col_lower = col.lower().strip()
            
            if col_lower in self.standard_vars:
                std_info = self.standard_vars[col_lower]
                validation = std_info.get('validation', {})
                
                if 'min' in validation or 'max' in validation:
                    min_val = validation.get('min')
                    max_val = validation.get('max')
                    
                    actual_min = df[col].min()
                    actual_max = df[col].max()
                    
                    if min_val is not None and actual_min < min_val:
                        issues.append({
                            'column': col,
                            'issue': f'Verdi under minimum: {actual_min} < {min_val}',
                            'severity': 'error'
                        })
                    
                    if max_val is not None and actual_max > max_val:
                        issues.append({
                            'column': col,
                            'issue': f'Verdi over maksimum: {actual_max} > {max_val}',
                            'severity': 'error'
                        })
        
        return issues
    
    def generate_validation_report(self, df: pd.DataFrame, table_name: str = "Tabell") -> str:
        """
        Generer fullstendig valideringsrapport.
        """
        report = []
        report.append(f"=" * 60)
        report.append(f"VALIDERINGSRAPPORT: {table_name}")
        report.append(f"=" * 60)
        report.append(f"Antall rader: {len(df)}")
        report.append(f"Antall kolonner: {len(df.columns)}")
        report.append("")
        
        # Kolonnenavn-standardisering
        suggestions = self.suggest_column_standardization(df)
        if suggestions:
            report.append("📝 FORSLAG TIL STANDARDISERING AV KOLONNENAVN:")
            report.append("-" * 60)
            for old_name, new_name in suggestions.items():
                report.append(f"  '{old_name}' → '{new_name}'")
            report.append("")
        else:
            report.append("✓ Alle kolonnenavn følger standard")
            report.append("")
        
        # Datatype-validering
        type_issues = self.validate_data_types(df)
        if type_issues:
            report.append("⚠️  DATATYPE-ADVARSLER:")
            report.append("-" * 60)
            for issue in type_issues:
                report.append(f"  {issue['column']}: {issue['issue']}")
            report.append("")
        
        # Geografisk koding
        geo_issues = self.validate_geographic_coding(df)
        if geo_issues:
            report.append("🗺️  GEOGRAFISK KODING:")
            report.append("-" * 60)
            for issue in geo_issues:
                report.append(f"  {issue['column']}: {issue['issue']}")
                if 'example' in issue:
                    report.append(f"    Eksempel: {issue['example']}")
            report.append("")
        
        # Verdi-validering
        value_issues = self.validate_value_ranges(df)
        if value_issues:
            report.append("❌ VERDI-FEIL:")
            report.append("-" * 60)
            for issue in value_issues:
                report.append(f"  {issue['column']}: {issue['issue']}")
            report.append("")
        
        # Oppsummering
        total_issues = len(suggestions) + len(type_issues) + len(geo_issues) + len(value_issues)
        
        report.append("=" * 60)
        report.append(f"OPPSUMMERING:")
        report.append(f"  Forslag til standardisering: {len(suggestions)}")
        report.append(f"  Datatype-advarsler: {len(type_issues)}")
        report.append(f"  Geografisk koding-advarsler: {len(geo_issues)}")
        report.append(f"  Verdi-feil: {len(value_issues)}")
        report.append(f"  Totalt: {total_issues}")
        
        if total_issues == 0:
            report.append("")
            report.append("✅ TABELLEN ER GODKJENT!")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def standardize_dataframe(self, df: pd.DataFrame, auto_fix: bool = False) -> pd.DataFrame:
        """
        Standardiser DataFrame basert på kontrollskjema.
        
        Args:
            df: Input DataFrame
            auto_fix: Hvis True, gjør automatiske fikser
        
        Returns:
            Standardisert DataFrame
        """
        df_std = df.copy()
        
        # Standardiser kolonnenavn
        suggestions = self.suggest_column_standardization(df_std)
        if auto_fix and suggestions:
            df_std = df_std.rename(columns=suggestions)
            print(f"✓ Endret {len(suggestions)} kolonnenavn")
        
        # TODO: Flere automatiske fikser
        # - Konverter datatyper
        # - Standardiser verdier
        # - Fiks geografisk koding
        
        return df_std


def validate_file(file_path: str, table_name: str = None):
    """
    Valider en Excel-fil mot kontrollskjema.
    """
    if table_name is None:
        table_name = Path(file_path).stem
    
    df = pd.read_excel(file_path)
    
    validator = TableValidator()
    report = validator.generate_validation_report(df, table_name)
    
    print(report)
    
    # Generer også standardisert versjon
    suggestions = validator.suggest_column_standardization(df)
    if suggestions:
        print("\n" + "=" * 60)
        print("Vil du se en forhåndsvisning av standardisert versjon? (j/n)")
        # For nå, bare generer den
        df_std = validator.standardize_dataframe(df, auto_fix=True)
        print("\nStandardiserte kolonner:")
        print(df_std.columns.tolist())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Bruk: python validate_table.py <excel_file>")
        print("\nEksempel:")
        print("  python validate_table.py output_tabell.xlsx")
        sys.exit(1)
    
    file_path = sys.argv[1]
    table_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    validate_file(file_path, table_name)
