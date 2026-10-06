import sys
sys.path.insert(0, '.')
from src import data_loader
import pandas as pd

print('Testing load_enriched with Finance Plan...')
df = data_loader.load_enriched()
print(f'Enriched shape: {df.shape}')
if 'FinanceTarget' in df.columns:
    print(f'FinanceTarget non-null: {df["FinanceTarget"].notna().sum()}')
    print(f'FinanceTarget sum: {df["FinanceTarget"].sum()}')
    print(f'FinanceForecast sum: {df["FinanceForecast"].sum()}')
    print(f'Variance sum: {df["Variance"].sum()}')
    print(f'VariancePct sample: {df["VariancePct"].head()}')