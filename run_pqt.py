# generate_tracking_html.py — run sekali untuk generate dari existing parquet
import pandas as pd
from pathlib import Path
from us_market.dashboard.html_builder import build_tracking_month, build_tracking_index

BASE_DIR     = Path("us_market")
tracking_dir = BASE_DIR / "output" / "tracking"
parquet_path = tracking_dir / "master.parquet"
json_dir     = tracking_dir / "json"
html_dir     = tracking_dir / "html"
json_dir.mkdir(exist_ok=True)
html_dir.mkdir(exist_ok=True)

df = pd.read_parquet(parquet_path)

# Generate per month
months = sorted(df["Date"].str[:7].unique(), reverse=True)
for month_key in months:
    mtd = df[df["Date"].str.startswith(month_key)]
    
    # JSON
    (json_dir / f"{month_key}.json").write_text(
        mtd.to_json(orient="records", date_format="iso")
    )
    
    # HTML
    html = build_tracking_month(mtd, month_key)
    (html_dir / f"{month_key}.html").write_text(html, encoding="utf-8")
    print(f"✅ {month_key} — {len(mtd)} rows")

# Index
index_html = build_tracking_index(months)
(html_dir / "index.html").write_text(index_html, encoding="utf-8")
print("✅ Index generated")