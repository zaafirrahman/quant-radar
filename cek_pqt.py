import pandas as pd
df = pd.read_parquet("us_market/output/tracking/master.parquet")
print(df.shape)
print(df)