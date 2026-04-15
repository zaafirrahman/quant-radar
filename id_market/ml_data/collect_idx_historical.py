"""
collect_idx_historical.py
==========================
Seed script — jalankan SEKALI secara manual untuk mengisi idx_ohlcv.parquet
dengan data historis 3 tahun (2022–2024) dari yfinance (.JK suffix).

Data ini TERPISAH dari parquet IDX utamamu (yang ada freq, foreign, dll).
Tujuannya hanya untuk training ML — OHLCV + derived momentum features.

Output: ml_data/idx_ohlcv.parquet
Schema: date | ticker | open | high | low | close | volume | [derived features]
"""

import yfinance as yf
import pandas as pd
from pathlib import Path
import time
import warnings
warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR  = Path("ml_data")
OUTPUT_FILE = OUTPUT_DIR / "idx_ohlcv.parquet"

START_DATE = "2022-01-01"
END_DATE   = "2024-12-31"

BATCH_SIZE  = 50     # fetch N tickers sekaligus (yfinance batch)
SLEEP_BATCH = 2.0    # detik antar batch

# IDX tickers — semua yang listed di IDX (~900 tickers)
# Kita auto-fetch dari Wikipedia / hardcode universe Pluang-mu
# Untuk simplicity, kita pakai IDX Composite components + common stocks
# Kamu bisa replace list ini dengan list ticker dari Pluang universe-mu

# NOTE: yfinance IDX format = "BBCA.JK", "TLKM.JK", dst.

# Untuk seed, kita ambil pendekatan: fetch IHSG composite + LQ45 + IDX80
# lalu expand ke semua yang bisa di-fetch

# Starter universe — kamu bisa expand dengan list dari scraped IDX-mu
IDX_TICKERS_RAW = """
AALI ABBA ABDA ABMM ABNA ABSORB ACST ADES ADHI ADMF ADMG ADMR ADRO AGII AGRO
AHAP AIMS AISA AKKU AKPI AKRA AKSI ALDO ALKA ALMI ALTO AMAG AMFG AMPO AMRT
ANDI ANJT ANTM APEX APII APLI APLN ARCI ARGO ARKA ARNA ARMY ARTA ASBI ASDM
ASII ASJT ASLC ASMI ASRM ASSA ATAP ATPK AUTO AVIA AVIT AYLS BABP BACA BACK
BAJA BALI BAPA BAPS BAYU BBCA BBHI BBKP BBMD BBNI BBRI BBSI BBTN BBYB BCAP
BCIC BCIP BEKS BELL BEST BFIN BGTG BHAT BHIT BIKA BIMA BIPI BIRD BISI BJBR
BJTM BKDP BKSL BLTA BLTZ BMRI BMSR BMTR BNBA BNBR BNII BNLI BOBA BOGA BRAM
BRMS BRNL BRPT BSDE BSIM BSSR BTEK BTON BTPN BTPS BUGO BUMI BUVA BVIC BWPT
CAKK CAMP CANI CARS CASA CATP CBMF CCMD CEKA CFIN CINT CITA CITY CLPI CMNP
CMNT CMPP COAL COCO CORF COWL CPRO CSIS CSMI CSRA CTRA CTRS DADA DART DATA
DAVE DBDH DBO DCII DEWA DFAM DIVA DKFT DLTA DMAS DNAR DNET DPNS DPUM DSSA
DUTI DVLA DWGL DYNS ECII EDGE EKAD ELSA ELTY EMDE EMTK ENRG ENVY EPAC ERAA
ESSA EURO EXCL FAST FASW FILM FIRE FITR FLMC FMII FOOD FORE FORU FPNI FREN
GAGE GAMA GBIC GEMS GGRM GJTL GLOB GLVA GMFI GMTD GOLD GPRA GRIA GSMF GTBO
GTSI GWSA GZCO HADE HDTX HEAL HELI HEXA HITS HMSP HOKI HRUM IATA ICON IDEA
IGAR IIKP IMJS IMPC INCI INDO INDF INDX INDY INET INOV INPC INPP INRU INTA
INTD INTP IPPE IPOL ISAT ISSP ITIC IVIA JAST JAWA JECC JGLE JKON JKSW JPFA
JPRS JRPT JSMR JTPE KAEF KALO KARW KBAG KBLI KBLM KBLV KDSI KEEN KIAS KICK
KIJA KINO KIOS KLBF KMDS KMTR KOBX KOIN KONI KOPI KOTA KPAS KPIG KRAS KREN
LABA LAND LCGP LEAD LINK LION LMAS LMSH LPCK LPGI LPIN LPKR LPPF LSIP LTLS
LUCK MABA MAIN MAMI MAPA MARK MASA MAYA MBAP MBSS MCAS MDIA MDKI MDLN MDLY
MDRN MEDC MEGA MERK MFIN MFMI MGNA MICE MIDI MIKA MITI MKPI MLBI MLIA MLPL
MLPT MMIX MNCN MNCS MOLI MPMX MPOW MPPA MPRO MRAT MSKY MTLA MTMH MTRA MTRO
MTSM MYOH MYOR NASI NCKL NETV NFCX NICL NISP NRCA NUSA NWSA OCAP OILS OMRE
OONA OPMS OTTO PADI PALM PAMG PANS PBID PBSA PCAR PDPP PEHA PGAS PGUN PICO
PJAA PKPK PLAN PLIN PLNT PMMP PNBS PNLF PNSE POLA POLL POLU POOL POSA POWR
PPRE PPRO PRDA PRIM PSAB PSGO PSKT PTBA PTDU PTIS PTPP PTRO PTSP PUDP PURE
PWON PYFA RAJA RALS RANC RBMS RDTX REAL RELI RIGS RIMO RISE RMKE ROCK RODA
ROTI RUIS RUPF SAFE SAME SATU SCCO SCMA SDMU SDPC SEMA SIDO SILO SIMP SKBM
SKLT SMAR SMCB SMDR SMGR SMKL SMKM SMMT SMRA SMSM SOFA SOHO SONA SOTS SPMO
SRAJ SRTG SSIA SSMS STAR STTP SUGI SUGN SULR SUNI SURE SWAT TALF TAMA TARA
TEBE TECH TFCO TGRA TIFA TINS TIRA TIRT TJHI TKIM TLKM TMPO TNCA TOBA TOPS
TOTL TOTO TOWR TPIA TPMA TRIL TRIM TRJA TRST TRUS TSPC TUGU UANG UCID ULTJ
UNIC UNIT UNSP UNTR UNVR URBN VICI VIDA VINS VIVA VOKS VRNA WAPO WEGE WEHA
WIKA WIFI WIKA WINS WKST WMPP WOMF WOOD WPAK WTON YELO YPAS YULE ZBRA ZYRX
""".split()

# Deduplicate
IDX_TICKERS_RAW = sorted(set(IDX_TICKERS_RAW))
IDX_TICKERS_YF  = [f"{t}.JK" for t in IDX_TICKERS_RAW]

print(f"Universe size: {len(IDX_TICKERS_YF)} tickers")


# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_batch(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV untuk batch tickers, return long-format DataFrame."""
    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            group_by="ticker",
        )
    except Exception as e:
        print(f"    [ERROR] Batch download failed: {e}")
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    records = []

    # Single ticker: columns = [Open, High, Low, Close, Volume]
    if len(tickers) == 1:
        ticker = tickers[0]
        df = raw.copy()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower()
                      for c in df.columns]
        df["ticker"] = ticker.replace(".JK", "")
        df.index.name = "date"
        df = df.reset_index()
        return df[["date", "ticker", "open", "high", "low", "close", "volume"]]

    # Multi ticker: yfinance returns MultiIndex (field, ticker) or (ticker, field)
    # Detect order from level values
    lvl0 = raw.columns.get_level_values(0).unique().tolist()
    # If level 0 contains field names like 'Close', order is (field, ticker)
    field_first = any(x in lvl0 for x in ["Close", "Open", "High", "Low", "Volume"])

    for ticker in tickers:
        try:
            if field_first:
                # Access pattern: raw["Close"][ticker]
                if ticker not in raw.columns.get_level_values(1):
                    continue
                df = pd.DataFrame({
                    "open":   raw["Open"][ticker] if "Open" in raw.columns.get_level_values(0) else None,
                    "high":   raw["High"][ticker] if "High" in raw.columns.get_level_values(0) else None,
                    "low":    raw["Low"][ticker]  if "Low"  in raw.columns.get_level_values(0) else None,
                    "close":  raw["Close"][ticker],
                    "volume": raw["Volume"][ticker] if "Volume" in raw.columns.get_level_values(0) else None,
                }, index=raw.index)
            else:
                # Access pattern: raw[ticker]["Close"]
                if ticker not in raw.columns.get_level_values(0):
                    continue
                sub = raw[ticker].copy()
                sub.columns = [c.lower() for c in sub.columns]
                # Handle adj close column name variations
                if "adj close" in sub.columns:
                    sub = sub.drop(columns=["adj close"], errors="ignore")
                df = sub[["open", "high", "low", "close", "volume"]]

            df = df.dropna(subset=["close"])
            if df.empty:
                continue
            df = df.copy()
            df["ticker"] = ticker.replace(".JK", "")
            df.index.name = "date"
            df = df.reset_index()
            records.append(df[["date", "ticker", "open", "high", "low", "close", "volume"]])
        except Exception:
            continue

    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tambah fitur momentum per ticker — ini yang akan jadi ticker-level features
    saat training ML nantinya.

    Computed per ticker (groupby), sorted by date.
    """
    df = df.sort_values(["ticker", "date"]).copy()

    def per_ticker(g):
        g = g.copy()
        c = g["close"]
        v = g["volume"]

        g["ret_1d"]  = c.pct_change(1) * 100          # return kemarin
        g["ret_3d"]  = c.pct_change(3) * 100
        g["ret_5d"]  = c.pct_change(5) * 100
        g["ret_20d"] = c.pct_change(20) * 100

        g["vol_20d_avg"] = v.rolling(20).mean()
        g["vol_ratio"]   = v / g["vol_20d_avg"]        # volume spike indicator

        # Volatility
        g["volatility_20d"] = (c.pct_change() * 100).rolling(20).std()

        # Price vs moving averages
        g["ma5"]  = c.rolling(5).mean()
        g["ma20"] = c.rolling(20).mean()
        g["above_ma5"]  = (c > g["ma5"]).astype(int)
        g["above_ma20"] = (c > g["ma20"]).astype(int)

        # Target label: apakah next day close naik >3% dari hari ini?
        g["next_day_ret"] = c.pct_change(1).shift(-1) * 100
        g["label"]        = (g["next_day_ret"] > 3.0).astype(int)

        return g

    result = df.groupby("ticker", group_keys=False).apply(per_ticker)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"{'='*60}")
    print(f"  Quant Radar — IDX OHLCV Historical Collector")
    print(f"  Period : {START_DATE} → {END_DATE}")
    print(f"  Tickers: {len(IDX_TICKERS_YF)}")
    print(f"  Label  : next_day_ret > 3%")
    print(f"{'='*60}\n")

    OUTPUT_DIR.mkdir(exist_ok=True)

    if OUTPUT_FILE.exists():
        existing = pd.read_parquet(OUTPUT_FILE)
        print(f"[INFO] File sudah ada: {len(existing)} rows")
        ans = input("Overwrite? (y/n): ").strip().lower()
        if ans != "y":
            print("[ABORT] Cancelled.")
            return

    all_batches = []
    batches = [IDX_TICKERS_YF[i:i+BATCH_SIZE]
               for i in range(0, len(IDX_TICKERS_YF), BATCH_SIZE)]

    print(f"[1/3] Fetching IDX OHLCV in {len(batches)} batches of {BATCH_SIZE}...\n")

    failed_tickers = []
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i:2d}/{len(batches)} — {batch[0]} … {batch[-1]}")
        df_batch = fetch_batch(batch, START_DATE, END_DATE)

        if df_batch.empty:
            print(f"    [WARN] Batch {i} returned no data")
            failed_tickers.extend(batch)
        else:
            success = df_batch["ticker"].nunique()
            print(f"    ✓ {success}/{len(batch)} tickers, {len(df_batch)} rows")
            all_batches.append(df_batch)

        if i < len(batches):
            time.sleep(SLEEP_BATCH)

    if not all_batches:
        print("[ERROR] No data fetched. Check internet / yfinance.")
        return

    print(f"\n[2/3] Combining & computing derived features...")
    df_all = pd.concat(all_batches, ignore_index=True)
    df_all["date"] = pd.to_datetime(df_all["date"])

    # Remove timezone info jika ada
    if hasattr(df_all["date"].dt, "tz") and df_all["date"].dt.tz is not None:
        df_all["date"] = df_all["date"].dt.tz_localize(None)

    print(f"  Raw rows     : {len(df_all):,}")
    print(f"  Unique ticker: {df_all['ticker'].nunique()}")
    print(f"  Date range   : {df_all['date'].min().date()} → {df_all['date'].max().date()}")

    df_featured = add_derived_features(df_all)

    # Drop rows tanpa label (last row per ticker, atau awal yg belum ada rolling)
    before = len(df_featured)
    df_featured = df_featured.dropna(subset=["label", "ret_5d", "volatility_20d"])
    print(f"  After dropna : {len(df_featured):,} rows (dropped {before - len(df_featured):,})")

    label_dist = df_featured["label"].value_counts(normalize=True) * 100
    print(f"\n  Label distribution:")
    print(f"    0 (tidak naik >3%): {label_dist.get(0, 0):.1f}%")
    print(f"    1 (naik >3%)       : {label_dist.get(1, 0):.1f}%")

    if failed_tickers:
        print(f"\n  Failed tickers ({len(failed_tickers)}): {failed_tickers[:10]}{'...' if len(failed_tickers)>10 else ''}")

    print(f"\n[3/3] Saving to {OUTPUT_FILE}...")
    df_featured.to_parquet(OUTPUT_FILE, engine="pyarrow",
                           compression="snappy", index=False)
    print(f"  ✓ Saved: {OUTPUT_FILE}")
    print(f"  File size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"\n[DONE] {df_featured['ticker'].nunique()} tickers, {len(df_featured):,} rows stored.")
    print(f"[NEXT] Jalankan train.py untuk training XGBoost model.")


if __name__ == "__main__":
    main()
