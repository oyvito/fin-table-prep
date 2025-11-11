"""
Test-script for å utvikle og teste aggregeringslogikk isolert.

INPUT (fra FASE 4 deteksjon):
- df_base: DataFrame klart for aggregering
- aggregeringer: Liste med dict som beskriver hver aggregering:
  {
    'kolonne': 'bosted',
    'type': 'geography_rollup',
    'total_verdi': 301,
    'total_label': '0301 Oslo'
  }

OUTPUT:
- df_final: DataFrame med basis + alle aggregeringer utført

Dette scriptet tester forskjellige strategier for å UTFØRE aggregeringene
(deteksjon er allerede gjort i FASE 4).
"""

import sys
import io
import pandas as pd

# UTF-8 encoding setup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_aggregering_strategi_1(df_base, agg_list):
    """
    Strategi 1: Sekvensiell aggregering (feil - lager kryssaggregering)
    
    Problem: Aggregerer første variabel, deretter andre variabel på 
    det kombinerte datasettet → lager uønsket kryssaggregering.
    """
    print("\n=== STRATEGI 1: Sekvensiell aggregering ===")
    print(f"Basis: {len(df_base)} rader")
    
    df_result = df_base.copy()
    
    for agg in agg_list:
        kolonne = agg['kolonne']
        total_verdi = agg['total_verdi']
        total_label = agg['total_label']
        
        # Gruppér på alt UNNTATT denne kolonnen
        group_cols = [c for c in df_result.columns 
                     if c not in [kolonne, 'antall'] and not c.endswith('.1')]
        
        df_total = df_result.groupby(group_cols, dropna=False).agg({'antall': 'sum'}).reset_index()
        df_total[kolonne] = total_verdi
        df_total[f'{kolonne}.1'] = total_label
        
        print(f"  Aggregering på '{kolonne}': +{len(df_total)} rader")
        
        # Legg til i resultatet (PROBLEM: inkluderer tidligere aggregeringer!)
        df_result = pd.concat([df_result, df_total], ignore_index=True)
        print(f"  Totalt nå: {len(df_result)} rader")
    
    return df_result


def test_aggregering_strategi_2(df_base, agg_list):
    """
    Strategi 2: Parallell aggregering + kryssaggregering
    
    Hver aggregering gjøres fra basis. Deretter lages alle kombinasjoner
    av totalkategorier (kryssaggregeringer).
    """
    print("\n=== STRATEGI 2: Parallell + kryssaggregering ===")
    print(f"Basis: {len(df_base)} rader")
    
    agg_results = []
    
    # 1. Lag hver enkelt aggregering fra basis
    for agg in agg_list:
        kolonne = agg['kolonne']
        total_verdi = agg['total_verdi']
        total_label = agg['total_label']
        
        group_cols = [c for c in df_base.columns 
                     if c not in [kolonne, 'antall'] and not c.endswith('.1')]
        
        df_total = df_base.groupby(group_cols, dropna=False).agg({'antall': 'sum'}).reset_index()
        df_total[kolonne] = total_verdi
        df_total[f'{kolonne}.1'] = total_label
        
        print(f"  Aggregering på '{kolonne}': {len(df_total)} rader")
        agg_results.append(df_total)
    
    # 2. Lag kryssaggregeringer (alle kombinasjoner av totalkategorier)
    if len(agg_list) >= 2:
        # Gruppér på dimensjoner som IKKE aggregeres
        agg_kolonner = [agg['kolonne'] for agg in agg_list]
        group_cols = [c for c in df_base.columns 
                     if c not in agg_kolonner + ['antall'] and not c.endswith('.1')]
        
        df_cross = df_base.groupby(group_cols, dropna=False).agg({'antall': 'sum'}).reset_index()
        
        # Sett totalkategorier for alle aggregerte dimensjoner
        for agg in agg_list:
            df_cross[agg['kolonne']] = agg['total_verdi']
            df_cross[f"{agg['kolonne']}.1"] = agg['total_label']
        
        print(f"  Kryssaggregering: {len(df_cross)} rader")
        agg_results.append(df_cross)
    
    # 3. Kombiner alt
    df_result = pd.concat([df_base] + agg_results, ignore_index=True)
    print(f"Totalt: {len(df_result)} rader")
    
    return df_result


def test_aggregering_strategi_3(df_base, agg_list):
    """
    Strategi 3: Sekvensiell med filter (unngå dobbel-aggregering)
    
    Aggregerer sekvensiellt, men filtrerer bort allerede aggregerte verdier
    før neste aggregering.
    """
    print("\n=== STRATEGI 3: Sekvensiell med filter ===")
    print(f"Basis: {len(df_base)} rader")
    
    df_result = df_base.copy()
    total_verdier = {}  # Holder styr på total-verdier per kolonne
    
    for agg in agg_list:
        kolonne = agg['kolonne']
        total_verdi = agg['total_verdi']
        total_label = agg['total_label']
        
        total_verdier[kolonne] = total_verdi
        
        # Filtrer bort rader som allerede har total-verdier
        df_original = df_result.copy()
        for col, tot_val in total_verdier.items():
            if col != kolonne:  # Ikke filtrer på kolonnen vi skal aggregere nå
                df_original = df_original[df_original[col] != tot_val]
        
        print(f"  Filtrert datasett: {len(df_original)} rader (ekskl. tidligere totaler)")
        
        # Gruppér på alt UNNTATT denne kolonnen
        group_cols = [c for c in df_original.columns 
                     if c not in [kolonne, 'antall'] and not c.endswith('.1')]
        
        df_total = df_original.groupby(group_cols, dropna=False).agg({'antall': 'sum'}).reset_index()
        df_total[kolonne] = total_verdi
        df_total[f'{kolonne}.1'] = total_label
        
        print(f"  Aggregering på '{kolonne}': +{len(df_total)} rader")
        
        # Legg til i resultatet
        df_result = pd.concat([df_result, df_total], ignore_index=True)
        print(f"  Totalt nå: {len(df_result)} rader")
    
    return df_result


def sammenlign_med_output(df_result, strategi_navn):
    """
    Sammenligner resultat med forventet output
    """
    df_expected = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
    
    print(f"\n{'='*60}")
    print(f"RESULTAT: {strategi_navn}")
    print(f"{'='*60}")
    print(f"Forventet: {len(df_expected)} rader")
    print(f"Generert:  {len(df_result)} rader")
    print(f"Differanse: {len(df_result) - len(df_expected)} rader")
    
    if len(df_result) == len(df_expected):
        print("✅ PERFEKT MATCH på antall rader!")
    else:
        diff_pct = (len(df_result) / len(df_expected) - 1) * 100
        print(f"❌ Avvik: {diff_pct:+.1f}%")
    
    # Analyser kombinasjoner
    print(f"\nKombinasjon av bosted × kjønn:")
    combo_expected = df_expected.groupby(['bosted', 'kjønn']).size().reset_index(name='count')
    combo_result = df_result.groupby(['bosted', 'kjønn']).size().reset_index(name='count')
    
    print("\nForventet:")
    print(combo_expected.to_string(index=False))
    print(f"\nGenerert:")
    print(combo_result.to_string(index=False))
    
    return len(df_result) == len(df_expected)


if __name__ == "__main__":
    # Les basis-data - bruker OUTPUT-strukturen (etter transformasjon, før aggregering)
    # I virkeligheten vil generate_prep_script ha transformert input → output-struktur først
    df_output_full = pd.read_excel('training_data/OK-BEF001/ok-bef001_output.xlsx')
    
    # Simuler df_base: Output UTEN aggregeringer (kun detail-nivå)
    # Filtrer bort Oslo i alt (301) og Begge kjønn (3)
    df_base = df_output_full[(df_output_full['bosted'] != 301) & 
                             (df_output_full['kjønn'] != 3)].copy()
    
    print(f"Output full (med aggregeringer): {len(df_output_full)} rader")
    print(f"Basis (detail-nivå kun): {len(df_base)} rader")
    
    # Aggregeringsbeskrivelser (fra FASE 4 deteksjon)
    aggregeringer = [
        {
            'kolonne': 'bosted',
            'type': 'geography_rollup',
            'total_verdi': 301,
            'total_label': '0301 Oslo'
        },
        {
            'kolonne': 'kjønn',
            'type': 'binary_total',
            'total_verdi': 3,
            'total_label': 'Begge kjønn'
        }
    ]
    
    print("="*60)
    print("TEST AV AGGREGERINGSSTRATEGIER")
    print("="*60)
    print(f"Basis-data: {len(df_base)} rader")
    print(f"Aggregeringer å utføre: {len(aggregeringer)}")
    for agg in aggregeringer:
        print(f"  - {agg['kolonne']}: {agg['type']} → {agg['total_label']}")
    
    # Test alle strategier
    results = {}
    
    # Strategi 1: Sekvensiell (lager feil)
    df1 = test_aggregering_strategi_1(df_base, aggregeringer)
    results['Strategi 1'] = sammenlign_med_output(df1, "Strategi 1: Sekvensiell")
    
    # Strategi 2: Parallell + kryssaggregering
    df2 = test_aggregering_strategi_2(df_base, aggregeringer)
    results['Strategi 2'] = sammenlign_med_output(df2, "Strategi 2: Parallell + kryss")
    
    # Strategi 3: Sekvensiell med filter
    df3 = test_aggregering_strategi_3(df_base, aggregeringer)
    results['Strategi 3'] = sammenlign_med_output(df3, "Strategi 3: Sekvensiell med filter")
    
    # Oppsummering
    print("\n" + "="*60)
    print("OPPSUMMERING")
    print("="*60)
    for strategi, success in results.items():
        status = "✅ PERFEKT" if success else "❌ FEIL"
        print(f"{strategi}: {status}")
