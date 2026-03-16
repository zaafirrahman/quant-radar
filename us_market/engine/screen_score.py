import numpy as np

def calculate_score(df):

    df = df.copy()

    df["SMA_V20"] = df["Volume"].rolling(20).mean()

    df["H325"] = df["High"].rolling(325).max()
    df["L325"] = df["Low"].rolling(325).min()

    df["P14"] = df["Close"] - df["Close"].shift(14)

    df["VOL_SURGE"] = df["Volume"] / df["SMA_V20"]

    df["RANGE_POS"] = (
        (df["Close"] - df["L325"]) /
        (df["H325"] - df["L325"]).replace(0, np.nan)
    )

    df["SCORE"] = (
        df["P14"]
        * df["VOL_SURGE"]
        * df["RANGE_POS"]
    )

    # Remove warmup period
    df = df.iloc[325:].copy()

    df.dropna(inplace=True)

    return df