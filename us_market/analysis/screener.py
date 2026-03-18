import yfinance as yf
import pandas as pd
import numpy as np

from us_market.engine.screen_score import calculate_score

def run_screener(tickers):

    data = yf.download(
        tickers,
        period="3y",
        interval="1d",
        group_by="ticker",
        threads=True
    )

    results = []

    for ticker in tickers:

        try:
            df = data[ticker].dropna()

            if len(df) < 325:
                continue

            score_df = calculate_score(df)

            # =========================
            # HISTORICAL STATS
            # =========================
            scores = score_df["SCORE"].dropna()

            mean_score = scores.mean()
            std_score = scores.std()

            # Z-score (current)
            current_score = scores.iloc[-1]
            z_score = (current_score - mean_score) / std_score if std_score != 0 else 0

            # =========================
            # THRESHOLD LOGIC (SIMPLE VERSION)
            # =========================
            # pakai percentile sebagai threshold awal (misal top 5%)
            threshold = np.percentile(scores, 95)

            # =========================
            # DISTANCE
            # =========================
            distance_pct = (current_score - threshold) / threshold

            last = score_df.iloc[-1]

            results.append({
                "Ticker": ticker,
                "Last_Price": round(last["Close"], 2),
                "Momentum_14d": round(last["P14"], 2),
                "Vol_Surge": round(last["VOL_SURGE"], 2),
                "Range_Pos_325": round(last["RANGE_POS"], 4),

                "Quant_Score": round(current_score, 4),
                "Threshold": round(threshold, 4),
                "Distance_%": round(distance_pct * 100, 2),
                "Z_Score": round(z_score, 2)
            })

        except Exception as e:
            continue

    report = pd.DataFrame(results)

    # =========================
    # RANK BY DISTANCE
    # =========================
    report = report.sort_values(
        by="Distance_%",
        ascending=False
    )

    report.reset_index(drop=True, inplace=True)
    report.index += 1
    report.insert(0, "Rank", report.index)

    return report