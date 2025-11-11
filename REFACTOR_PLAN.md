"""
NY REKKEFØLGE for generate_multi_input_script - PLAN

Nåværende (problematisk):
1. Les inputs (rå Excel)
2. FASE 1: Variabel-par deteksjon (per input)
3. FASE 2: Kolonnemapping (hver input → output)  ← FEIL!
4. FASE 3: Multi-input nøkkelanalyse
5. FASE 4: Aggregering (input1 → output)  ← FEIL!

Ny rekkefølge (brukerforslag):
1. Undersøk antall inputs
2. ENCODE alle inputs (XML-decode, normalize)
3. MERGE (hvis flere inputs) → df_merged
4. Variabel-par og statistikkvariabel-deteksjon (på df_merged!)
5. Kolonnemapping (df_merged → output)
6. Aggregering (df_merged → output) 
7. Andeler (ved behov)

Implementasjonsstrategi:
- STEG 1-2: Gjøres før analyse (i kode-flyt)
- STEG 3: simulate_merge() - allerede laget
- STEG 4-7: Kjøres på analysis_df (merged eller single input)

For single-input:
- Skip merge
- Analyser direkte på input (backward compatible)

For multi-input:
- Merge først
- Analyser merged
- Mapping blir: merged → output (ikke input1 → output)

Endringer nødvendig:
1. Flytt Excel-lesing + encoding først
2. Legg til merge-simulering
3. Oppdater FASE 1 til å bruke analysis_df
4. Oppdater FASE 2 (mapping) til å bruke analysis_df
5. Oppdater FASE 4 (aggregering) til å bruke analysis_df
6. Oppdater script-generering til å reflektere ny rekkefølge

Backward compatibility:
- Single-input: Fungerer som før (analyser per input)
- Multi-input: Ny metode (analyser merged)
"""
