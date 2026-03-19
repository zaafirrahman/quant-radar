import pandas as pd
from pathlib import Path

from us_market.analysis.single_sniper import run_single_sniper
import yfinance as yf


# ─────────────────────────────────────────
#  BULK SNIPER
# ─────────────────────────────────────────

def run_bulk_sniper(candidates_df: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, dict]:
    """
    Loop through sniper candidates, run single_sniper per ticker.

    Args:
        candidates_df : DataFrame from sniper_candidates.csv (must have 'Ticker' column)
        output_dir    : Path to us_market/output/sniper/

    Returns:
        summary_df    : DataFrame with one row per ticker (for bulk dashboard)
        results       : dict keyed by ticker → full single_sniper result dict
                        (for building individual HTML dashboards)
    """

    signals_dir = output_dir / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    results      = {}

    tickers = candidates_df["Ticker"].tolist()
    print(f"\n🎯 Running Bulk Sniper for {len(tickers)} candidates: {tickers}\n")

    for ticker in tickers:
        # Fetch company name
        try:
            info    = yf.Ticker(ticker).info
            company = info.get("longName", ticker)
        except Exception:
            company = ticker

        result = run_single_sniper(ticker, company)

        if result is None:
            print(f"  ⚠️  Skipping {ticker} — insufficient data\n")
            continue

        # ── Save per-ticker signals CSV ───────────────────────────────────────
        sig_path = signals_dir / f"{ticker}_signals.csv"
        result["signals"].to_csv(sig_path, index=False)
        print(f"  💾 Signals saved: {sig_path}")

        summary_rows.append(result["summary"])
        results[ticker] = result

    # ── Build & save summary CSV ──────────────────────────────────────────────
    if not summary_rows:
        print("❌ No valid sniper results.")
        return pd.DataFrame(), {}

    summary_df = pd.DataFrame(summary_rows)

    # Rank by Swing_Score descending
    summary_df = summary_df.sort_values("Sniper_Score", ascending=False).reset_index(drop=True)
    summary_df.insert(0, "Rank", summary_df.index + 1)

    summary_path = output_dir / "sniper_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\n📊 Sniper summary saved: {summary_path}")

    return summary_df, results