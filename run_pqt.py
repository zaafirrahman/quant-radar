# regen_tracking.py — taruh di root, run sekali, hapus setelahnya
import pandas as pd
from pathlib import Path
from us_market.dashboard.html_builder import build_tracking_month, build_tracking_index

BASE_DIR     = Path("us_market")
tracking_dir = BASE_DIR / "output" / "tracking"
parquet_path = tracking_dir / "master.parquet"
json_dir     = tracking_dir / "json"
html_dir     = tracking_dir / "html"

df     = pd.read_parquet(parquet_path)
months = sorted(df["Date"].str[:7].unique(), reverse=True)

for month_key in months:
    mtd  = df[df["Date"].str.startswith(month_key)]
    html = build_tracking_month(mtd, month_key)
    (html_dir / f"{month_key}.html").write_text(html, encoding="utf-8")
    print(f"✅ {month_key} regenerated — {len(mtd)} rows")

index_html = build_tracking_index(months)
(html_dir / "index.html").write_text(index_html, encoding="utf-8")
print("✅ Index regenerated")