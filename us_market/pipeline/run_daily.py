from datetime import datetime
from pathlib import Path

from us_market.config.ticker_universe import US_TICKERS
from us_market.analysis.screener import run_screener
from us_market.analysis.bulk_sniper import run_bulk_sniper
from us_market.dashboard.html_builder import (
    build_radar_dashboard,
    build_bulk_dashboard,
    build_single_dashboard,
)


def main():

    print("🚀 Running Quant Radar Pipeline...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    BASE_DIR   = Path(__file__).resolve().parents[1]
    radar_dir  = BASE_DIR / "output" / "radar"
    sniper_dir = BASE_DIR / "output" / "sniper"
    html_dir   = sniper_dir / "html"

    radar_dir.mkdir(parents=True, exist_ok=True)
    sniper_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    #  1. SCREENER
    # ──────────────────────────────────────────
    print("\n📡 Running screener...")
    report = run_screener(US_TICKERS)

    csv_path = radar_dir / "us_radar.csv"
    report.to_csv(csv_path, index=False)
    print(f"📊 Radar CSV saved: {csv_path}")

    html = build_radar_dashboard(report, timestamp)
    html_path = radar_dir / "us_radar.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 Radar dashboard saved: {html_path}")

    # ──────────────────────────────────────────
    #  2. FILTER TOP 5 CANDIDATES
    # ──────────────────────────────────────────
    top5 = report.head(5)
    sniper_candidates_path = radar_dir / "sniper_candidates.csv"
    top5.to_csv(sniper_candidates_path, index=False)
    print(f"\n🎯 Top 5 candidates:")
    print(top5[["Ticker", "Quant_Score"]].to_string(index=False))
    print(f"🧠 Candidates saved: {sniper_candidates_path}")

    # ──────────────────────────────────────────
    #  3. BULK SNIPER
    # ──────────────────────────────────────────
    print("\n🔫 Running bulk sniper...")
    summary_df, results = run_bulk_sniper(top5, sniper_dir)

    if summary_df.empty:
        print("❌ No sniper results — skipping HTML generation.")
        return

    # ──────────────────────────────────────────
    #  4. BUILD HTML — BULK DASHBOARD
    # ──────────────────────────────────────────
    bulk_html = build_bulk_dashboard(summary_df, timestamp)
    bulk_path = sniper_dir / "index.html"
    with open(bulk_path, "w", encoding="utf-8") as f:
        f.write(bulk_html)
    print(f"\n🌐 Bulk dashboard saved: {bulk_path}")

    # ──────────────────────────────────────────
    #  5. BUILD HTML — SINGLE DASHBOARDS
    # ──────────────────────────────────────────
    for ticker, result in results.items():
        single_html = build_single_dashboard(result)
        single_path = html_dir / f"{ticker}.html"
        with open(single_path, "w", encoding="utf-8") as f:
            f.write(single_html)
        print(f"📄 Single dashboard saved: {single_path}")

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()