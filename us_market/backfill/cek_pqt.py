import pandas as pd
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "output" / "tracking" / "master.parquet"
print("Looking at:", path)
print("Exists:", path.exists())

df = pd.read_parquet(path)
print(df.shape)
print(df)