import pandas as pd

actual = pd.read_excel('training_data/OK-SYS002/OK-SYS002_output.xlsx')
test = pd.read_excel('training_data/OK-SYS002/OK-SYS002_test_output.xlsx')

print('=== ACTUAL OUTPUT ===')
print(f'Rader: {len(actual)}')
print(f'Kolonner: {list(actual.columns)}')
print(f'Aldersgrupper: {sorted(actual["aldersgrupper"].unique())}')
print(f'År: {sorted(actual["aargang"].unique())}')

print('\n=== TEST OUTPUT ===')
print(f'Rader: {len(test)}')
print(f'Kolonner: {list(test.columns)}')
print(f'Aldersgrupper: {sorted(test["aldersgrupper"].unique())}')
print(f'År: {sorted(test["aargang"].unique())}')

print('\n=== DIFFERANSE ===')
print(f'Mangler {len(actual) - len(test)} rader')

# Sjekk om "Alder i alt" mangler
print(f'\nActual har "Alder i alt": {"Alder i alt" in actual["aldersgrupper"].values}')
print(f'Test har "Alder i alt": {"Alder i alt" in test["aldersgrupper"].values}')
