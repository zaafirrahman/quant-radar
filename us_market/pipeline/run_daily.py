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


# ─────────────────────────────────────────
#  TRACKING HELPER
# ─────────────────────────────────────────

def _append_tracking(summary_df: pd.DataFrame, report: pd.DataFrame,
                     today: str, tracking_dir: Path):
    """Append today's data to master parquet and update MTD JSON + HTML.
    
    Includes:
    - Candidates (distance > 0) with full sniper score
    - Tickers seen in last 20 trading days (price tracking only, no sniper)
    """

    parquet_path = tracking_dir / "master.parquet"
    json_dir     = tracking_dir / "json"
    html_dir     = tracking_dir / "html"
    json_dir.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    # ── Load existing parquet ─────────────────────────────────────────────────
    existing = pd.read_parquet(parquet_path) if parquet_path.exists() else pd.DataFrame()

    # ── Build radar lookup ────────────────────────────────────────────────────
    radar_lookup = report.set_index("Ticker")[["Radar_Score", "Distance_%", "Last_Price"]].to_dict("index")

    # ── Candidates today (distance > 0) ──────────────────────────────────────
    candidate_tickers = set(summary_df["Ticker"].tolist())
    rows = []

    for _, row in summary_df.iterrows():
        ticker = row["Ticker"]
        r      = radar_lookup.get(ticker, {})
        price  = float(r.get("Last_Price", 0)) if r.get("Last_Price") else None

        price_change = None
        if not existing.empty and price:
            prev = existing[existing["Ticker"] == ticker].sort_values("Date")
            if not prev.empty:
                prev_price   = float(prev["Price"].iloc[-1])
                price_change = round((price / prev_price - 1) * 100, 2) if prev_price else None

        rows.append({
            "Date":         today,
            "Ticker":       ticker,
            "Radar_Score":  round(float(r.get("Radar_Score", 0)), 4),
            "Distance_%":   round(float(r.get("Distance_%", 0)), 2),
            "Price":        price,
            "Price_Change": price_change,
            "Sniper_Score": float(row["Sniper_Score"]),
        })

    # ── 20d window tickers (previously seen, not candidate today) ────────────
    if not existing.empty:
        cutoff = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=28)).strftime("%Y-%m-%d")
        recent_tickers = set(
            existing[existing["Date"] >= cutoff]["Ticker"].unique()
        ) - candidate_tickers  # exclude today's candidates, already handled

        if recent_tickers:
            # Download prices for these tickers
            print(f"  📡 Fetching prices for {len(recent_tickers)} tracked tickers (20d window)...")
            try:
                price_data = yf.download(
                    list(recent_tickers),
                    period="5d",
                    interval="1d",
                    progress=False,
                    group_by="ticker",
                    threads=True,
                )

                for ticker in recent_tickers:
                    try:
                        if isinstance(price_data.columns, pd.MultiIndex):
                            tk_data = price_data.xs(ticker, axis=1, level=0).dropna()
                        else:
                            tk_data = price_data.dropna()

                        if tk_data.empty:
                            continue

                        price = float(tk_data["Close"].iloc[-1])

                        # Price change vs prev day in parquet
                        price_change = None
                        prev = existing[existing["Ticker"] == ticker].sort_values("Date")
                        if not prev.empty:
                            prev_price   = float(prev["Price"].iloc[-1])
                            price_change = round((price / prev_price - 1) * 100, 2) if prev_price else None

                        # Radar score for today (may be negative = signal faded)
                        r = radar_lookup.get(ticker, {})

                        rows.append({
                            "Date":         today,
                            "Ticker":       ticker,
                            "Radar_Score":  round(float(r.get("Radar_Score", 0)), 4) if r else None,
                            "Distance_%":   round(float(r.get("Distance_%", 0)), 2) if r else None,
                            "Price":        round(price, 2),
                            "Price_Change": price_change,
                            "Sniper_Score": None,  # no sniper if not candidate
                        })

                    except Exception:
                        continue

            except Exception as ex:
                print(f"  ⚠️  Price fetch for tracked tickers failed: {ex}")

    if not rows:
        print("  ⚠️  No rows to append to tracking.")
        return

    new_df = pd.DataFrame(rows)

    # ── Append to parquet ─────────────────────────────────────────────────────
    if not existing.empty:
        combined = existing[existing["Date"] != today]
        combined = pd.concat([combined, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_parquet(parquet_path, index=False)
    print(f"  🗄️  Parquet updated: {len(combined)} total rows ({len(rows)} today)")

    # ── MTD JSON ──────────────────────────────────────────────────────────────
    month_key = today[:7]
    mtd       = combined[combined["Date"].str.startswith(month_key)]
    json_path = json_dir / f"{month_key}.json"
    mtd.to_json(json_path, orient="records", date_format="iso")
    print(f"  📄 MTD JSON updated: {json_path}")

    # ── MTD HTML ──────────────────────────────────────────────────────────────
    html_path  = html_dir / f"{month_key}.html"
    month_html = build_tracking_month(mtd, month_key)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(month_html)
    print(f"  🌐 MTD HTML updated: {html_path}")

    # ── Tracking index ────────────────────────────────────────────────────────
    available_months = sorted(
        [f.stem for f in html_dir.glob("*.html") if f.stem != "index"],
        reverse=True
    )
    index_html = build_tracking_index(available_months)
    with open(html_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  🌐 Tracking index updated")


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
        print("⚠️  No candidates today — skipping sniper & tracking.")
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

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()