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
#  EDGE HELPERS
# ─────────────────────────────────────────

def _calc_edge(ar: float, wr: float) -> float:
    """Risk-adjusted return. WR=0 → ar directly so negatives propagate."""
    if wr == 0:
        return ar
    return ar * (wr / 100)


def _normalize_edge(edge_raw: float) -> float:
    """tanh compression → -1..+1, then shift to 0..1."""
    return (math.tanh(edge_raw / 3) + 1) / 2


def _signal_characteristic(e5: float, e10: float, e20: float) -> str:
    if e5 > 0 and e10 > 0 and e20 > 0:
        if e5 >= e10 >= e20:
            return "BURST"
        elif e20 >= e10 >= e5:
            return "COMPOUNDER"
        else:
            return "STEADY"
    elif e20 > 0 and e5 <= 0:
        return "COMPOUNDER"
    elif e5 > 0 and e20 <= 0:
        return "BURST"
    else:
        return "ERRATIC"


# ─────────────────────────────────────────
#  QUALITY HELPERS
# ─────────────────────────────────────────

def _calc_sample_score(n: int, max_n: int = 50) -> float:
    """Diminishing returns — sqrt scale. Max at max_n signals."""
    return round(min(math.sqrt(n) / math.sqrt(max_n), 1.0), 4)


def _calc_cluster_score(dates: list) -> float:
    """
    Signals spread across time vs clustered.
    Gap < 5 trading days = same cluster.
    Score = n_clusters / n_signals → 0..1
    """
    if len(dates) <= 1:
        return round(1.0 / max(len(dates), 1), 4)
    sorted_dates = sorted(pd.to_datetime(dates))
    clusters = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days >= 5:
            clusters += 1
    return round(clusters / len(dates), 4)


def _calc_stability_score(returns: pd.Series, signals_df: pd.DataFrame) -> float:
    """
    Two sub-components:
    1. CV stability  — consistent return magnitude
    2. Temporal      — no decay between early and recent signals
    """
    # ── CV stability ──────────────────────────────────────────
    mean_r = returns.mean()
    std_r  = returns.std()
    if abs(mean_r) < 1e-9:
        cv_stability = 0.0
    else:
        cv_stability = 1 / (1 + abs(std_r / mean_r))

    # ── Temporal consistency ──────────────────────────────────
    n = len(signals_df)
    if n < 4:
        # too few signals to split meaningfully → neutral
        temporal = 0.5
    else:
        mid       = n // 2
        wr_first  = (signals_df.iloc[:mid]["Return_20d (%)"] > 0).mean() * 100
        wr_second = (signals_df.iloc[mid:]["Return_20d (%)"] > 0).mean() * 100
        temporal  = 1 - abs(wr_first - wr_second) / 100

    return round(0.5 * cv_stability + 0.5 * temporal, 4)


# ─────────────────────────────────────────
#  SNIPER SCORE
# ─────────────────────────────────────────

def _calc_sniper_score(edge_raw: float, quality_score: float) -> float:
    """
    Hard gate at edge = 0:
    - Negative edge → quality cannot rescue → capped below 50
    - Positive edge → combined score 50-100
    """
    edge_01 = _normalize_edge(edge_raw)
    if edge_raw <= 0:
        score = edge_01 * quality_score * 100
    else:
        score = ((edge_01 + quality_score) / 2) * 100
    return round(score, 2)


def _verdict(sniper_score: float) -> str:
    if sniper_score >= 75:
        return "💎 S-TIER: HIGH CONVICTION"
    elif sniper_score >= 60:
        return "🥇 A-TIER: STRONG SIGNAL"
    elif sniper_score >= 50:
        return "🥈 B-TIER: MODERATE SIGNAL"
    else:
        return "🥉 C-TIER: AVOID"


# ─────────────────────────────────────────
#  AVGWIN / AVGLOSS HELPER
# ─────────────────────────────────────────

def _calc_win_loss(series: pd.Series) -> tuple[float, float]:
    """
    Returns (avg_win, avg_loss) for a return series.
    avg_win  → mean of positive returns (or 0.0 if none)
    avg_loss → mean of negative returns, always negative (or 0.0 if none)
    """
    wins   = series[series > 0]
    losses = series[series <= 0]
    avg_win  = round(wins.mean(),   2) if len(wins)   > 0 else 0.0
    avg_loss = round(losses.mean(), 2) if len(losses) > 0 else 0.0
    return avg_win, avg_loss


# ─────────────────────────────────────────
#  BACKTEST ENGINE
# ─────────────────────────────────────────

def run_single_sniper(ticker: str, company: str) -> dict | None:
    """
    Full sniper analysis for one ticker.
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

    scored = calculate_score(raw)
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

    # ── AvgWin & AvgLoss per horizon ─────────────────────────────────────────
    aw5,  al5  = _calc_win_loss(signals_df["Return_5d (%)"])
    aw10, al10 = _calc_win_loss(signals_df["Return_10d (%)"])
    aw20, al20 = _calc_win_loss(signals_df["Return_20d (%)"])

    stats_df = pd.DataFrame(
        {
            "Avg Return (%)": [ar5,  ar10,  ar20],
            "Win Rate (%)":   [wr5,  wr10,  wr20],
            "Avg Win (%)":    [aw5,  aw10,  aw20],
            "Avg Loss (%)":   [al5,  al10,  al20],
        },
        index=["5-Day", "10-Day", "20-Day"]
    )

    # ── 5. Edge Score ────────────────────────────────────────────────────────
    e5  = _calc_edge(ar5,  wr5)
    e10 = _calc_edge(ar10, wr10)
    e20 = _calc_edge(ar20, wr20)

    edge_score_raw = round((e5 + e10 + e20) / 3, 4)
    characteristic = _signal_characteristic(e5, e10, e20)

    # ── 6. Quality Score ─────────────────────────────────────────────────────
    sample_score    = _calc_sample_score(n)
    cluster_score   = _calc_cluster_score(signals_df["Date"].tolist())
    stability_score = _calc_stability_score(signals_df["Return_20d (%)"], signals_df)
    quality_score   = round((sample_score + cluster_score + stability_score) / 3, 4)

    # ── 7. Sniper Score ───────────────────────────────────────────────────────
    sniper_score = _calc_sniper_score(edge_score_raw, quality_score)
    verdict      = _verdict(sniper_score)

    # ── 8. Sharia compliance ─────────────────────────────────────────────────
    sharia = get_sharia_status(ticker)

    # ── 9. Recent signals (regime check) ─────────────────────────────────────
    recent_df = signals_df.tail(10).reset_index(drop=True)

    # ── 10. Power ranking ────────────────────────────────────────────────────
    power_df = signals_df.sort_values("Signal_Score", ascending=False).reset_index(drop=True)
    power_df.index = power_df.index + 1
    power_df.index.name = "Rank"

    # ── 11. Summary row ───────────────────────────────────────────────────────
    summary = {
        "Ticker":          ticker,
        "Company":         company,
        "WR_5":            wr5,
        "WR_10":           wr10,
        "WR_20":           wr20,
        "AVG_5":           ar5,
        "AVG_10":          ar10,
        "AVG_20":          ar20,
        "AvgWin_5":        aw5,
        "AvgLoss_5":       al5,
        "AvgWin_10":       aw10,
        "AvgLoss_10":      al10,
        "AvgWin_20":       aw20,
        "AvgLoss_20":      al20,
        "Sample":          n,
        "Edge_Score":      edge_score_raw,
        "Characteristic":  characteristic,
        "Sample_Score":    sample_score,
        "Cluster_Score":   cluster_score,
        "Stability_Score": stability_score,
        "Quality_Score":   quality_score,
        "Sniper_Score":    sniper_score,
        "Sharia":          sharia,
    }

    print(f"  ✅ {ticker} — Edge: {edge_score_raw} | Quality: {quality_score} | Sniper: {sniper_score} | {characteristic} | {sharia}")

    return {
        "summary":        summary,
        "signals":        signals_df,
        "stats":          stats_df,
        "recent":         recent_df,
        "power_ranking":  power_df,
        "meta": {
            "ticker":           ticker,
            "company":          company,
            "current_price":    current_price,
            "current_score":    current_score,
            "threshold":        threshold,
            "edge_score":       edge_score_raw,
            "characteristic":   characteristic,
            "sample_score":     sample_score,
            "cluster_score":    cluster_score,
            "stability_score":  stability_score,
            "quality_score":    quality_score,
            "sniper_score":     sniper_score,
            "verdict":          verdict,
            "sharia":           sharia,
        },
    }