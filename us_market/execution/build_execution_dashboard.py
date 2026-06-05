"""
build_execution_dashboard.py
─────────────────────────────
Reads equity_curve.csv, rebalance_log.csv, cycle_return.csv
and generates index.html for the execution dashboard.

Called from run_daily.py after run_execution().
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR / "data"
OUT_DIR     = BASE_DIR.parent / "output" / "execution"

EQUITY_PATH = DATA_DIR / "equity_curve.csv"
REBAL_PATH  = DATA_DIR / "rebalance_log.csv"
CYCLE_PATH  = DATA_DIR / "cycle_return.csv"


# ── Stats helpers ─────────────────────────────────────────────────────────────

def _safe(val, decimals=2, suffix=""):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{round(val, decimals)}{suffix}"

def _color(val, positive="#00ff88", negative="#ff4d4d", neutral="#cccccc"):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return neutral
    return positive if val >= 0 else negative

def _drawdown(equity_series):
    roll_max = equity_series.cummax()
    dd = (equity_series / roll_max - 1)
    return dd.min() * 100

def _fetch_current_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch latest close price for each ticker via yfinance.
    Returns dict {ticker: price}. Falls back to empty dict on any error.
    Uses period='5d' so it always gets the most recent trading day close
    even if today is weekend/holiday.
    """
    if not _YF_AVAILABLE or not tickers:
        return {}
    try:
        raw = yf.download(tickers, period="5d", auto_adjust=True, progress=False)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        # Take last valid row
        last_row = close.ffill().iloc[-1]
        prices = {}
        for t in tickers:
            val = last_row.get(t) if hasattr(last_row, "get") else last_row.get(t, None)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                prices[t] = float(val)
        return prices
    except Exception as e:
        print(f"⚠️  yfinance fetch failed: {e}")
        return {}


def _build_spy_series(equity_df):
    """Rebuild SPY rebased to 100 from equity_curve if spy_equity is available."""
    if "spy_equity" in equity_df.columns:
        spy = equity_df["spy_equity"].dropna()
        if not spy.empty:
            return spy
    return None


# ── HTML generation ───────────────────────────────────────────────────────────

def build_execution_dashboard(timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Load data ──────────────────────────────────────────────────────────────
    equity_df = pd.read_csv(EQUITY_PATH, parse_dates=["date"]) if EQUITY_PATH.exists() else pd.DataFrame()
    rebal_df  = pd.read_csv(REBAL_PATH) if REBAL_PATH.exists() else pd.DataFrame()
    cycle_df  = pd.read_csv(CYCLE_PATH) if CYCLE_PATH.exists() else pd.DataFrame()

    if equity_df.empty:
        return "<html><body><p>No data yet. Run run_backfill.py first.</p></body></html>"

    # ── Core metrics ───────────────────────────────────────────────────────────
    equity_series    = equity_df["equity"]
    daily_rets       = equity_df["daily_return"]
    current_equity   = float(equity_series.iloc[-1])
    total_return     = (current_equity / 100 - 1) * 100
    max_dd           = _drawdown(equity_series)
    avg_daily_ret    = float(daily_rets.mean()) * 100
    volatility       = float(daily_rets.std()) * 100
    win_rate         = float((daily_rets > 0).mean()) * 100
    best_day         = float(daily_rets.max()) * 100
    worst_day        = float(daily_rets.min()) * 100

    # ── Cycle stats ────────────────────────────────────────────────────────────
    best_cycle  = float(cycle_df["cycle_return"].max()) if not cycle_df.empty else None
    worst_cycle = float(cycle_df["cycle_return"].min()) if not cycle_df.empty else None
    last_3      = cycle_df.to_dict("records") if not cycle_df.empty else []

    # ── Active batch ───────────────────────────────────────────────────────────
    active_rebal = pd.DataFrame()
    active_rid   = None
    if not rebal_df.empty:
        active_rid   = int(rebal_df["rebalance_id"].max())
        active_rebal = rebal_df[rebal_df["rebalance_id"] == active_rid].copy()

    # Days elapsed in active batch
    days_elapsed = 0
    if not equity_df.empty and active_rid:
        days_elapsed = len(equity_df[equity_df["rebalance_id"] == active_rid])

    # ── Chart data ─────────────────────────────────────────────────────────────
    chart_dates  = [d.strftime("%Y-%m-%d") for d in equity_df["date"]]
    chart_equity = [round(float(v), 4) for v in equity_series]

    # Rebalance markers for chart
    rebal_markers = []
    if not rebal_df.empty:
        for rid in rebal_df["rebalance_id"].unique():
            rows = rebal_df[rebal_df["rebalance_id"] == rid]
            ds = rows["date_start"].iloc[0]
            rebal_markers.append(ds)

    # SPY series
    spy_series = _build_spy_series(equity_df)
    chart_spy  = []
    if spy_series is not None:
        chart_spy = [round(float(v), 4) if not np.isnan(v) else None for v in equity_df["spy_equity"]]

    # ── Current holdings unrealized P&L ────────────────────────────────────────
    holdings_html = ""
    if not active_rebal.empty:
        # Fetch current prices for all LIVE tickers
        live_tickers = []
        for _, row in active_rebal.iterrows():
            xp = row.get("exit_price")
            if not xp or (isinstance(xp, float) and np.isnan(xp)):
                live_tickers.append(row["ticker"])

        current_prices = _fetch_current_prices(live_tickers)
        if current_prices:
            print(f"📡 Fetched live prices: {current_prices}")

        rows_html = ""
        for _, row in active_rebal.iterrows():
            ep  = row.get("entry_price")
            xp  = row.get("exit_price")
            ret = row.get("return_per_ticker")
            cp  = None  # current price placeholder

            if xp and not (isinstance(xp, float) and np.isnan(xp)):
                # Already closed — use recorded return
                ret_str   = f"{'+' if ret >= 0 else ''}{_safe(ret, 2)}%"
                ret_color = _color(ret)
                cur_str   = _safe(xp, 2)   # show exit price as "current"
                status    = "CLOSED"
            else:
                # Live — compute unrealized return from fetched price
                cp = current_prices.get(row["ticker"])
                if cp and ep and not (isinstance(ep, float) and np.isnan(ep)):
                    unrealized = (cp / ep - 1) * 100
                    ret_str    = f"{'+' if unrealized >= 0 else ''}{round(unrealized, 2)}%"
                    ret_color  = _color(unrealized)
                    cur_str    = _safe(cp, 2)
                else:
                    ret_str   = "–"
                    ret_color = "#888888"
                    cur_str   = "–"
                status = "LIVE"

            rows_html += f"""
            <tr>
                <td style="color:#ffffff;font-weight:bold;">{row['ticker']}</td>
                <td style="color:#888888;">{_safe(row.get('sniper_score'), 2)}</td>
                <td style="color:#ff8c00;">{_safe(float(row.get('weight', 0)) * 100, 1)}%</td>
                <td style="color:#cccccc;">{_safe(ep, 2)}</td>
                <td style="color:#aaaaaa;">{cur_str}</td>
                <td style="color:{ret_color};font-weight:bold;">{ret_str}</td>
                <td style="color:#555555;font-size:11px;">{status}</td>
            </tr>"""

        holdings_html = f"""
        <div class="section-title">📋 BATCH {active_rid} HOLDINGS <span style="color:#555;font-size:11px;margin-left:8px;">DAY {days_elapsed}/20</span></div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>TICKER</th>
                        <th>SNIPER SCORE</th>
                        <th>WEIGHT</th>
                        <th>ENTRY</th>
                        <th>CURRENT</th>
                        <th>RETURN</th>
                        <th>STATUS</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>"""

    # ── Last 3 cycles table ────────────────────────────────────────────────────
    cycles_html = ""
    if last_3:
        rows_html = ""
        def _short_date(d):
            """Convert YYYY-MM-DD to YY-MM-DD."""
            if not d or d == '—':
                return '—'
            parts = str(d).split('-')
            if len(parts) == 3:
                return f"{parts[0][-2:]}-{parts[1]}-{parts[2]}"
            return d
        for c in reversed(last_3):
            ret   = c.get("cycle_return")
            color = _color(ret)
            rid   = c.get("rebalance_id", "?")
            label = f"#{rid}"
            ds    = _short_date(c.get('date_start', '—'))
            de    = _short_date(c.get('date_end', '—'))
            rows_html += f"""
            <tr>
                <td style="color:#555555;font-size:11px;">{label}</td>
                <td style="color:#888888;">{ds} → {de}</td>
                <td style="color:{color};font-weight:bold;">{'+' if ret and ret >= 0 else ''}{_safe(ret, 2)}%</td>
                <td style="color:#cccccc;">{_safe(c.get('equity_end'), 4)}</td>
            </tr>"""

        cycles_html = f"""
        <div class="section-title">🔁 ALL COMPLETED CYCLES</div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr><th>CYCLE</th><th>PERIOD</th><th>RETURN</th><th>EQUITY END</th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>"""

    # ── JSON for JS ───────────────────────────────────────────────────────────
    chart_json = json.dumps({
        "dates":   chart_dates,
        "equity":  chart_equity,
        "spy":     chart_spy,
        "rebalance_dates": rebal_markers,
    })

    # ── Color helpers for template ─────────────────────────────────────────────
    tr_color   = _color(total_return)
    dd_color   = "#ff4d4d"
    adr_color  = _color(avg_daily_ret)
    bd_color   = _color(best_day)
    wd_color   = _color(worst_day)
    bc_color   = _color(best_cycle)
    wc_color   = _color(worst_cycle)

    # VS SPY: both values rebased from 100 on same start date → direct comparison
    spy_latest    = None
    vs_spy_pts    = None
    vs_spy_pct    = None
    vs_spy_color  = "#888888"
    vs_spy_str    = "—"
    vs_spy_sub    = ""
    if chart_spy and any(v is not None for v in chart_spy):
        last_valid = next((v for v in reversed(chart_spy) if v is not None), None)
        if last_valid:
            spy_latest   = last_valid
            vs_spy_pts   = round(current_equity - spy_latest, 2)
            vs_spy_pct   = round((current_equity / spy_latest - 1) * 100, 2)
            vs_spy_color = _color(vs_spy_pts)
            sign         = "+" if vs_spy_pts >= 0 else ""
            vs_spy_str   = f"{sign}{vs_spy_pts:.2f} pts"
            vs_spy_sub   = f"{sign}{vs_spy_pct:.2f}% vs SPY"

    # Win rate bar
    wr_bar_pct = round(win_rate, 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="../../../assets/logo.png">
    <title>Alpha Execution Bot</title>
    <link rel="stylesheet" href="execution.css">
</head>
<body>

<a href="../../us_hub.html" class="nav-btn">◀ Hub</a>

<h2>ALPHA EXECUTOR</h2>
<p class="subtitle" style="color:#ff8c00; margin-bottom: 6px;">Capital Flow Engine</p>
<p class="subtitle">Chained 20-Day Rebalance Simulation · Sniper Top 5 · Score-Weighted</p>

<!-- ── HERO SNAPSHOT ──────────────────────────────────────────── -->
<div class="hero-grid">

    <!-- Row 1: Equity full width -->
    <div class="hero-card hero-main">
        <div class="hero-label">CURRENT EQUITY</div>
        <div class="hero-value">{_safe(current_equity, 4)}</div>
        <div class="hero-sub">started at 100.00</div>
    </div>

    <!-- Row 2: Return + Drawdown -->
    <div class="hero-card hero-return">
        <div class="hero-label">TOTAL RETURN</div>
        <div class="hero-value" style="color:{tr_color};">{'+' if total_return >= 0 else ''}{_safe(total_return, 2)}%</div>
        <div class="hero-sub">since 2026-01-02</div>
    </div>
    <div class="hero-card hero-dd">
        <div class="hero-label">MAX DRAWDOWN</div>
        <div class="hero-value" style="color:{dd_color};">{_safe(max_dd, 2)}%</div>
        <div class="hero-sub">peak-to-trough</div>
    </div>

    <!-- Row 3: Batch + VS SPY -->
    <div class="hero-card hero-batch">
        <div class="hero-label">ACTIVE BATCH</div>
        <div class="hero-value" style="color:#ffffff;">#{active_rid}</div>
        <div class="hero-sub">day {days_elapsed} / 20</div>
    </div>
    <div class="hero-card hero-vspy">
        <div class="hero-label">VS BENCHMARK</div>
        <div class="hero-value" style="color:{vs_spy_color};">{vs_spy_str}</div>
        <div class="hero-sub2" style="color:{vs_spy_color};">{vs_spy_sub}</div>
    </div>

</div>

<!-- ── EQUITY CHART ───────────────────────────────────────────── -->
<div class="section-title">📈 EQUITY CURVE</div>
<div class="chart-wrap">
    <canvas id="equityChart"></canvas>
</div>

<!-- ── MINI STATS ─────────────────────────────────────────────── -->
<div class="section-title">📊 PERFORMANCE STATS</div>
<div class="stats-grid">
    <div class="stat-box">
        <div class="stat-label">AVG DAILY RETURN</div>
        <div class="stat-value" style="color:{adr_color};">{'+' if avg_daily_ret >= 0 else ''}{_safe(avg_daily_ret, 3)}%</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">DAILY VOLATILITY</div>
        <div class="stat-value" style="color:#cccccc;">{_safe(volatility, 3)}%</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">BEST DAY</div>
        <div class="stat-value" style="color:{bd_color};">+{_safe(best_day, 2)}%</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">WORST DAY</div>
        <div class="stat-value" style="color:{wd_color};">{_safe(worst_day, 2)}%</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">BEST CYCLE</div>
        <div class="stat-value" style="color:{bc_color};">{'+' if best_cycle and best_cycle >= 0 else ''}{_safe(best_cycle, 2)}%</div>
    </div>
    <div class="stat-box">
        <div class="stat-label">WORST CYCLE</div>
        <div class="stat-value" style="color:{wc_color};">{_safe(worst_cycle, 2)}%</div>
    </div>
</div>

<!-- Win Rate Bar -->
<div class="winrate-wrap">
    <div class="winrate-label">WIN RATE (daily) <span style="color:#00ff88;">{_safe(win_rate, 1)}%</span></div>
    <div class="winrate-track">
        <div class="winrate-fill" style="width:{wr_bar_pct}%;"></div>
    </div>
</div>

{holdings_html}

{cycles_html}

<p class="footer">Generated {timestamp} · Alpha Executor · Quant Radar</p>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
const DATA = {chart_json};
</script>
<script src="execution.js"></script>
</body>
</html>"""

    out_path = OUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"🌐 Execution dashboard saved → {out_path}")
    return html


if __name__ == "__main__":
    build_execution_dashboard()