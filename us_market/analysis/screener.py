import yfinance as yf
import pandas as pd

from us_market.engine.screen_score import calculate_score


def run_screener(tickers):

    data = yf.download(
        tickers,
        period="2y",
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

            last = score_df.iloc[-1]

            results.append({
                "Ticker": ticker,
                "Last_Price": round(last["Close"],2),
                "Momentum_14d": round(last["P14"],2),
                "Vol_Surge": round(last["VOL_SURGE"],2),
                "Range_Pos_325": round(last["RANGE_POS"],4),
                "Quant_Score": round(last["SCORE"],4)
            })

        except:
            continue

    report = pd.DataFrame(results)

    report = report.sort_values(
        by="Quant_Score",
        ascending=False
    )

    report.reset_index(drop=True, inplace=True)
    report.index += 1
    report.insert(0,"Rank",report.index)

    return report