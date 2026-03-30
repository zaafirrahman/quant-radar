import os
import pandas as pd
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "output" / "tracking" / "master.parquet"
print("Looking at:", path)
print("Exists:", path.exists())

# Check Parquet file
# df = pd.read_parquet(path)
# print(df.shape)
# print(df)

# Best sniper check
df = pd.read_parquet(path)
df['Date'] = pd.to_datetime(df['Date'])
target_date = '2026-03-27'
df_date = df[df['Date'] == target_date]
top_5_sniper = df_date.nlargest(5, 'Sniper_Score')
print(f"--- Top 5 Sniper Score pada {target_date} ---")
print(top_5_sniper[['Ticker', 'Sniper_Score', 'Radar_Score', 'Price']])