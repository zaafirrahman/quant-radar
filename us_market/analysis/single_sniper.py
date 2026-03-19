import math
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup

from us_market.engine.screen_score import calculate_score


# ─────────────────────────────────────────
#  SHARIA COMPLIANCE SCRAPER
# ─────────────────────────────────────────

def get_sharia_status(ticker: str) -> str:
    """Scrape Zoya Finance for halal compliance status."""
    try:
        url = f"https://zoya.finance/stocks/{ticker.lower()}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")

        # Zoya renders compliance in an h2 tag like:
        # "BKNG stock is Shariah-compliant"
        # "BKNG stock is not Shariah-compliant"
        # "BKNG stock is doubtful"
        h2 = soup.find("h2")
        if h2:
            text = h2.get_text(strip=True).lower()
            if "not shariah" in text or "not halal" in text:
                return "Not Halal"
            elif "doubtful" in text:
                return "Doubtful"
            elif "shariah-compliant" in text or "shariah compliant" in text:
                return "Halal"
        return "Not Covered"
    except Exception:
        return "N/A"


# ─────────────────────────────────────────
#  BACKTEST ENGINE
# ─────────────────────────────────────────

def run_single_sniper(ticker: str, company: str) -> dict | None:
    """
    Full sniper analysis for one ticker.

    Returns a dict with:
        summary   – one-row dict  (for sniper_summary.csv + bulk dashboard)
        signals   – DataFrame     (for TICKER_signals.csv + single dashboard)
        meta      – misc scalars  (current_price, threshold, score, etc.)
    Returns None if data is insufficient.
    """
    print(f"  🔍 Analysing {ticker}...")

    # ── 1. Download & score ──────────────────────────────────────────────────
    raw = yf.download(ticker, period="3y", interval="1d", progress=False)

    if raw.empty:
        print(f"  ❌ No data for {ticker}")
        return None

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)

    raw = raw.dropna()

    scored = calculate_score(raw)          # uses the shared engine
    if len(scored) < 20:
        print(f"  ⚠️  Not enough scored rows for {ticker}")
        return None

    # ── 2. Current state ─────────────────────────────────────────────────────
    current_score = float(scored["SCORE"].iloc[-1])
    current_price = float(scored["Close"].iloc[-1])
    threshold     = float(scored["SCORE"].quantile(0.95))

    # ── 3. Historical signals (above threshold) ───────────────────────────────
    signal_rows = scored[scored["SCORE"] > threshold].copy()

    results = []
    for date, row in signal_rows.iterrows():
        idx = raw.index.get_loc(date)
        if idx + 20 >= len(raw):
            continue
        entry = float(raw["Close"].iloc[idx])
        p5    = float(raw["Close"].iloc[idx + 5])
        p10   = float(raw["Close"].iloc[idx + 10])
        p20   = float(raw["Close"].iloc[idx + 20])
        results.append({
            "Date":           date.strftime("%Y-%m-%d"),
            "Signal_Score":   round(float(row["SCORE"]), 2),
            "Entry":          round(entry, 2),
            "Return_5d (%)":  round((p5  / entry - 1) * 100, 2),
            "Return_10d (%)": round((p10 / entry - 1) * 100, 2),
            "Return_20d (%)": round((p20 / entry - 1) * 100, 2),
            "W/L":            "✅ WIN" if p20 > entry else "❌ LOS",
        })

    if not results:
        print(f"  ⚠️  No completed signals for {ticker}")
        return None

    signals_df = pd.DataFrame(results)

    # ── 4. Strategy stats ────────────────────────────────────────────────────
    ar5  = round(signals_df["Return_5d (%)"].mean(),  2)
    ar10 = round(signals_df["Return_10d (%)"].mean(), 2)
    ar20 = round(signals_df["Return_20d (%)"].mean(), 2)
    wr5  = round((signals_df["Return_5d (%)"]  > 0).mean() * 100, 2)
    wr10 = round((signals_df["Return_10d (%)"] > 0).mean() * 100, 2)
    wr20 = round((signals_df["Return_20d (%)"] > 0).mean() * 100, 2)
    n    = len(signals_df)

    stats_df = pd.DataFrame(
        {"Avg Return (%)": [ar5, ar10, ar20],
         "Win Rate (%)":   [wr5, wr10, wr20]},
        index=["5-Day", "10-Day", "20-Day"]
    )

    # ── 5. Swing score & verdict ─────────────────────────────────────────────
    momentum        = (ar5 * 3) + (ar10 * 2) + (ar20 * 1)
    win_factor      = (wr5 * 0.5) + (wr10 * 0.3) + (wr20 * 0.2)
    volatility_boost = abs(ar5)
    signal_boost    = math.sqrt(n)
    sniper_score     = round(momentum * win_factor * signal_boost * (1 + volatility_boost / 10), 2)

    if sniper_score > 500:
        verdict = "💎 S-TIER: EMITEN MONSTER (High Conviction)"
    elif sniper_score > 200:
        verdict = "🥇 A-TIER: SANGAT LAYAK SWING"
    elif sniper_score > 50:
        verdict = "🥈 B-TIER: LUMAYAN (Moderate)"
    else:
        verdict = "🥉 C-TIER: KURANG HISTORIS / BERISIKO"

    # ── 6. Sharia compliance ─────────────────────────────────────────────────
    sharia = get_sharia_status(ticker)

    # ── 7. Recent signals (regime check) ─────────────────────────────────────
    recent_df = signals_df.tail(10).reset_index(drop=True)

    # ── 8. Power ranking ─────────────────────────────────────────────────────
    power_df = signals_df.sort_values("Signal_Score", ascending=False).reset_index(drop=True)
    power_df.index = power_df.index + 1
    power_df.index.name = "Rank"

    # ── 9. Summary row (for bulk dashboard) ──────────────────────────────────
    summary = {
        "Ticker":          ticker,
        "Company":         company,
        "WinRate_5d":      wr5,
        "WinRate_10d":     wr10,
        "WinRate_20d":     wr20,
        "AvgRet_5d":       ar5,
        "AvgRet_10d":      ar10,
        "AvgRet_20d":      ar20,
        "Sample":  n,
        "Sniper_Score":     sniper_score,
        "Sharia":          sharia,
    }

    print(f"  ✅ {ticker} done — Swing Score: {sniper_score} | Sharia: {sharia}")

    return {
        "summary":       summary,
        "signals":       signals_df,
        "stats":         stats_df,
        "recent":        recent_df,
        "power_ranking": power_df,
        "meta": {
            "ticker":        ticker,
            "company":       company,
            "current_price": current_price,
            "current_score": current_score,
            "threshold":     threshold,
            "sniper_score":   sniper_score,
            "verdict":       verdict,
            "sharia":        sharia,
        },
    }