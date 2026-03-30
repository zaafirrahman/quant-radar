import pytz
import shutil
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

from us_market.config.ticker_universe import US_TICKERS
from us_market.analysis.screener import run_screener
from us_market.analysis.bulk_sniper import run_bulk_sniper
from us_market.dashboard.html_builder import (
    build_radar_dashboard,
    build_bulk_dashboard,
    build_single_dashboard,
    build_tracking_index,
    build_tracking_month,
)
from us_market.dashboard.porto_builder import build_porto_dashboard
from us_market.pipeline.tracking_helper import _append_tracking
from us_market.execution.run_execution import run_execution
from us_market.execution.build_execution_dashboard import build_execution_dashboard


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

def main():

    print("🚀 Running Quant Radar Pipeline...")
    edt       = pytz.timezone("US/Eastern")
    now_edt   = datetime.now(edt)
    timestamp = now_edt.strftime("%Y-%m-%d %H:%M:%S")
    today     = now_edt.strftime("%Y-%m-%d")

    BASE_DIR      = Path(__file__).resolve().parents[1]
    radar_dir     = BASE_DIR / "output" / "radar"
    sniper_dir    = BASE_DIR / "output" / "sniper"
    html_dir      = sniper_dir / "html"
    tracking_dir  = BASE_DIR / "output" / "tracking"

    radar_dir.mkdir(parents=True, exist_ok=True)
    sniper_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)
    tracking_dir.mkdir(parents=True, exist_ok=True)

    # Clear stale sniper outputs
    for f in html_dir.glob("*.html"):
        f.unlink()

    signals_dir = sniper_dir / "signals"
    if signals_dir.exists():
        shutil.rmtree(signals_dir)
        signals_dir.mkdir()

    summary_path = sniper_dir / "sniper_summary.csv"
    if summary_path.exists():
        summary_path.unlink()

    # ── 1. Screener ───────────────────────────────────────────────────────────
    print("\n📡 Running screener...")
    report = run_screener(US_TICKERS)

    csv_path = radar_dir / "us_radar.csv"
    report.to_csv(csv_path, index=False)
    print(f"📊 Radar CSV saved: {csv_path}")

    html = build_radar_dashboard(report, timestamp)
    with open(radar_dir / "us_radar.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 Radar dashboard saved")

    # ── 2. Filter candidates ──────────────────────────────────────────────────
    candidates = report[report["Distance_%"] > 0].copy()
    candidates.to_csv(radar_dir / "sniper_candidates.csv", index=False)
    print(f"\n🎯 Candidates (Distance > 0): {len(candidates)}")
    print(candidates[["Ticker", "Radar_Score", "Distance_%"]].to_string(index=False))

    if candidates.empty:
        print("⚠️  No candidates today — skipping sniper, porto & tracking.")
        return

    # ── 3. Bulk sniper ────────────────────────────────────────────────────────
    print("\n🔫 Running bulk sniper...")
    summary_df, results = run_bulk_sniper(candidates, sniper_dir)

    if summary_df.empty:
        print("❌ No sniper results.")
        return

    # ── 4. Bulk dashboard ─────────────────────────────────────────────────────
    bulk_html = build_bulk_dashboard(summary_df, timestamp)
    with open(sniper_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(bulk_html)
    print(f"\n🌐 Bulk dashboard saved")

    # ── 5. Single dashboards ──────────────────────────────────────────────────
    for ticker, result in results.items():
        single_html = build_single_dashboard(result)
        with open(html_dir / f"{ticker}.html", "w", encoding="utf-8") as f:
            f.write(single_html)
        print(f"📄 {ticker}.html saved")

    # ── 6. Tracking ───────────────────────────────────────────────────────────
    if now_edt.weekday() >= 5:
        print("\n⚠️  Weekend detected (EDT) — skipping tracking append.")
    else:
        print("\n📊 Updating tracking data...")
        _append_tracking(summary_df, report, today, tracking_dir)

    # ── 7. Porto Builder ──────────────────────────────────────────────────────
    print("\n🏗️  Building porto dashboard...")
    portfolio_dir = BASE_DIR / "output" / "portfolio"
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    porto_html = build_porto_dashboard(summary_df, timestamp)
    with open(portfolio_dir / "porto_builder.html", "w", encoding="utf-8") as f:
        f.write(porto_html)
    print(f"🌐 Porto builder saved → output/portfolio/porto_builder.html")

    print("\n✅ Pipeline complete!")

    # ── 8. Execution Bot ─────────────────────────────────────────────────────
    print("\n⚡ Running execution engine...")
    execution_dir = BASE_DIR / "output" / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)
 
    try:
        run_execution(summary_df=summary_df, today_str=today)
        exec_html = build_execution_dashboard(timestamp=timestamp)
        print("✅ Execution dashboard updated")
    except Exception as e:
        print(f"⚠️  Execution engine error: {e}")


if __name__ == "__main__":
    main()