"""
Konverterer Excel-fil med NAV TKNR-koder til JSON-kodeliste.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime


def create_tknr_codelist(excel_path: str, output_dir: str = "kodelister"):
    """
    Leser Excel-fil med TKNR-koder og lager JSON-kodeliste.
    
    Forventet Excel-struktur:
    - Tknr: NAV trygdekontornummer
    - PX-kode: PX-kode for statistikkbanken
    - SSB-kode: SSB standard kode
    - PX-navn: Navn som skal brukes i statistikkbanken
    """
    # Les Excel-fil
    df = pd.read_excel(excel_path)
    
    print(f"Lest {len(df)} rader fra {excel_path}")
    print(f"\nKolonner: {df.columns.tolist()}")
    print(f"\nData:")
    print(df)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Bygg mappings
    tknr_to_px = {}  # TKNR -> PX-kode
    tknr_to_ssb = {}  # TKNR -> SSB-kode
    px_labels = {}  # PX-kode -> Navn
    
    for _, row in df.iterrows():
        tknr = str(int(row['Tknr'])) if pd.notna(row['Tknr']) else None
        px_code = str(int(row['PX-kode'])) if pd.notna(row['PX-kode']) else None
        ssb_code = str(int(row['SSB-kode'])) if pd.notna(row['SSB-kode']) else None
        px_name = str(row['PX-navn']).strip() if pd.notna(row['PX-navn']) else ''
        
        if not tknr or not px_code:
            continue
        
        tknr_to_px[tknr] = px_code
        if ssb_code:
            tknr_to_ssb[tknr] = ssb_code
        if px_name:
            px_labels[px_code] = px_name
    
    # Lag kodeliste-struktur
    codelist = {
        "name": "nav_tknr_til_px",
        "description": "Mapping fra NAV TKNR (trygdekontornummer) til PX-kode for Oslo",
        "source": "NAV TKNR codes til PxWeb format",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        
        "source_column_patterns": [
            ".*tknr.*",
            ".*trygdekontor.*",
            ".*nav.*kontor.*"
        ],
        
        "target_column_patterns": [
            ".*px.*kode.*",
            ".*px.*code.*",
            ".*geografi.*",
            ".*bydel.*"
        ],
        
        "type": "mapping",
        "mappings": {
            "tknr_to_px": tknr_to_px,
            "tknr_to_ssb": tknr_to_ssb
        },
        "labels": px_labels
    }
    
    # Lagre til JSON
    filename = "NAV_TKNR_til_PX.json"
    output_file = output_path / filename
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(codelist, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Lagret {filename}")
    print(f"  - {len(tknr_to_px)} TKNR -> PX mappings")
    print(f"  - {len(tknr_to_ssb)} TKNR -> SSB mappings")
    print(f"  - {len(px_labels)} PX labels")
    print(f"\nEksempel mappings:")
    print(f"  TKNR -> PX: {list(tknr_to_px.items())[:3]}")
    print(f"  TKNR -> SSB: {list(tknr_to_ssb.items())[:3]}")
    print(f"  Labels: {list(px_labels.items())[:3]}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = "kodelister/geokoder_NAV_TKNR_til_PX.xlsx"
    
    create_tknr_codelist(excel_file)
    print("\n✅ Ferdig! Kodeliste lagret i kodelister/")
