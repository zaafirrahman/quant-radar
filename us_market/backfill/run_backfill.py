"""
run_backfill.py — One-time historical backfill for tracking data.

Usage:
    # Full backfill (2026-01-02 to 2026-03-23)
    python -m us_market.backfill.run_backfill

    # Rerun a specific date (manual rescue)
    python -m us_market.backfill.run_backfill --date 2026-02-14
"""

import argparse
import math
import warnings
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import date, timedelta

warnings.filterwarnings("ignore")

from us_market.config.ticker_universe import US_TICKERS
from us_market.engine.screen_score import calculate_score
from us_market.analysis.single_sniper import (
    _calc_edge, _calc_sample_score,
    _calc_cluster_score, _calc_stability_score, _calc_sniper_score,
)

# ─────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parents[1]
TRACKING_DIR = BASE_DIR / "output" / "tracking"
PARQUET_PATH = TRACKING_DIR / "master.parquet"
LOG_PATH     = BASE_DIR / "backfill" / "backfill_log.csv"

TRACKING_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
(TRACKING_DIR / "json").mkdir(parents=True, exist_ok=True)
(TRACKING_DIR / "html").mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────
#  TRADING DAYS
# ─────────────────────────────────────────

def _trading_days(start: date, end: date) -> list[date]:
    """Return Mon–Fri dates between start and end inclusive."""
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


# ─────────────────────────────────────────
#  SNIPER SCORE (lightweight)
# ─────────────────────────────────────────

def _quick_sniper(ticker: str, raw_full: pd.DataFrame, as_of: date) -> float | None:
    raw = raw_full[raw_full.index.date <= as_of].copy()
    if len(raw) < 345:
        return None
    try:
        scored    = calculate_score(raw)
        if len(scored) < 20:
            return None

        threshold   = float(scored["SCORE"].quantile(0.95))
        signal_rows = scored[scored["SCORE"] > threshold]

        results = []
        for dt, row in signal_rows.iterrows():
            idx = raw.index.get_loc(dt)
            if idx + 20 >= len(raw):
                continue
            entry = float(raw["Close"].iloc[idx])
            p5    = float(raw["Close"].iloc[idx + 5])
            p10   = float(raw["Close"].iloc[idx + 10])
            p20   = float(raw["Close"].iloc[idx + 20])
            results.append({
                "Date":           dt.strftime("%Y-%m-%d"),
                "Return_5d (%)":  round((p5  / entry - 1) * 100, 2),
                "Return_10d (%)": round((p10 / entry - 1) * 100, 2),
                "Return_20d (%)": round((p20 / entry - 1) * 100, 2),
            })

        if not results:
            return None

        sdf  = pd.DataFrame(results)
        ar5  = sdf["Return_5d (%)"].mean()
        ar10 = sdf["Return_10d (%)"].mean()
        ar20 = sdf["Return_20d (%)"].mean()
        wr5  = (sdf["Return_5d (%)"]  > 0).mean() * 100
        wr10 = (sdf["Return_10d (%)"] > 0).mean() * 100
        wr20 = (sdf["Return_20d (%)"] > 0).mean() * 100
        n    = len(sdf)

        e5  = _calc_edge(ar5,  wr5)
        e10 = _calc_edge(ar10, wr10)
        e20 = _calc_edge(ar20, wr20)
        edge_raw        = (e5 + e10 + e20) / 3
        sample_score    = _calc_sample_score(n)
        cluster_score   = _calc_cluster_score(sdf["Date"].tolist())
        stability_score = _calc_stability_score(sdf["Return_20d (%)"], sdf)
        quality_score   = (sample_score + cluster_score + stability_score) / 3

        return _calc_sniper_score(edge_raw, quality_score)

    except Exception:
        return None


# ─────────────────────────────────────────
#  PROCESS ONE DAY
# ─────────────────────────────────────────

def _process_day(target: date, raw_cache: dict,
                 existing_parquet: pd.DataFrame) -> tuple[list[dict], str, int, str]:
    rows = []

    # ── Screener — find candidates (distance > 0) ─────────────────────────────
    candidates = []
    for ticker in US_TICKERS:
        raw = raw_cache.get(ticker)
        if raw is None or raw.empty:
            continue
        try:
            df = raw[raw.index.date <= target].copy()
            if len(df) < 345:
                continue

            scored        = calculate_score(df)
            current_score = float(scored["SCORE"].iloc[-1])
            threshold     = float(scored["SCORE"].quantile(0.95))
            distance_pct  = (current_score - threshold) / threshold * 100

            price = float(df["Close"].iloc[-1])
            prev_df = raw[raw.index.date < target]
            price_change = None
            if len(prev_df) > 0:
                prev_price   = float(prev_df["Close"].iloc[-1])
                price_change = round((price / prev_price - 1) * 100, 2)

            if distance_pct > 0:
                candidates.append({
                    "ticker":       ticker,
                    "radar_score":  round(current_score, 4),
                    "distance_pct": round(distance_pct, 2),
                    "price":        round(price, 2),
                    "price_change": price_change,
                    "raw":          raw,
                    "is_candidate": True,
                })
            else:
                # Still track if seen in last 20 trading days
                if not existing_parquet.empty:
                    target_str = target.strftime("%Y-%m-%d")
                    cutoff_date = (target - timedelta(days=28)).strftime("%Y-%m-%d")
                    recent = existing_parquet[
                        (existing_parquet["Ticker"] == ticker) &
                        (existing_parquet["Date"] >= cutoff_date)
                    ]
                    if not recent.empty:
                        candidates.append({
                            "ticker":       ticker,
                            "radar_score":  round(current_score, 4),
                            "distance_pct": round(distance_pct, 2),
                            "price":        round(price, 2),
                            "price_change": price_change,
                            "raw":          raw,
                            "is_candidate": False,
                        })

        except Exception:
            continue

    if not candidates:
        return [], "SUCCESS", 0, ""

    # ── Sniper for candidates only ────────────────────────────────────────────
    tickers_done = []
    n_candidates = 0
    for c in candidates:
        sniper = _quick_sniper(c["ticker"], c["raw"], target) if c["is_candidate"] else None
        rows.append({
            "Date":         target.strftime("%Y-%m-%d"),
            "Ticker":       c["ticker"],
            "Radar_Score":  c["radar_score"],
            "Distance_%":   c["distance_pct"],
            "Price":        c["price"],
            "Price_Change": c["price_change"],
            "Sniper_Score": round(sniper, 2) if sniper is not None else None,
        })
        if c["is_candidate"]:
            tickers_done.append(c["ticker"])
            n_candidates += 1

    return rows, "SUCCESS", n_candidates, ",".join(tickers_done)


# ─────────────────────────────────────────
#  LOG HELPER
# ─────────────────────────────────────────

def _log(date_str: str, status: str, n: int, tickers: str, notes: str = ""):
    row = pd.DataFrame([{
        "Date":         date_str,
        "Status":       status,
        "N_Candidates": n,
        "Tickers":      tickers,
        "Notes":        notes,
    }])
    if LOG_PATH.exists():
        log = pd.read_csv(LOG_PATH)
        log = log[log["Date"] != date_str]
        log = pd.concat([log, row], ignore_index=True)
    else:
        log = row
    log.to_csv(LOG_PATH, index=False)


# ─────────────────────────────────────────
#  PARQUET HELPER
# ─────────────────────────────────────────

def _append_parquet(new_rows: list[dict], target_date: str):
    new_df = pd.DataFrame(new_rows)
    if PARQUET_PATH.exists():
        existing = pd.read_parquet(PARQUET_PATH)
        existing = existing[existing["Date"] != target_date]
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_parquet(PARQUET_PATH, index=False)


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=None,
                        help="Rerun specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date:
        days = [date.fromisoformat(args.date)]
        print(f"🔁 Rerunning single date: {args.date}")
    else:
        start = date(2026, 1, 2)
        end   = date(2026, 3, 23)
        days  = _trading_days(start, end)
        print(f"📅 Backfill: {days[0]} → {days[-1]} ({len(days)} trading days)")

    # ── Download raw data once ────────────────────────────────────────────────
    print(f"\n📥 Downloading 3y OHLCV for {len(US_TICKERS)} tickers...")
    raw_data = yf.download(
        US_TICKERS,
        period="3y",
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=True,
    )

    # Build per-ticker cache
    raw_cache = {}
    for ticker in US_TICKERS:
        try:
            if isinstance(raw_data.columns, pd.MultiIndex):
                df = raw_data.xs(ticker, axis=1, level=0).dropna()
            else:
                df = raw_data[ticker].dropna()
            raw_cache[ticker] = df if not df.empty else pd.DataFrame()
        except Exception:
            raw_cache[ticker] = pd.DataFrame()

    print(f"✅ Cache ready — {sum(1 for v in raw_cache.values() if not v.empty)} tickers loaded\n")

    # ── Process each day ──────────────────────────────────────────────────────
    total_rows = 0
    for i, target in enumerate(days, 1):
        date_str = target.strftime("%Y-%m-%d")
        print(f"[{i:03d}/{len(days)}] {date_str} ... ", end="", flush=True)

        # Load existing parquet for 20d window lookup
        existing_parquet = pd.read_parquet(PARQUET_PATH) if PARQUET_PATH.exists() else pd.DataFrame()

        try:
            rows, status, n, tickers_str = _process_day(target, raw_cache, existing_parquet)

            if rows:
                _append_parquet(rows, date_str)
                total_rows += len(rows)

            _log(date_str, status, n, tickers_str)
            print(f"{n} candidates → {tickers_str if tickers_str else 'none'}")

        except Exception as ex:
            _log(date_str, "FAILED", 0, "", str(ex))
            print(f"❌ FAILED: {ex}")

    print(f"\n✅ Backfill complete — {total_rows} rows written to parquet")
    print(f"📋 Log saved: {LOG_PATH}")
    print(f"🗄️  Parquet: {PARQUET_PATH}")


if __name__ == "__main__":
    main()