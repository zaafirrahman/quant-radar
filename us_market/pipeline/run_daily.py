from datetime import datetime
from pathlib import Path

from us_market.config.ticker_universe import US_TICKERS
from us_market.analysis.screener import run_screener
from us_market.dashboard.html_builder import build_radar_dashboard


def main():

    print("🚀 Running Quant Radar...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Resolve us_market root
    BASE_DIR = Path(__file__).resolve().parents[1]

    # Output folder
    output_dir = BASE_DIR / "output" / "radar"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run Screener
    report = run_screener(US_TICKERS)

    # Save full radar CSV
    csv_path = output_dir / "us_radar.csv"
    report.to_csv(csv_path, index=False)

    print(f"📊 Radar CSV saved: {csv_path}")

    # ===============================
    # SELECT TOP 5 FOR SNIPER
    # ===============================

    top5 = (
        report
        .sort_values("Quant_Score", ascending=False)
        .head(5)
    )

    sniper_path = output_dir / "sniper_candidates.csv"
    top5.to_csv(sniper_path, index=False)

    print("🎯 Top 5 candidates for Sniper:")
    print(top5[["Ticker", "Quant_Score"]])

    print(f"🧠 Sniper candidate list saved: {sniper_path}")

    # ===============================
    # BUILD DASHBOARD
    # ===============================

    html = build_radar_dashboard(report, timestamp)

    html_path = output_dir / "us_radar.html"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🌐 Dashboard saved: {html_path}")


if __name__ == "__main__":
    main()