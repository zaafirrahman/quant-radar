from datetime import datetime
from pathlib import Path

from us_market.config.ticker_universe import US_TICKERS
from us_market.analysis.screener import run_screener
from us_market.dashboard.html_builder import build_radar_dashboard


def main():

    print("🚀 Running Quant Radar...")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === Resolve us_market root ===
    BASE_DIR = Path(__file__).resolve().parents[1]

    # === Output folder inside us_market ===
    output_dir = BASE_DIR / "output" / "radar"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run Screener
    report = run_screener(US_TICKERS)

    # Save CSV
    csv_path = output_dir / "us_radar.csv"
    report.to_csv(csv_path, index=False)

    print(f"📊 Radar CSV saved: {csv_path}")

    # Build HTML dashboard
    html = build_radar_dashboard(report, timestamp)

    html_path = output_dir / "us_radar.html"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🌐 Dashboard saved: {html_path}")


if __name__ == "__main__":
    main()