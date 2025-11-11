import pandas as pd
import re

df = pd.read_excel('training_data/OK-SYS002/OK-SYS002_input_1.xlsx')
df.columns = df.columns.str.lower()

def decode(val):
    if not isinstance(val, str):
        return val
    return re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), val)

df['aldgr16a__fmt'] = df['aldgr16a__fmt'].apply(decode)

print('Sysselsatte aldersgrupper:')
print(df['aldgr16a__fmt'].value_counts().sort_index())
print(f"\nTotalt: {len(df)} rader")
print(f"Unik kombinasjon (bydel × kjønn × alder): {df.groupby(['b_delbydel2017_01', 'kjoenn_fmt', 'aldgr16a__fmt']).ngroups}")
