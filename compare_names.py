import json

# Last inn begge kodelister
with open('kodelister/NAV_TKNR_til_PX.json', encoding='utf-8') as f:
    tknr = json.load(f)

with open('kodelister/SSB_til_PX_geo_bydel.json', encoding='utf-8') as f:
    ssb = json.load(f)

print("=" * 60)
print("SAMMENLIGNING AV BYDELSNAVNE")
print("=" * 60)

# Samle alle PX-koder (unntatt Oslo i alt)
tknr_labels = {k: v for k, v in tknr['labels'].items() if k != '100000'}
ssb_labels = ssb['labels']

print(f"\nTKNR har {len(tknr_labels)} bydeler")
print(f"SSB har {len(ssb_labels)} bydeler")

# Sammenlign navn for hver PX-kode
print("\nPX-kode | TKNR navn          | SSB navn           | Match?")
print("-" * 60)

all_codes = sorted(set(list(tknr_labels.keys()) + list(ssb_labels.keys())), key=lambda x: int(x))

differences = []
for code in all_codes:
    tknr_name = tknr_labels.get(code, "MANGLER")
    ssb_name = ssb_labels.get(code, "MANGLER")
    match = "✓" if tknr_name == ssb_name else "✗"
    
    print(f"{code:7} | {tknr_name:18} | {ssb_name:18} | {match}")
    
    if tknr_name != ssb_name and tknr_name != "MANGLER" and ssb_name != "MANGLER":
        differences.append((code, tknr_name, ssb_name))

if differences:
    print("\n" + "=" * 60)
    print("FORSKJELLER FUNNET:")
    print("=" * 60)
    for code, tknr_name, ssb_name in differences:
        print(f"PX-kode {code}:")
        print(f"  TKNR: '{tknr_name}'")
        print(f"  SSB:  '{ssb_name}'")
else:
    print("\n✓ Alle navn er identiske!")
