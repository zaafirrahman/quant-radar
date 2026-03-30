import json
import math
import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz

_CHARACTERISTIC_TIER = {
    "COMPOUNDER": "COMPDR",
    "BURST":      "BURST",
    "STEADY":     "STEADY",
    "ERRATIC":    "ERATIC",
}
_SHARIA_MAP = {
    "Halal": "Halal",
    "Not Halal": "NoHalal",
    "Doubtful": "Doubt",
    "Not Covered": "Uncover",
}

def _tier_from_characteristic(val: str) -> str:
    val_upper = str(val).upper()
    for key, tier in _CHARACTERISTIC_TIER.items():
        if key in val_upper:
            return tier
    return "ERRATIC"

def _sharia_compliance(val: str) -> str:
    if not val:  # handle None / "" / missing
        return "-"
    return _SHARIA_MAP.get(val, "-")

def _safe_float(val, fallback: float = 0.0) -> float:
    """Convert to float safely; returns fallback for NaN/Inf/empty."""
    try:
        result = float(val)
        if math.isnan(result) or math.isinf(result):
            return fallback
        return result
    except (ValueError, TypeError):
        return fallback

def _safe_str(val: object, fallback: str = "") -> str:
    """Convert to string, strip None."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return fallback
    return str(val)

def _js_str(val: str) -> str:
    """Escape a Python string for safe embedding inside a JS double-quoted string."""
    return (
        val
        .replace("\\", "\\\\")
        .replace('"',  '\\"')
        .replace("'",  "\\'")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def build_stocks_data(summary_df: pd.DataFrame) -> list[dict]:
    """Build the STOCKS list from DataFrame — pure data, no HTML."""
    df = summary_df.sort_values("Sniper_Score", ascending=False).reset_index(drop=True)
    stocks = []

    for _, row in df.iterrows():
        ticker  = _safe_str(row["Ticker"], "UNKNOWN")
        company = _safe_str(row.get("Company", ticker))
        score   = _safe_float(row["Sniper_Score"])
        sample  = int(_safe_float(row["Sample"]))
        char    = _safe_str(row.get("Characteristic", ""))
        halal  = _safe_str(row.get("Sharia", "\u2014"), "\u2014")
        sharia   = _sharia_compliance(halal)
        tier    = _tier_from_characteristic(char)

        wr5  = _safe_float(row["WR_5"])  / 100
        wr10 = _safe_float(row["WR_10"]) / 100
        wr20 = _safe_float(row["WR_20"]) / 100

        aw5  = _safe_float(row["AvgWin_5"])
        aw10 = _safe_float(row["AvgWin_10"])
        aw20 = _safe_float(row["AvgWin_20"])
        al5  = _safe_float(row["AvgLoss_5"])
        al10 = _safe_float(row["AvgLoss_10"])
        al20 = _safe_float(row["AvgLoss_20"])

        avg5  = _safe_float(row["AVG_5"])
        avg10 = _safe_float(row["AVG_10"])
        avg20 = _safe_float(row["AVG_20"])

        ev5  = round(wr5  * aw5  + (1 - wr5)  * al5,  2)
        ev10 = round(wr10 * aw10 + (1 - wr10) * al10, 2)
        ev20 = round(wr20 * aw20 + (1 - wr20) * al20, 2)

        stocks.append({
            "id":      ticker,
            "ticker":  ticker,
            "company": company,
            "score":   round(score, 2),
            "sample":  sample,
            "tier":    tier,
            "char":    char,
            "sharia":  sharia,
            "tf":      "20D",
            "ev":  {"5D": ev5,  "10D": ev10,  "20D": ev20},
            "avg": {"5D": avg5, "10D": avg10, "20D": avg20},
            "wr":  {"5D": round(wr5  * 100, 2), "10D": round(wr10 * 100, 2), "20D": round(wr20 * 100, 2)},
            "aw":  {"5D": aw5,  "10D": aw10,  "20D": aw20},
            "al":  {"5D": al5,  "10D": al10,  "20D": al20},
            "selected": False,
            "alloc": 0,
        })

    return stocks


def build_porto_dashboard(summary_df: pd.DataFrame, timestamp: str) -> str:
    """
    Build the porto HTML page.
    CSS and JS are loaded from external files — Python only injects:
      1. The timestamp
      2. The STOCKS data array (one <script> block)
    """
    stocks = build_stocks_data(summary_df)

    # Use json.dumps for safe, valid JS — no manual escaping needed
    stocks_js = json.dumps(stocks, ensure_ascii=False)

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Portfolio Strategy Builder</title>\n'
        '<link rel="icon" type="image/png" href="../../../assets/logo.png">\n'
        '<link rel="stylesheet" href="porto_builder.css">\n'
        '</head>\n'
        '<body>\n'

        # NAV — stacked group 
        '<div class="nav-group">\n'
        '<a href="../sniper/index.html" class="nav-btn nav-sniper">&#9664; Sniper</a>\n'
        '<a href="../../us_hub.html" class="nav-btn">&#9664; Hub</a>\n'
        '</div>\n'

        # HEADER
        '<div class="header">\n'
        '<h1>Portfolio<br>Strategy Builder</h1>\n'
        '<p class="ts">Generated: ' + timestamp + '</p>\n'
        '<p class="ts" style="color:#ff8c00">Todays runner ranked by sniper score</p>\n'
        '</div>\n'

        # ACTION BAR
        '<div class="action-bar">\n'
        '<span class="action-hint">&#8595; Click checkbox to select stocks</span>\n'
        '<button class="how-btn" onclick="openHow()">[?] Info</button>\n'
        '</div>\n'

        # CARD GRID (populated by JS)
        '<div class="card-grid" id="cardGrid"></div>\n'

        # HOW TO USE OVERLAY
        '<div class="overlay" id="howOverlay">\n'
        '<div class="overlay-box">\n'
        '<button class="overlay-close" onclick="closeHow()">&#10005; Close</button>\n'
        '<div class="overlay-title">How to Use</div>\n'
        '<div class="how-item"><span class="how-icon">&#9635;</span>'
        '<span><b style="color:#fff">Checkbox (orange/green block, left)</b> \u2014 Click to select or deselect a stock. '
        'Allocation % recalculates automatically across all selected stocks in real-time.</span></div>\n'
        '<div class="how-item"><span class="how-icon">&#11041;</span>'
        '<span><b style="color:#fff">Ticker Name</b> \u2014 Click to open the full Sniper Detail dashboard '
        'for that ticker: backtest history, signal table, edge &amp; quality breakdown.</span></div>\n'
        '<div class="how-item"><span class="how-icon">&#9636;</span>'
        '<span><b style="color:#fff">TF Dropdown</b> \u2014 Switch time-frame per card individually (5D / 10D / 20D). '
        'EV updates immediately on the card and in the footer basket.</span></div>\n'
        '<div class="how-item"><span class="how-icon">&#9641;</span>'
        '<span><b style="color:#fff">EV / Alloc box (right block)</b> \u2014 Click to open the Stress Test popup. '
        'Shows Win Rate, Loss Rate, Avg Win, Avg Loss, EV and Avg Return for each time-frame.</span></div>\n'
        '<div class="how-item"><span class="how-icon">&#9644;</span>'
        '<span><b style="color:#fff">Sticky Footer</b> \u2014 Displays Average EV of your basket, '
        'count of selected stocks, and a scrollable chip list showing each ticker with its '
        'score-weighted allocation %. All values update live.</span></div>\n'
        '</div></div>\n'

        # STRESS TEST OVERLAY
        '<div class="stress-overlay" id="stressOverlay">\n'
        '<div class="stress-box">\n'
        '<button class="stress-close" onclick="closeStress()">&#10005; Close</button>\n'
        '<div class="stress-title">Stress Test</div>\n'
        '<div class="stress-ticker-name" id="stressTicker">\u2014</div>\n'
        '<div class="stress-tf-tabs" id="stressTabs"></div>\n'
        '<div class="stress-grid" id="stressGrid"></div>\n'
        '<div class="stress-formula">'
        'EV : <span>(WR% &times; AvgWin) + (LR% &times; AvgLoss)</span><br>'
        'Where <span>LR% = 1 &minus; WR%</span> &nbsp;|&nbsp; <span>AvgLoss</span> is typically negative<br>'
        'Allocation : <span>Score / Total Score</span>'
        '</div>\n'
        '</div></div>\n'

        # STICKY FOOTER — row 1: avg ev + selected count | row 2: chip list
        '<div class="sticky-footer">\n'
        '<div class="footer-top">\n'
        '<div class="footer-ev">AVG EV:&nbsp;<span class="ev-val" id="footerEv" style="color:var(--dim)">\u2014</span></div>\n'
        '<div class="footer-count">Selected:<span class="cnt-val" id="footerCount">0</span></div>\n'
        '</div>\n'
        '<div class="footer-chips" id="footerChips"><span class="footer-empty">No stocks selected</span></div>\n'
        '</div>\n'

        # DATA INJECTION — only this <script> block is generated by Python
        '<script>const STOCKS = ' + stocks_js + ';</script>\n'

        # LOGIC — loaded from static external file
        '<script src="porto_builder.js"></script>\n'

        '</body></html>\n'
    )

    return html


# ── CLI runner ──────────────────────────────────────────────
if __name__ == "__main__":
    edt       = pytz.timezone("US/Eastern")
    timestamp = datetime.now(edt).strftime("%d-%m-%Y %H:%M")

    csv_path  = Path(__file__).resolve().parent / "sniper_summary.csv"
    df        = pd.read_csv(csv_path)
    html      = build_porto_dashboard(df, timestamp)

    out_path  = Path(__file__).resolve().parent / "porto_builder.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ porto_builder.html saved → {out_path}")