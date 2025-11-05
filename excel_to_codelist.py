"""
Konverterer Excel-fil med geokoder til separate JSON-kodelister per geografisk nivå.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime


def create_codelist_from_excel(excel_path: str, output_dir: str = "kodelister"):
    """
    Leser Excel-fil med geokoder og lager separate JSON-kodelister for hvert geografisk nivå.
    
    Forventet Excel-struktur:
    - STP_kode: SSB standard kode
    - PX_value_text: Tekstverdi for PX
    - PX_agg_code: Aggregeringskode for PX
    - PX_value_code&text: Kombinert kode og tekst
    - Geo_nivå: Geografisk nivå (Kommune, Bydel, Grunnkrets, etc.)
    """
    # Les Excel-fil
    df = pd.read_excel(excel_path)
    
    print(f"Lest {len(df)} rader fra {excel_path}")
    print(f"\nKolonner: {df.columns.tolist()}")
    print(f"\nGeografiske nivåer funnet:")
    print(df['Geo_nivå'].value_counts())
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Grupper per geografisk nivå
    for geo_level in df['Geo_nivå'].unique():
        # Rett skrivefeil: Grunnkrektsområde → Grunnkretsområde
        geo_level_clean = geo_level.replace('Grunnkrekts', 'Grunnkrets')
        df_level = df[df['Geo_nivå'] == geo_level].copy()
        
        # Bygg mappings: SSB-kode -> PX-kode og labels
        mappings = {}
        labels = {}
        
        for _, row in df_level.iterrows():
            ssb_code = str(row['STP_kode']).strip()
            px_code = str(row['PX_agg_code']).strip() if pd.notna(row['PX_agg_code']) else ssb_code
            px_label = str(row['PX_value_text']).strip() if pd.notna(row['PX_value_text']) else ''
            
            # Håndter spesialtilfeller
            if ssb_code == 'nan':
                continue
            
            # For Oslo kommune: bruk "0301" som standard SSB-kode hvis STP_kode er "-"
            if ssb_code == '-' and geo_level == 'Kommune':
                ssb_code = '0301'
                
            if ssb_code == '-':
                continue
                
            mappings[ssb_code] = px_code
            labels[px_code] = px_label
        
        # Lag kodeliste-struktur
        codelist = {
            "name": f"geo_{geo_level_clean.lower().replace(' ', '_')}",
            "description": f"Mapping fra SSB-kode til PX-kode for geografisk nivå: {geo_level_clean}",
            "source": "SSB standard territorial codes til PxWeb format",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "geo_level": geo_level_clean,
            
            "source_column_patterns": [
                ".*stp.*kode.*",
                ".*ssb.*kode.*",
                ".*geo.*kode.*",
                f".*{geo_level_clean.lower()}.*kode.*"
            ],
            
            "target_column_patterns": [
                ".*px.*kode.*",
                ".*px.*code.*",
                ".*geografi.*",
                f".*{geo_level_clean.lower()}.*"
            ],
            
            "type": "mapping",
            "mappings": mappings,
            "labels": labels
        }
        
        # Lagre til JSON
        filename = f"SSB_til_PX_geo_{geo_level_clean.lower().replace(' ', '_')}.json"
        output_file = output_path / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(codelist, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Lagret {filename}")
        print(f"  - {len(mappings)} mappings")
        print(f"  - Eksempel: {list(mappings.items())[:3]}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = "kodelister/geokoder_SSB_til_px.xlsx"
    
    create_codelist_from_excel(excel_file)
    print("\n✅ Ferdig! Kodelister lagret i kodelister/")
