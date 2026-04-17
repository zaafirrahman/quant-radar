"""
inference.py
============
Inference harian XGBoost classifier untuk prediksi IDX movers.

Logic:
  - Load model dari ml_data/model.json
  - Load IDX OHLCV terbaru (hari ini T)
  - Load US features terbaru (hari ini T)
  - Compute ticker-level features (ret_1d, ret_3d, vol_ratio, dll)
  - Predict: probabilitas next_day_ret > 3%
  - Output: top N tickers dengan probability tertinggi

Dijalankan: harian via GH Actions setelah append_daily.py
Output    : output/ml_signal_{date}.json & output/ml_signal_{date}.html
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

# ── Config ────────────────────────────────────────────────────────────────────
# Path resolution: selalu relatif terhadap lokasi script ini
SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR / "ml_data"
OUTPUT_DIR = SCRIPT_DIR / "output"

MODEL_FILE   = DATA_DIR / "model.json"
FEAT_FILE    = DATA_DIR / "feature_cols.json"
IDX_FILE     = DATA_DIR / "idx_ohlcv.parquet"
US_FILE      = DATA_DIR / "us_features.parquet"

TOP_N = 20        # Jumlah top tickers yang ditampilkan
THRESHOLD = 0.6   # Probability threshold untuk entry signal


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_model_and_features() -> tuple[xgb.XGBClassifier, list]:
    print("[1/4] Loading model and features...")

    model = xgb.XGBClassifier()
    model.load_model(MODEL_FILE)
    print(f"  Model loaded: {MODEL_FILE}")

    with open(FEAT_FILE, "r") as f:
        feature_cols = json.load(f)
    print(f"  Features   : {len(feature_cols)} columns")

    return model, feature_cols


def load_latest_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load IDX dan US data terbaru."""
    print("[2/4] Loading market data...")

    idx = pd.read_parquet(IDX_FILE)
    idx["date"] = pd.to_datetime(idx["date"])

    us = pd.read_parquet(US_FILE)
    us.index = pd.to_datetime(us.index)

    # Get latest dates
    idx_latest = idx["date"].max()
    us_latest = us.index.max()

    print(f"  IDX latest : {idx_latest.date()} ({idx[idx['date']==idx_latest]['ticker'].nunique()} tickers)")
    print(f"  US latest  : {us_latest.date()}")

    # Butuh minimal 20 hari data untuk compute rolling features (ret_20d, volatility_20d)
    # Ambil 90 hari terakhir untuk memastikan semua ticker punya cukup history
    idx_recent = idx[idx["date"] >= idx_latest - pd.Timedelta(days=90)].copy()

    return idx_recent, us


def compute_ticker_features(idx_recent: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ticker-level features untuk data terbaru.
    Perlu minimal beberapa hari data untuk compute returns.
    """
    idx_recent = idx_recent.sort_values(["ticker", "date"]).copy()

    def per_ticker(g):
        g = g.copy()
        c = g["close"]
        v = g["volume"]

        g["ret_1d"]  = c.pct_change(1) * 100
        g["ret_3d"]  = c.pct_change(3) * 100
        g["ret_5d"]  = c.pct_change(5) * 100
        g["ret_20d"] = c.pct_change(20) * 100

        g["vol_20d_avg"] = v.rolling(20).mean()
        g["vol_ratio"]   = v / g["vol_20d_avg"]

        g["volatility_20d"] = (c.pct_change() * 100).rolling(20).std()

        g["ma5"]  = c.rolling(5).mean()
        g["ma20"] = c.rolling(20).mean()
        g["above_ma5"]  = (c > g["ma5"]).astype(int)
        g["above_ma20"] = (c > g["ma20"]).astype(int)

        return g

    # Simpan ticker sebagai index agar tidak hilang, lalu reset setelah apply
    result = idx_recent.groupby("ticker", group_keys=False).apply(per_ticker)
    # Reset index untuk mendapatkan kembali kolom ticker
    result = result.reset_index()
    return result


def build_inference_dataset(
    idx_featured: pd.DataFrame,
    us: pd.DataFrame,
    feature_cols: list,
) -> pd.DataFrame:
    """
    Join IDX features dengan US features untuk inference.
    """
    print("[3/4] Building inference dataset...")

    # Get latest date dari IDX
    latest_date = idx_featured["date"].max()

    # Filter hanya latest date
    df_latest = idx_featured[idx_featured["date"] == latest_date].copy()

    # US features: ambil yang terbaru (tanggal yang sama atau sebelumnya)
    us_sorted = us.sort_index()
    us_date = us_sorted.index[us_sorted.index <= latest_date].max()
    us_row = us_sorted.loc[[us_date]].iloc[0]

    print(f"  IDX date   : {latest_date.date()}")
    print(f"  US date    : {us_date.date()}")

    # Extract US features yang dibutuhkan
    us_feature_cols = [c for c in feature_cols if c in us_row.index]
    us_values = {c: us_row[c] for c in us_feature_cols}

    # Add US features ke setiap row
    for col, val in us_values.items():
        df_latest[col] = val

    # Drop rows dengan NaN di CRITICAL feature columns (core IDX features)
    # Rolling features seperti ret_20d, volatility_20d butuh 20 hari data
    # Ticker baru/listing mungkin belum punya cukup data -> skip saja
    idx_feature_cols = [c for c in feature_cols if c not in us_feature_cols]
    critical_features = [c for c in idx_feature_cols if c in df_latest.columns]

    # Hanya drop NaN di fitur yang tersedia, isi NaN sisanya dengan median
    before = len(df_latest)
    df_latest = df_latest.dropna(subset=critical_features)
    dropped = before - len(df_latest)

    # Isi NaN yang tersisa dengan median (untuk fitur opsional)
    for col in feature_cols:
        if col in df_latest.columns and df_latest[col].isna().any():
            df_latest[col] = df_latest[col].fillna(df_latest[col].median())

    print(f"  Valid tickers: {len(df_latest)} (dropped {dropped} due to missing data)")

    return df_latest


def run_inference(
    df: pd.DataFrame,
    model: xgb.XGBClassifier,
    feature_cols: list,
) -> pd.DataFrame:
    """
    Run inference dan return predictions.
    """
    print("[4/4] Running inference...")

    # Prepare X dengan column order yang sama seperti training
    X = df[feature_cols].copy()
    X = X.fillna(X.median())

    # Predict probabilities
    probs = model.predict_proba(X)[:, 1]

    df_result = df[["ticker", "date", "close", "volume"]].copy()
    df_result["probability"] = probs
    df_result["signal"] = (probs >= THRESHOLD).astype(int)

    # Sort by probability descending
    df_result = df_result.sort_values("probability", ascending=False)

    # Top N
    top_n = df_result.head(TOP_N)

    print(f"\n  Top {TOP_N} tickers by probability:")
    print(f"  {'Rank':<5} {'Ticker':<10} {'Close':<10} {'Probability':<12} {'Signal'}")
    print(f"  {'-'*50}")
    for i, row in top_n.iterrows():
        signal_icon = "YES" if row["signal"] == 1 else "no"
        print(f"  {i+1:<5} {row['ticker']:<10} {row['close']:<10.2f} {row['probability']:<12.4f} {signal_icon}")

    # Summary stats
    high_prob = df_result[df_result["probability"] >= THRESHOLD]
    print(f"\n  Signal summary:")
    print(f"    Tickers dengan prob >= {THRESHOLD:.1f}: {len(high_prob)}")
    print(f"    Avg probability: {df_result['probability'].mean():.4f}")
    print(f"    Max probability: {df_result['probability'].max():.4f}")

    return df_result


def save_outputs(df_result: pd.DataFrame) -> None:
    """Save predictions ke JSON dan HTML."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")

    # JSON output
    json_file = OUTPUT_DIR / f"ml_signal_{date_str}.json"
    records = df_result.to_dict(orient="records")
    # Convert numpy types to native Python
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, (np.floating, np.integer)):
                rec[k] = float(v) if isinstance(v, np.floating) else int(v)
            elif isinstance(v, pd.Timestamp):
                rec[k] = v.isoformat()

    with open(json_file, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\n  [OK] JSON: {json_file}")

    # HTML output
    html_file = OUTPUT_DIR / f"ml_signal_{date_str}.html"
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>IDX ML Signal — {date_str}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 800px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        .signal-yes {{ background: #d4edda; color: #155724; font-weight: bold; }}
        .prob-high {{ color: #dc3545; font-weight: bold; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <h1>IDX ML Signal — {date_str}</h1>
    <p class="meta">Generated: {datetime.now(timezone.utc).isoformat()}</p>
    <p class="meta">Model: XGBoost | Threshold: {THRESHOLD} | Top N: {TOP_N}</p>

    <h2>Top {TOP_N} Tickers</h2>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Ticker</th>
                <th>Close</th>
                <th>Probability</th>
                <th>Signal</th>
            </tr>
        </thead>
        <tbody>
"""
    for i, row in df_result.head(TOP_N).iterrows():
        signal_class = "signal-yes" if row["signal"] == 1 else ""
        prob_class = "prob-high" if row["probability"] >= THRESHOLD else ""
        signal_text = "YES" if row["signal"] == 1 else "no"
        html_content += f"""
            <tr>
                <td>{i+1}</td>
                <td>{row['ticker']}</td>
                <td>{row['close']:.2f}</td>
                <td class="{prob_class}">{row['probability']:.4f}</td>
                <td class="{signal_class}">{signal_text}</td>
            </tr>
"""
    html_content += """
        </tbody>
    </table>

    <h2>Summary</h2>
    <ul>
"""
    high_prob = df_result[df_result["probability"] >= THRESHOLD]
    html_content += f"""
        <li>Tickers dengan prob >= {THRESHOLD}: <strong>{len(high_prob)}</strong></li>
        <li>Avg probability: <strong>{df_result['probability'].mean():.4f}</strong></li>
        <li>Max probability: <strong>{df_result['probability'].max():.4f}</strong></li>
    </ul>
</body>
</html>
"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [OK] HTML: {html_file}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"{'='*60}")
    print(f"  Quant Radar — IDX ML Inference")
    print(f"  Model  : XGBoost Classifier")
    print(f"  Output : Top {TOP_N} tickers with probability >= {THRESHOLD}")
    print(f"{'='*60}\n")

    model, feature_cols = load_model_and_features()
    idx_recent, us = load_latest_data()
    idx_featured = compute_ticker_features(idx_recent)
    df_inference = build_inference_dataset(idx_featured, us, feature_cols)
    df_result = run_inference(df_inference, model, feature_cols)
    save_outputs(df_result)

    print(f"\n{'='*60}")
    print(f"  DONE — Signals ready for review")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
