"""
append_daily.py
===============
Append 1 hari data terbaru ke idx_ohlcv.parquet dan us_features.parquet.

Dijalankan: harian via GH Actions, pagi hari (setelah US close malam sebelumnya)
Output    : Append ke parquet yang sudah ada
"""

import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
# Path resolution: selalu relatif terhadap lokasi script ini
SCRIPT_DIR = Path(__file__).parent
IDX_FILE   = SCRIPT_DIR / "idx_ohlcv.parquet"
US_FILE    = SCRIPT_DIR / "us_features.parquet"

# IDX tickers (sama seperti collect_idx_historical.py)
IDX_TICKERS_RAW = """
AADI AALI ABBA ABDA ABMM ACES ACRO ACST ADCP ADES ADHI ADMF ADMG ADMR ADRO
AEGS AGAR AGII AGRO AGRS AHAP AIMS AISA AKKU AKPI AKRA AKSI ALDO ALII ALKA
ALMI ALTO AMAG AMAN AMAR AMFG AMIN AMMN AMMS AMOR AMRT ANDI ANJT ANTM APEX
APIC APII APLI APLN ARCI AREA ARGO ARII ARKA ARKO ARMY ARNA ARTA ARTI ARTO
ASBI ASDM ASGR ASHA ASII ASJT ASLC ASLI ASMI ASPI ASPR ASRI ASRM ASSA ATAP
ATIC ATLA AUTO AVIA AWAN AXIO AYAM AYLS BABP BABY BACA BAIK BAJA BALI BANK
BAPA BAPI BATA BATR BAUT BAYU BBCA BBHI BBKP BBLD BBMD BBNI BBRI BBRM BBSI
BBSS BBTN BBYB BCAP BCIC BCIP BDKR BDMN BEBS BEEF BEER BEKS BELI BELL BESS
BEST BFIN BGTG BHAT BHIT BIKA BIKE BIMA BINA BINO BIPI BIPP BIRD BISI BJBR
BJTM BKDP BKSL BKSW BLES BLOG BLTA BLTZ BLUE BMAS BMBL BMHS BMRI BMSR BMTR
BNBA BNBR BNGA BNII BNLI BOAT BOBA BOGA BOLA BOLT BOSS BPFI BPII BPTR BRAM
BREN BRIS BRMS BRNA BRPT BRRC BSBK BSDE BSIM BSML BSSR BSWD BTEK BTEL BTON
BTPN BTPS BUAH BUDI BUKA BUKK BULL BUMI BUVA BVIC BWPT BYAN CAKK CAMP CANI
CARE CARS CASA CASH CASS CBDK CBMF CBPE CBRE CBUT CCSI CDIA CEKA CENT CFIN
CGAS CHEK CHEM CHIP CINT CITA CITY CLAY CLEO CLPI CMNP CMNT CMPP CMRY CNKO
CNMA CNTB CNTX COAL COCO COIN COWL CPIN CPRI CPRO CRAB CRSN CSAP CSIS CSMI
CSRA CTBN CTRA CTTH CUAN CYBR DAAZ DADA DART DATA DAYA DCII DEAL DEFI DEPO
DEWA DEWI DFAM DGIK DGNS DGWG DIGI DILD DIVA DKFT DKHH DLTA DMAS DMMX DMND
DNAR DNET DOID DOOH DOSS DPNS DPUM DRMA DSFI DSNG DSSA DUCK DUTI DVLA DWGL
DYAN EAST ECII EDGE EKAD ELIT ELPI ELSA ELTY EMAS EMDE EMTK ENAK ENRG ENVY
ENZO EPAC EPMT ERAA ERAL ERTX ESIP ESSA ESTA ESTI ETWA EURO EXCL FAPA FAST
FASW FILM FIMP FIRE FISH FITT FLMC FMII FOLK FOOD FORE FORU FPNI FUJI FUTR
FWCT GAMA GDST GDYR GEMA GEMS GGRM GGRP GHON GIAA GJTL GLOB GLVA GMFI GMTD
GOLD GOLF GOLL GOOD GOTO GOTOM GPRA GPSO GRIA GRPH GRPM GSMF GTBO GTRA GTSI
GULA GUNA GWSA GZCO HADE HAIS HAJJ HALO HATM HBAT HDFA HDIT HEAL HELI HERO
HEXA HGII HILL HITS HKMU HMSP HOKI HOME HOMI HOPE HOTL HRME HRTA HRUM HUMI
HYGN IATA IBFN IBOS IBST ICBP ICON IDEA IDPR IFII IFSH IGAR IIKP IKAI IKAN
IKBI IKPM IMAS IMJS IMPC INAF INAI INCF INCI INCO INDF INDO INDR INDS INDX
INDY INET INKP INOV INPC INPP INPS INRU INTA INTD INTP IOTF IPAC IPCC IPCM
IPOL IPPE IPTV IRRA IRSX ISAP ISAT ISEA ISSP ITIC ITMA ITMG JARR JAST JATI
JAWA JAYA JECC JGLE JIHD JKON JMAS JPFA JRPT JSKY JSMR JSPT JTPE KAEF KAQI
KARW KAYU KBAG KBLI KBLM KBLV KBRI KDSI KDTN KEEN KEJU KETR KIAS KICI Kija
KING KINO KIOS KJEN KKES KKGI KLAS KLBF KLIN KMDS KMTR KOBX KOCI KOIN KOKA
KONI KOPI KOTA KPIG KRAS KREN KRYA KSIX KUAS LABA LABS LAJU LAND LAPD LCGP
LCKM LEAD LFLO LIFE LINK LION LIVE LMAS LMAX LMPI LMSH LOPI LPCK LPGI LPIN
LPKR LPLI LPPF LPPS LRNA LSIP LTLS LUCK LUCY MABA MAGP MAHA MAIN MANG MAPA
MAPB MAPI MARI MARK MASB MAXI MAYA MBAP MBMA MBSS MBTO MCAS MCOL MCOR MDIA
MDIY MDKA MDKI MDLA MDLN MDRN MEDC MEDS MEGA MEJA MENN MERI MERK META MFMI
MGLV MGNA MGRO MHKI MICE MIDI MIKA MINA MINE MIRA MITI MKAP MKNT MKPI MKTR
MLBI MLIA MLPL MLPT MMIX MMLP MNCN MOLI MORA MPIX MPMX MPOW MPPA MPRO MPXL
MRAT MREI MSIE MSIN MSJA MSKY MSTI MTDL MTEL MTFN MTLA MTMH MTPS MTRA MTSM
MTWI MUTU MYOH MYOR MYTX NAIK NANO NASA NASI NATO NAYZ NCKL NELY NEST NETV
NFCX NICE NICK NICL NIRO NISP NOBU NPGF NRCA NSSS NTBK NUSA NZIA OASA OBAT
OBMD OCAP OILS OKAS OLIV OMED OMRE OMS PACK PADA PADI PALM PAMG PANI PANR
PANS PART PBID PBRX PBSA PCAR PDES PDPP PEGE PEHA PEVE PGAS PGEO PGJO PGLI
PGUN PICO PIPA PJAA PJHB PKPK PLAN PLAS PLIN PMJS PMMP PMUI PNBN PNBS PNGO
PNIN PNLF PNSE POLA POLI POLL POLU POLY POOL PORT POSA POWR PPGL PPRE PPRI
PPRO PRAY PRDA PRIM PSAB PSAT PSDN PSGO PSKT PSSI PTBA PTDU PTIS PTMP PTMR
PTPP PTPS PTPW PTRO PTSN PTSP PUDP PURA PURE PURI PWON PYFA PZZA RAAM RAFI
RAJA RALS RANC RATU RBMS RCCC RDTX REAL RELF RELI RGAS RICY RIGS RIMO RISE
RLCO RMKE RMKO ROCK RODA RONY ROTI RSCH RSGK RUIS RUNS SAFE SAGE SAME SAMF
SAPX SATU SBAT SBMA SCCO SCMA SCNP SCPI SDMU SDPC SDRA SEMA SFAN SGER SGRO
SHID SHIP SICO SIDO SILO SIMA SIMP SINI SIPD SKBM SKLT SKRN SKYB SLIS SMAR
SMBR SMCB SMDM SMDR SMGA SMGR SMIL SMKL SMKM SMLE SMMA SMMT SMRA SMRU SMSM
SNLK SOCI SOFA SOHO SOLA SONA SOSS SOTS SOUL SPMA SPRE SPTO SQMI SRAJ SRIL
SRSN SRTG SSIA SSMS SSTM STAA STAR STRK STTP SUGI SULI SUNI SUPA SUPR SURE
SURI SWAT SWID TALF TAMA TAMU TAPG TARA TAXI TAYS TBIG TBLA TBMS TCID TCPI
TDPM TEBE TECH TELE TFAS TFCO TGKA TGRA TGUK TIFA TINS TIRA TIRT TKIM TLDN
TLKM TMAS TMPO TNCA TOBA TOOL TOPS TOSK TOTL TOTO TOWR TOYS TPIA TPMA TRAM
TRGU TRIL TRIM TRIN TRIO TRIS TRJA TRON TRST TRUE TRUK TRUS TSPC TUGU TYRE
UANG UCID UDNG UFOE ULTJ UNIC UNIQ UNIT UNSP UNTD UNTR UNVR URBN UVCR VAST
VERN VICI VICO VINS VISI VIVA VKTR VOKS VRNA VTNY WAPO WBSA WEGE WEHA WGSH
WICO WIDI WIFI WIIM WIKA WINE WINR WINS WIRG WMPP WMUU WOMF WOOD WOWS WSBP
WSKT WTON YELO YOII YPAS YULE YUPI ZATA ZBRA ZINC ZONE ZYRX
""".split()

IDX_TICKERS_RAW = sorted(set(IDX_TICKERS_RAW))
IDX_TICKERS_YF  = [f"{t}.JK" for t in IDX_TICKERS_RAW]

# US tickers (sama seperti collect_us_historical.py)
US_TICKERS = {
    "^GSPC":  "sp500",
    "^IXIC":  "nasdaq",
    "^DJI":   "dow",
    "^VIX":   "vix",
    "DX-Y.NYB": "dxy",
    "GC=F":   "gold",
    "CL=F":   "crude",
    "MTF=F":  "coal",
    "XLF":    "xlf",
    "XLK":    "xlk",
    "XLE":    "xle",
    "XLB":    "xlb",
    "XLY":    "xly",
    "XLI":    "xli",
    "XLP":    "xlp",
    "EEM":    "eem",
    "ASHR":   "ashr",
    "^TNX":   "us10y",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_last_trading_date(df: pd.DataFrame, idx_file=True) -> pd.Timestamp:
    """Get last trading date dari parquet yang sudah ada."""
    if idx_file:
        df["date"] = pd.to_datetime(df["date"])
        return df["date"].max()
    else:
        return df.index.max()


def fetch_idx_daily(tickers: list[str], date: pd.Timestamp) -> pd.DataFrame:
    """Fetch OHLCV untuk 1 hari tertentu."""
    start = (date - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end   = (date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False, group_by="ticker")

    if raw.empty:
        return pd.DataFrame()

    records = []

    # Detect column order
    lvl0 = raw.columns.get_level_values(0).unique().tolist()
    ticker_first = any(str(x).endswith(".JK") for x in lvl0)

    for ticker in tickers:
        try:
            if ticker_first:
                if ticker not in raw.columns.get_level_values(0):
                    continue
                sub = raw[ticker].copy()
                sub.columns = [c.lower() for c in sub.columns]
                if "adj close" in sub.columns:
                    sub = sub.drop(columns=["adj close"], errors="ignore")
                df = sub[["open", "high", "low", "close", "volume"]]
            else:
                if ticker not in raw.columns.get_level_values(1):
                    continue
                df = pd.DataFrame({
                    "open":   raw["Open"][ticker] if "Open" in lvl0 else None,
                    "high":   raw["High"][ticker] if "High" in lvl0 else None,
                    "low":    raw["Low"][ticker]  if "Low"  in lvl0 else None,
                    "close":  raw["Close"][ticker],
                    "volume": raw["Volume"][ticker] if "Volume" in lvl0 else None,
                }, index=raw.index)

            df = df.dropna(subset=["close"])
            if df.empty:
                continue

            # Filter hanya tanggal yang diminta
            df = df[df.index.date == date.date()]
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


def fetch_us_daily(date: pd.Timestamp) -> pd.DataFrame:
    """Fetch US features untuk 1 hari tertentu."""
    start = (date - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end   = (date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    all_closes = {}
    for symbol in US_TICKERS.keys():
        try:
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                if "Close" in df.columns.get_level_values(0):
                    close = df["Close"].squeeze()
                else:
                    close = df.xs("Close", axis=1, level=1).squeeze()
            else:
                close = df["Close"].squeeze()
            close.name = symbol
            all_closes[symbol] = close
        except Exception:
            continue

    if not all_closes:
        return pd.DataFrame()

    closes_df = pd.DataFrame(all_closes)
    closes_df.index = pd.to_datetime(closes_df.index)

    # Filter hanya tanggal yang diminta
    closes_df = closes_df[closes_df.index.date == date.date()]
    if closes_df.empty:
        return pd.DataFrame()

    # Build features (sama seperti collect_us_historical.py)
    features = pd.DataFrame(index=closes_df.index)

    for symbol, col_name in US_TICKERS.items():
        if symbol not in closes_df.columns:
            continue
        series = closes_df[symbol]
        if col_name in ("vix", "us10y"):
            features[f"{col_name}_level"] = series
            features[f"{col_name}_chg"]   = series.pct_change() * 100
        else:
            features[f"{col_name}_chg"] = series.pct_change() * 100

    features["us_market_open"] = features["sp500_chg"].notna().astype(int)

    if "sp500_chg" in features and "nasdaq_chg" in features:
        features["risk_appetite"] = (
            features["sp500_chg"].fillna(0) + features["nasdaq_chg"].fillna(0)
        ) / 2

    if "sp500_chg" in features and "vix_chg" in features:
        features["fear_greed_proxy"] = (
            features["sp500_chg"].fillna(0) - features["vix_chg"].fillna(0)
        )

    return features


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ticker-level features (sama seperti collect_idx_historical.py)."""
    if df.empty:
        return df

    df = df.sort_values(["ticker", "date"]).copy()

    def per_ticker(g):
        g = g.copy()
        c = g["close"]
        v = g["volume"]

        g["ret_1d"]  = c.pct_change(1) * 100
        g["ret_3d"]  = c.pct_change(3) * 100
        g["ret_5d"]  = c.pct_change(5) * 100
        g["ret_20d"] = c.pct_change(20) * 100

        g["vol_20d_avg"] = v.rolling(20).mean()
        g["vol_ratio"]   = v / g["vol_20d_avg"]

        g["volatility_20d"] = (c.pct_change() * 100).rolling(20).std()

        g["ma5"]  = c.rolling(5).mean()
        g["ma20"] = c.rolling(20).mean()
        g["above_ma5"]  = (c > g["ma5"]).astype(int)
        g["above_ma20"] = (c > g["ma20"]).astype(int)

        g["next_day_ret"] = c.pct_change(1).shift(-1) * 100
        g["label"]        = (g["next_day_ret"] > 3.0).astype(int)

        return g

    result = df.groupby("ticker", group_keys=False).apply(per_ticker)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"{'='*60}")
    print(f"  Quant Radar — Append Daily Data")
    print(f"{'='*60}\n")

    # Load existing data
    print("[1/4] Loading existing parquet...")
    idx = pd.read_parquet(IDX_FILE)
    us  = pd.read_parquet(US_FILE)

    idx_last = get_last_trading_date(idx, idx_file=True)
    us_last  = get_last_trading_date(us, idx_file=False)

    print(f"  IDX last: {idx_last.date()}")
    print(f"  US last : {us_last.date()}")

    # Determine target date (next trading day)
    # Start from yesterday, keep adding 1 day until we get valid data
    target_date = (pd.Timestamp.now() - pd.Timedelta(days=1)).date()
    max_retries = 10

    print(f"\n[2/4] Fetching daily data...")
    print(f"  Target: {target_date}")

    idx_daily = pd.DataFrame()
    us_daily = pd.DataFrame()

    for i in range(max_retries):
        check_date = target_date - pd.Timedelta(days=i)
        check_date_ts = pd.Timestamp(check_date)

        print(f"\n  Trying {check_date}...")

        # Skip weekend
        if check_date.weekday() >= 5:
            print(f"    Skip: Weekend")
            continue

        # Fetch IDX
        idx_daily = fetch_idx_daily(IDX_TICKERS_YF, check_date_ts)
        if idx_daily.empty:
            print(f"    IDX: No data (market closed?)")
            continue

        print(f"    IDX: {len(idx_daily)} rows, {idx_daily['ticker'].nunique()} tickers")

        # Fetch US
        us_daily = fetch_us_daily(check_date_ts)
        if us_daily.empty:
            print(f"    US: No data (market closed?)")
            continue

        print(f"    US: {len(us_daily)} rows")

        # Both succeeded
        target_date = check_date
        break

    if idx_daily.empty or us_daily.empty:
        print("\n[ERROR] Could not fetch any data!")
        return

    # Compute derived features for IDX
    print("\n[3/4] Computing derived features...")

    # Butuh data historis untuk compute rolling features
    # Gabung dengan data existing
    idx_combined = pd.concat([idx, idx_daily], ignore_index=True)
    idx_featured = add_derived_features(idx_combined)

    # Filter hanya baris baru
    idx_new = idx_featured[idx_featured["date"].dt.date == target_date]
    idx_new = idx_new.dropna(subset=["ret_5d", "volatility_20d"])

    print(f"  New IDX rows: {len(idx_new)}")

    # US features butuh data historis untuk compute pct_change
    us_combined = pd.concat([us, us_daily])
    us_new = us_combined[us_combined.index.date == target_date]

    # Drop rows dengan NaN (hari pertama tidak ada pct_change)
    us_new = us_new.dropna(how="all")

    print(f"  New US rows: {len(us_new)}")

    if idx_new.empty or us_new.empty:
        print("\n[WARN] No valid new data to append (rolling calc needs more history)")
        return

    # Save
    print("\n[4/4] Saving...")

    # Append ke parquet
    idx_to_save = pd.concat([idx, idx_new], ignore_index=True)
    idx_to_save.to_parquet(IDX_FILE, engine="pyarrow", compression="snappy", index=False)
    print(f"  [OK] {IDX_FILE}: {len(idx_to_save)} rows (+{len(idx_new)})")

    us_to_save = pd.concat([us, us_new])
    us_to_save.to_parquet(US_FILE, engine="pyarrow", compression="snappy")
    print(f"  [OK] {US_FILE}: {len(us_to_save)} rows (+{len(us_new)})")

    print(f"\n{'='*60}")
    print(f"  DONE — Data appended: {target_date}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
