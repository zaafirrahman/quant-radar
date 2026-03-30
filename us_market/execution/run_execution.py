"""
run_execution.py
────────────────
Daily append engine for the Alpha Execution Bot.
Called from run_daily.py after sniper pipeline completes.

Logic:
  1. Determine current active batch from rebalance_log.csv
  2. Fetch today's prices for active holdings
  3. Append one row to equity_curve.csv
  4. If today = day 20 of batch → close batch, log cycle_return, open new batch

Usage (standalone):
    python run_execution.py

Usage (from run_daily.py):
    from us_market.execution.run_execution import run_execution
    run_execution(summary_df, today)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime

# ── Paths — adjust to match your project root ─────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR / "data"

EQUITY_PATH = DATA_DIR / "equity_curve.csv"
REBAL_PATH  = DATA_DIR / "rebalance_log.csv"
CYCLE_PATH  = DATA_DIR / "cycle_return.csv"

HOLD_DAYS   = 20   # trading days per batch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_price(ticker, date_str=None):
    """Fetch latest (or specific date) close price for one ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", auto_adjust=False)
        if hist.empty:
            return None
        if date_str:
            hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
            target = pd.Timestamp(date_str)
            match = hist[hist.index.normalize() == target]
            if not match.empty:
                return float(match["Close"].iloc[-1])
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"  ⚠️  Price fetch failed for {ticker}: {e}")
        return None


def _load_csv(path, dtypes=None):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=dtypes)
    return df


def _active_batch(rebal_df):
    """Return rows for the currently open batch (no exit_price or latest rebalance_id)."""
    if rebal_df.empty:
        return None, None
    latest_id = rebal_df["rebalance_id"].max()
    rows = rebal_df[rebal_df["rebalance_id"] == latest_id].copy()
    return latest_id, rows


def _days_elapsed(rebal_rows, equity_df):
    """Count how many equity_curve rows exist for this rebalance_id."""
    if equity_df.empty:
        return 0
    rid = rebal_rows["rebalance_id"].iloc[0]
    return len(equity_df[equity_df["rebalance_id"] == rid])


def _top5_from_summary(summary_df):
    """Extract top 5 by Sniper_Score from today's sniper_summary DataFrame."""
    if summary_df is None or summary_df.empty:
        return None
    df = summary_df.sort_values("Sniper_Score", ascending=False).head(5)
    return df[["Ticker", "Sniper_Score"]].copy()


def _open_new_batch(summary_df, current_equity, rebal_df, today_str):
    """
    Open a new batch using today's sniper_summary top 5.
    Writes new rows to rebalance_log with entry prices.
    Returns new rebal rows or None if failed.
    """
    top5 = _top5_from_summary(summary_df)
    if top5 is None:
        print("  ❌ Cannot open new batch: no sniper summary available.")
        return None

    new_rid = int(rebal_df["rebalance_id"].max() + 1) if not rebal_df.empty else 1
    total_score = top5["Sniper_Score"].sum()
    new_rows = []

    print(f"\n  📋 Opening Batch {new_rid} on {today_str}")
    for _, row in top5.iterrows():
        ticker = row["Ticker"]
        score  = row["Sniper_Score"]
        weight = score / total_score
        ep     = _safe_price(ticker)
        if ep is None:
            print(f"  ⚠️  Could not fetch entry price for {ticker}, skipping batch open.")
            return None

        new_rows.append({
            "rebalance_id":      new_rid,
            "date_start":        today_str,
            "date_end":          None,
            "ticker":            ticker,
            "sniper_score":      round(score, 4),
            "weight":            round(weight, 6),
            "entry_price":       round(ep, 4),
            "exit_price":        None,
            "return_per_ticker": None,
        })
        print(f"  ✅ {ticker}: weight={weight:.2%}, entry={ep:.4f}")

    new_rebal_df = pd.DataFrame(new_rows)

    # Append to rebalance_log
    existing = _load_csv(REBAL_PATH)
    combined = pd.concat([existing, new_rebal_df], ignore_index=True)
    combined.to_csv(REBAL_PATH, index=False)

    return new_rebal_df


def _close_batch(rebal_rows, equity_df, today_str):
    """
    Close the current batch:
     - Fill exit_price and return_per_ticker in rebalance_log
     - Append row to cycle_return.csv
    """
    rid = rebal_rows["rebalance_id"].iloc[0]
    date_start = rebal_rows["date_start"].iloc[0]
    tickers = rebal_rows["ticker"].tolist()

    print(f"\n  🔒 Closing Batch {rid} on {today_str}")

    # Get final equity for cycle return
    eq_rows = equity_df[equity_df["rebalance_id"] == rid]
    if not eq_rows.empty:
        equity_start = eq_rows["equity"].iloc[0] / (1 + eq_rows["daily_return"].iloc[0])
        equity_end   = eq_rows["equity"].iloc[-1]
        cycle_ret    = round((equity_end / equity_start - 1) * 100, 4)
    else:
        equity_end = None
        cycle_ret  = None

    # Fetch exit prices
    updated_rows = []
    for _, row in rebal_rows.iterrows():
        t  = row["ticker"]
        ep = row["entry_price"]
        xp = _safe_price(t)
        tr = round((xp / ep - 1) * 100, 4) if xp and ep else None
        r  = row.to_dict()
        r["date_end"]          = today_str
        r["exit_price"]        = round(xp, 4) if xp else None
        r["return_per_ticker"] = tr
        updated_rows.append(r)
        print(f"  {t}: exit={xp:.4f}, return={tr:.2f}%" if xp else f"  {t}: exit price unavailable")

    # Rewrite rebalance_log with updated rows for this batch
    existing = _load_csv(REBAL_PATH)
    existing = existing[existing["rebalance_id"] != rid]
    updated_df = pd.DataFrame(updated_rows)
    combined = pd.concat([existing, updated_df], ignore_index=True)
    combined.to_csv(REBAL_PATH, index=False)

    # Append to cycle_return
    cycle_entry = {
        "rebalance_id": rid,
        "date_start":   date_start,
        "date_end":     today_str,
        "cycle_return": cycle_ret,
        "equity_end":   round(equity_end, 6) if equity_end else None,
    }
    existing_cycles = _load_csv(CYCLE_PATH)
    new_cycles = pd.concat([existing_cycles, pd.DataFrame([cycle_entry])], ignore_index=True)
    new_cycles.to_csv(CYCLE_PATH, index=False)
    print(f"  ✅ Batch {rid} closed | cycle return: {cycle_ret:.2f}%")

    return cycle_ret


# ── Main execution function ───────────────────────────────────────────────────

def run_execution(summary_df=None, today_str=None):
    """
    Main daily execution logic.
    
    Args:
        summary_df : today's sniper_summary DataFrame (from run_daily.py)
        today_str  : date string 'YYYY-MM-DD' (defaults to today)
    """
    if today_str is None:
        today_str = datetime.today().strftime("%Y-%m-%d")

    print(f"\n⚡ Execution Engine | {today_str}")

    # Load existing data
    equity_df = _load_csv(EQUITY_PATH)
    rebal_df  = _load_csv(REBAL_PATH)

    if rebal_df.empty:
        print("  ❌ No rebalance_log found. Run run_backfill.py first.")
        return

    # Get active batch
    rid, rebal_rows = _active_batch(rebal_df)
    if rebal_rows is None:
        print("  ❌ Could not determine active batch.")
        return

    days_done = _days_elapsed(rebal_rows, equity_df)
    tickers   = rebal_rows["ticker"].tolist()
    weights   = rebal_rows.set_index("ticker")["weight"].to_dict()
    entries   = rebal_rows.set_index("ticker")["entry_price"].to_dict()

    # Previous equity (last row in equity_curve)
    if not equity_df.empty:
        prev_equity = float(equity_df["equity"].iloc[-1])
    else:
        prev_equity = 100.0

    # Fetch today's prices
    print(f"  📡 Fetching prices for batch {rid}: {tickers}")
    day_vals = {}
    for t in tickers:
        price = _safe_price(t)
        if price is None:
            print(f"  ❌ Missing price for {t}. Skipping today's append.")
            return
        alloc  = prev_equity  # equity at entry (will be scaled by weight below)
        # Reconstruct shares: allocation = equity_at_entry_day * weight / entry_price
        # We need the equity at the START of this batch
        batch_equity_rows = equity_df[equity_df["rebalance_id"] == rid]
        if not batch_equity_rows.empty:
            first_row   = batch_equity_rows.iloc[0]
            equity_open = first_row["equity"] / (1 + first_row["daily_return"])
        else:
            # First day of batch
            equity_open = prev_equity

        shares  = (equity_open * weights[t]) / entries[t]
        day_vals[t] = shares * price

    equity_today = sum(day_vals.values())
    daily_ret    = (equity_today / prev_equity) - 1 if prev_equity > 0 else 0

    # Fetch SPY for benchmark
    spy_price    = _safe_price("SPY")
    spy_eq       = None
    # Find SPY equity at batch open to compute relative benchmark
    batch_eq     = equity_df[equity_df["rebalance_id"] == rid]
    if not batch_eq.empty and spy_price:
        # Simple: find first SPY equity in this batch
        first_spy = batch_eq["spy_equity"].iloc[0]
        if first_spy and first_spy > 0:
            # SPY equity is stored as rebased to 100 at portfolio start
            # Keep it on same base by using ratio
            pass  # spy_eq will be appended as raw SPY price ratio
        spy_eq = None  # Will be calculated in dashboard from raw equity

    # Append to equity_curve
    new_row = {
        "date":         today_str,
        "equity":       round(equity_today, 6),
        "daily_return": round(daily_ret, 6),
        "rebalance_id": rid,
        "spy_equity":   spy_eq,
    }
    equity_df = pd.concat([equity_df, pd.DataFrame([new_row])], ignore_index=True)
    equity_df.to_csv(EQUITY_PATH, index=False)
    print(f"  ✅ Appended | equity={equity_today:.4f} | daily_return={daily_ret:.4%}")

    days_done += 1
    print(f"  📅 Day {days_done}/{HOLD_DAYS} of batch {rid}")

    # Check if batch is complete
    if days_done >= HOLD_DAYS:
        _close_batch(rebal_rows, equity_df, today_str)
        if summary_df is not None:
            _open_new_batch(summary_df, equity_today, rebal_df, today_str)
        else:
            print("  ⚠️  No summary_df provided — new batch will open on next run with data.")

    print("  ✅ Execution engine done.")


# ── Standalone run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Load today's sniper summary if available
    summary_path = Path(__file__).resolve().parents[2] / "output" / "sniper" / "sniper_summary.csv"
    if summary_path.exists():
        summary_df = pd.read_csv(summary_path)
    else:
        summary_df = None

    run_execution(summary_df)