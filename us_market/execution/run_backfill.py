"""
run_backfill.py
───────────────
One-time script: inject batch 1-3 historical data into execution CSVs.
Run once, then use run_execution.py for daily appends.

Usage:
    python run_backfill.py
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta

# ── Output paths ──────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent
DATA_DIR      = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EQUITY_PATH   = DATA_DIR / "equity_curve.csv"
REBAL_PATH    = DATA_DIR / "rebalance_log.csv"
CYCLE_PATH    = DATA_DIR / "cycle_return.csv"

# ── Hardcoded batch data (from manual summary) ────────────────────────────────
BATCHES = [
    {
        "rebalance_id": 1,
        "date_start":   "2026-01-02",
        "date_end":     "2026-01-29",   # 20 trading days from Jan 2
        "holdings": [
            {"ticker": "MU",   "sniper_score": 74.26, "entry_price": 315.42},
            {"ticker": "ASML", "sniper_score": 69.91, "entry_price": 1162.25},
            {"ticker": "GE",   "sniper_score": 69.33, "entry_price": 320.28},
            {"ticker": "QYLD", "sniper_score": 61.02, "entry_price": 17.33},
            {"ticker": "BCS",  "sniper_score": 58.65, "entry_price": 25.74},
        ],
    },
    {
        "rebalance_id": 2,
        "date_start":   "2026-01-30",
        "date_end":     "2026-02-26",   # 20 trading days from Jan 30
        "holdings": [
            {"ticker": "MU",   "sniper_score": 77.20, "entry_price": 414.88},
            {"ticker": "WDC",  "sniper_score": 73.70, "entry_price": 250.11},
            {"ticker": "HSBC", "sniper_score": 71.26, "entry_price": 85.60},
            {"ticker": "CHRW", "sniper_score": 69.45, "entry_price": 194.29},
            {"ticker": "LMT",  "sniper_score": 67.09, "entry_price": 630.90},
        ],
    },
    {
        "rebalance_id": 3,
        "date_start":   "2026-02-27",
        "date_end":     "2026-03-26",   # 20 trading days from Feb 27
        "holdings": [
            {"ticker": "GLW",  "sniper_score": 78.92, "entry_price": 150.38},
            {"ticker": "FIGS", "sniper_score": 75.67, "entry_price": 15.45},
            {"ticker": "AMAT", "sniper_score": 75.60, "entry_price": 372.30},
            {"ticker": "EWY",  "sniper_score": 74.05, "entry_price": 151.37},
            {"ticker": "AXTI", "sniper_score": 69.38, "entry_price": 37.90},
        ],
    },
]

# Batch 4 is ongoing — handled by run_execution.py
BATCH_4 = {
    "rebalance_id": 4,
    "date_start":   "2026-03-27",
    "date_end":     None,               # ongoing
    "holdings": [
        {"ticker": "E",   "sniper_score": 79.30, "entry_price": 55.22},
        {"ticker": "CVE", "sniper_score": 78.00, "entry_price": 26.82},
        {"ticker": "MPC", "sniper_score": 74.96, "entry_price": 251.91},
        {"ticker": "SLB", "sniper_score": 73.95, "entry_price": 53.50},
        {"ticker": "OXY", "sniper_score": 73.61, "entry_price": 65.32},
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _weights(holdings):
    """Compute score-weighted allocation per ticker."""
    total = sum(h["sniper_score"] for h in holdings)
    return {h["ticker"]: h["sniper_score"] / total for h in holdings}


def _fetch_prices(tickers, start, end):
    """
    Fetch daily Close prices via yfinance.
    Returns DataFrame indexed by date with ticker columns.
    end is inclusive so we add 1 calendar day for yf.
    """
    end_dt = pd.Timestamp(end) + pd.Timedelta(days=5)  # buffer for weekends
    raw = yf.download(
        tickers,
        start=start,
        end=end_dt.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})

    prices.index = pd.to_datetime(prices.index).normalize()
    # Drop timezone info
    prices.index = prices.index.tz_localize(None) if prices.index.tz else prices.index
    prices = prices.ffill()
    return prices


def _trading_days_from(start_str, n=20, prices_index=None):
    """
    Return list of n trading day dates starting from start_str (inclusive).
    Uses actual price index if provided, else approximate.
    """
    if prices_index is not None:
        start = pd.Timestamp(start_str)
        idx = prices_index[prices_index >= start]
        return idx[:n].tolist()
    # Fallback: business days
    start = pd.Timestamp(start_str)
    days = pd.bdate_range(start=start, periods=n)
    return days.tolist()


def _simulate_batch(batch, initial_equity, spy_prices, spy_anchor_equity=100.0):
    """
    Simulate one 20-day batch.

    spy_anchor_equity : the SPY equity value at the END of the previous batch
                        (so SPY curve is continuous, never resets to 100).

    Returns:
        equity_rows      : list of dicts for equity_curve.csv
        rebal_rows       : list of dicts for rebalance_log.csv
        cycle_return     : float
        final_equity     : float
        spy_final_equity : float  ← pass to next batch as spy_anchor_equity
    """
    rid       = batch["rebalance_id"]
    holdings  = batch["holdings"]
    start     = batch["date_start"]
    end       = batch["date_end"]
    tickers   = [h["ticker"] for h in holdings]
    weights   = _weights(holdings)

    print(f"\n  Batch {rid}: fetching {tickers} from {start} ...")

    # Determine fetch end date
    fetch_end = end if end else datetime.today().strftime("%Y-%m-%d")

    prices = _fetch_prices(tickers, start, fetch_end)

    # Get actual trading days in this batch
    if end:
        trading_days = prices.loc[start:end].index.tolist()
        # Cap at 20 days
        trading_days = trading_days[:20]
    else:
        trading_days = prices.loc[start:].index.tolist()

    if not trading_days:
        print(f"  ⚠️  No price data for batch {rid}, skipping.")
        return [], [], None, initial_equity, spy_anchor_equity

    # Allocate shares on entry day
    entry_day = trading_days[0]
    shares = {}
    for h in holdings:
        t = h["ticker"]
        alloc = initial_equity * weights[t]
        ep = h["entry_price"]  # use exact manual entry price
        shares[t] = alloc / ep

    # Daily loop
    equity_rows = []
    prev_equity  = initial_equity
    spy_prev_price = None  # SPY raw price on previous day (for daily SPY return)

    # SPY raw price at batch entry — used to chain equity, NOT to rebase to 100
    if spy_prices is not None and entry_day in spy_prices.index:
        spy_prev_price = float(spy_prices.loc[entry_day])

    spy_running = spy_anchor_equity  # starts where last batch ended

    for i, day in enumerate(trading_days):
        # Portfolio value
        day_vals = {}
        for t in tickers:
            if t in prices.columns and day in prices.index:
                price = prices.loc[day, t]
                if pd.isna(price):
                    price = prices[t].ffill().loc[day] if day in prices.index else np.nan
                day_vals[t] = shares[t] * price
            else:
                day_vals[t] = shares[t] * holdings[[h["ticker"] for h in holdings].index(t)]

        equity_t  = sum(v for v in day_vals.values() if not np.isnan(v))
        daily_ret = (equity_t / prev_equity) - 1 if prev_equity > 0 else 0

        # SPY: chain daily return onto running equity (never reset)
        spy_eq = None
        if spy_prices is not None and day in spy_prices.index:
            spy_raw = float(spy_prices.loc[day])
            if i == 0:
                # First day of batch: SPY equity = anchor (no change yet)
                spy_running    = spy_anchor_equity
                spy_prev_price = spy_raw
            else:
                if spy_prev_price and spy_prev_price > 0:
                    spy_daily_ret = (spy_raw / spy_prev_price) - 1
                    spy_running   = spy_running * (1 + spy_daily_ret)
                spy_prev_price = spy_raw
            spy_eq = round(spy_running, 6)

        equity_rows.append({
            "date":         day.strftime("%Y-%m-%d"),
            "equity":       round(equity_t, 6),
            "daily_return": round(daily_ret, 6),
            "rebalance_id": rid,
            "spy_equity":   spy_eq,
        })

        prev_equity = equity_t

    final_equity     = equity_rows[-1]["equity"] if equity_rows else initial_equity
    spy_final_equity = equity_rows[-1]["spy_equity"] if equity_rows and equity_rows[-1]["spy_equity"] else spy_anchor_equity
    cycle_return     = (final_equity / initial_equity) - 1

    # Rebalance log rows
    rebal_rows = []
    exit_day   = trading_days[-1]
    for h in holdings:
        t   = h["ticker"]
        ep  = h["entry_price"]
        xp  = None
        if t in prices.columns and exit_day in prices.index:
            xp = float(prices.loc[exit_day, t])
        ticker_ret = (xp / ep - 1) if xp else None

        rebal_rows.append({
            "rebalance_id":      rid,
            "date_start":        start,
            "date_end":          exit_day.strftime("%Y-%m-%d"),
            "ticker":            t,
            "sniper_score":      h["sniper_score"],
            "weight":            round(weights[t], 6),
            "entry_price":       ep,
            "exit_price":        round(xp, 4) if xp else None,
            "return_per_ticker": round(ticker_ret * 100, 4) if ticker_ret is not None else None,
        })

    return equity_rows, rebal_rows, round(cycle_return * 100, 4), final_equity, spy_final_equity


# ── Main ──────────────────────────────────────────────────────────────────────

def run_backfill():
    print("🔁 Starting backfill...")

    # ── Weekend guard ──────────────────────────────────────────────────────────
    from datetime import datetime
    today_dt = datetime.today()
    if today_dt.weekday() >= 5:
        print("⚠️  Weekend detected — backfill will still run (historical data only).")

    # Collect all tickers across all batches (incl batch 4)
    all_batches = BATCHES + [BATCH_4]
    all_tickers = list({h["ticker"] for b in all_batches for h in b["holdings"]})
    all_tickers.append("SPY")

    # Fetch SPY separately for benchmark
    print("\n📡 Fetching SPY benchmark...")
    spy_raw = _fetch_prices(["SPY"], "2026-01-02", datetime.today().strftime("%Y-%m-%d"))
    if "SPY" in spy_raw.columns:
        spy_prices = spy_raw["SPY"].dropna()
    else:
        spy_prices = spy_raw.iloc[:, 0].dropna()

    # Simulate completed batches 1-3
    all_equity   = []
    all_rebal    = []
    all_cycles   = []
    equity       = 100.0
    spy_anchor   = 100.0   # SPY starts at 100 on day 1, chains from there

    for batch in BATCHES:
        eq_rows, rb_rows, cyc_ret, equity, spy_anchor = _simulate_batch(
            batch, equity, spy_prices, spy_anchor_equity=spy_anchor
        )
        all_equity.extend(eq_rows)
        all_rebal.extend(rb_rows)
        if cyc_ret is not None:
            all_cycles.append({
                "rebalance_id":  batch["rebalance_id"],
                "date_start":    batch["date_start"],
                "date_end":      batch["date_end"],
                "cycle_return":  cyc_ret,
                "equity_end":    round(equity, 6),
            })
        print(f"  ✅ Batch {batch['rebalance_id']} done | cycle return: {cyc_ret:.2f}% | equity: {equity:.4f} | spy: {spy_anchor:.4f}")

    # Simulate batch 4 (ongoing)
    print("\n  Simulating batch 4 (ongoing)...")
    eq_rows, rb_rows, cyc_ret, equity, spy_anchor = _simulate_batch(
        BATCH_4, equity, spy_prices, spy_anchor_equity=spy_anchor
    )
    all_equity.extend(eq_rows)
    all_rebal.extend(rb_rows)
    # Don't log cycle_return for ongoing batch — will be done at close

    # ── Write CSVs ────────────────────────────────────────────────────────────
    equity_df = pd.DataFrame(all_equity)
    equity_df.to_csv(EQUITY_PATH, index=False)
    print(f"\n💾 equity_curve.csv → {len(equity_df)} rows")

    rebal_df = pd.DataFrame(all_rebal)
    rebal_df.to_csv(REBAL_PATH, index=False)
    print(f"💾 rebalance_log.csv → {len(rebal_df)} rows")

    cycle_df = pd.DataFrame(all_cycles)
    cycle_df.to_csv(CYCLE_PATH, index=False)
    print(f"💾 cycle_return.csv → {len(cycle_df)} rows")

    print("\n✅ Backfill complete!")
    print(f"   Final equity: {equity:.4f}")
    print(f"   Total return: {(equity / 100 - 1) * 100:.2f}%")


if __name__ == "__main__":
    run_backfill()