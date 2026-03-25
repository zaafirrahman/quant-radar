import pandas as pd
from pathlib import Path
import pytz

# ══════════════════════════════════════════════════════════════
#  SHARED STYLE CONSTANTS
# ══════════════════════════════════════════════════════════════

_FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');"

_BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: "IBM Plex Mono", "Cascadia Code", monospace;
    background: #000000;
    color: #cccccc;
    padding: 36px;
}

h2 {
    font-size: 28px;
    letter-spacing: 5px;
    color: #ffffff;
    font-weight: bold;
    margin-bottom: 6px;
    text-transform: uppercase;
    text-align: left;
}

.subtitle {
    text-align: left;
    color: #555555;
    font-size: 13px;
    margin-bottom: 28px;
    letter-spacing: 1px;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: #0a0a0a;
    border: 1px solid #222222;
}

th {
    background: #111111;
    color: #ffffff;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 14px;
    border-bottom: 1px solid #333333;
    border-right: 1px solid #1a1a1a;
    font-weight: 400;
}

th:last-child { border-right: none; }

td {
    padding: 12px 14px;
    border-bottom: 1px solid #1a1a1a;
    border-right: 1px solid #141414;
    font-size: 15px;
}

td:last-child  { border-right: none; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #111111; }

tr.top5 td { background: #0d0d0d; }
tr.top5:hover td { background: #161616; }

.nav-btn {
    position: fixed;
    top: 24px;
    right: 28px;
    font-family: "IBM Plex Mono", monospace;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #000000;
    background: #ff8c00;
    border: none;
    padding: 10px 18px;
    cursor: pointer;
    text-decoration: none;
    z-index: 999;
    transition: background 0.15s ease;
}
.nav-btn:hover { background: #ffaa33; }
"""

def _wrap_html(title: str, body: str, favicon_depth: str = "../../../") -> str:
    style = f"<style>{_FONT_IMPORT}{_BASE_CSS}</style>"
    favicon_link = f'<link rel="icon" type="image/png" href="{favicon_depth}assets/logo.png">'
    return f"""<html><head>{favicon_link}<title>{title}</title>{style}</head><body>{body}</body></html>"""


# ══════════════════════════════════════════════════════════════
#  COLOUR HELPERS
# ══════════════════════════════════════════════════════════════

def _color_distance(val: float) -> str:
    if val > 50:   return "color:#00ff88;font-weight:bold;"
    if val > 0:    return "color:#7CFC00;"
    if val > -20:  return "color:#ffa500;"
    return "color:#ff4d4d;"

def _color_z(val: float) -> str:
    if val > 2:  return "color:#00ff88;"
    if val > 1:  return "color:#7CFC00;"
    if val > 0:  return "color:#ffa500;"
    return "color:#ff4d4d;"

def _color_return(val: float) -> str:
    if val > 0:  return "color:#00ff88;font-weight:bold;"
    return "color:#ff4d4d;font-weight:bold;"

def _color_winrate(val: float) -> str:
    if val >= 60: return "color:#00ff88;font-weight:bold;"
    if val >= 50: return "color:#7CFC00;"
    if val >= 40: return "color:#ffa500;"
    return "color:#ff4d4d;"

def _color_sharia(val: str) -> str:
    if val == "Halal":     return "color:#00ff88;font-weight:bold;"
    if val == "Doubtful":  return "color:#ffa500;font-weight:bold;"
    if val == "Not Halal": return "color:#ff4d4d;font-weight:bold;"
    return "color:#888888;"

def _color_edge(val: float) -> str:
    if val > 3:    return "color:#00ff88;font-weight:bold;"
    if val > 1.5:  return "color:#7CFC00;font-weight:bold;"
    if val > 0:    return "color:#ffa500;"
    return "color:#ff4d4d;"

def _color_characteristic(val: str) -> str:
    if "COMPOUNDER" in val: return "color:#00ff88;"
    if "BURST"      in val: return "color:#ffff00;"
    if "STEADY"     in val: return "color:#ffa500;"
    return "color:#ff4d4d;"  # ERRATIC

def _color_quality(val: float) -> str:
    if val >= 0.75: return "color:#00ff88;font-weight:bold;"
    if val >= 0.50: return "color:#7CFC00;"
    if val >= 0.25: return "color:#ffa500;"
    return "color:#ff4d4d;"

def _color_sniper(val: float) -> str:
    if val >= 75: return "color:#00ff88;font-weight:bold;"
    if val >= 60: return "color:#7CFC00;font-weight:bold;"
    if val >= 50: return "color:#ffa500;font-weight:bold;"
    return "color:#ff4d4d;"

def _quality_status(q: float) -> str:
    if q >= 0.75: return "💚 HIGH QUALITY"
    if q >= 0.50: return "🟡 GOOD QUALITY"
    if q >= 0.25: return "🟠 MED QUALITY"
    return "🔴 LOW QUALITY"

def _edge_status(e: float) -> str:
    if e > 3:   return "💚 HIGH EDGE"
    if e > 1.5: return "🟡 GOOD EDGE"
    if e > 0:   return "🟠 MED EDGE"
    return "🔴 NEGATIVE EDGE"

def _td(content, style="color:#ffffff;"):
    return f'<td style="{style}">{content}</td>'


# ══════════════════════════════════════════════════════════════
#  1. RADAR DASHBOARD  (Signal Surge Amplifier Grid)
# ══════════════════════════════════════════════════════════════

def build_radar_dashboard(df: pd.DataFrame, timestamp: str) -> str:
    col_names = [
        "Rank", "Ticker", "Last_Price", "Momentum_14d", "Vol_Surge",
        "Range_Pos_325", "Radar_Score", "Threshold", "Distance_%", "Z_Score"
    ]
    header = "".join(f"<th>{c}</th>" for c in col_names)
    rows = []
    for i, row in df.iterrows():
        cells = []
        for j, col in enumerate(df.columns):
            val = row[col]
            if   j == 0: style = "color:#aaaaaa;"
            elif j == 1: style = "color:#ff8c00;font-weight:bold;"
            elif j in [2, 3, 4, 5]: style = "color:#ffffff;"
            elif j == 6: style = "color:#00cc66;font-weight:bold;"
            elif j == 7: style = "color:#ff8c00;"
            elif j == 8: style = _color_distance(float(val))
            elif j == 9: style = _color_z(float(val))
            else:        style = "color:#ffffff;"
            cells.append(f'<td style="{style}">{val}</td>')
        cls = "top5" if i < 5 else ""
        rows.append(f'<tr class="{cls}">{"".join(cells)}</tr>')
    table = f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    body = f"""
        <a href="../../us_hub.html" class="nav-btn" style="top:70px;">◀| Back to Hub</a>
        <a href="../sniper/index.html" class="nav-btn">Go to Sniper ▶</a>
        <h2>Signal Surge Amplifier Grid</h2>
        <p class="subtitle" style="margin-bottom:10px;color:#999999;">Generated {timestamp} EDT</p>
        <p class="subtitle" style="color:#ff8c00;">
            Ranked based on radar - threshold distance percentage
        </p>
        {table}
    """
    return _wrap_html("Radar - Signal Surge Amplifier Grid", body)


# ══════════════════════════════════════════════════════════════
#  2. BULK SNIPER DASHBOARD  (Runner Performance Protocol)
# ══════════════════════════════════════════════════════════════

def build_bulk_dashboard(summary_df: pd.DataFrame, timestamp: str) -> str:
    col_names = [
        "Rank", "Ticker", "WR_5", "WR_10", "WR_20",
        "AVG_5", "AVG_10", "AVG_20",
        "Sample", "Edge_Score", "Characteristic",
        "Sample_Score", "Cluster_Score", "Stability_Score", "Quality_Score",
        "Sniper_Score", "Sharia"
    ]
    header = "".join(f"<th>{c}</th>" for c in col_names)
    rows   = []
    for i, row in summary_df.iterrows():
        cells = [
            _td(row["Rank"],   "color:#aaaaaa;"),
            _td(f'<a href="html/{row["Ticker"]}.html" style="color:#ff8c00;text-decoration:none;font-weight:bold;">{row["Ticker"]}</a>'),
            _td(row["WR_5"],   _color_winrate(float(row["WR_5"]))),
            _td(row["WR_10"],  _color_winrate(float(row["WR_10"]))),
            _td(row["WR_20"],  _color_winrate(float(row["WR_20"]))),
            _td(row["AVG_5"],  _color_return(float(row["AVG_5"]))),
            _td(row["AVG_10"], _color_return(float(row["AVG_10"]))),
            _td(row["AVG_20"], _color_return(float(row["AVG_20"]))),
            _td(row["Sample"], "color:#ffffff;"),
            _td(row["Edge_Score"],      _color_edge(float(row["Edge_Score"]))),
            _td(row["Characteristic"],  _color_characteristic(str(row["Characteristic"]))),
            _td(row["Sample_Score"],    _color_quality(float(row["Sample_Score"]))),
            _td(row["Cluster_Score"],   _color_quality(float(row["Cluster_Score"]))),
            _td(row["Stability_Score"], _color_quality(float(row["Stability_Score"]))),
            _td(row["Quality_Score"],   _color_quality(float(row["Quality_Score"]))),
            _td(row["Sniper_Score"],    _color_sniper(float(row["Sniper_Score"]))),
            _td(row["Sharia"],          _color_sharia(str(row["Sharia"]))),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    table = f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    body = f"""
        <a href="../../us_hub.html" class="nav-btn" style="top:70px;">◀| Back to Hub</a>
        <a href="../radar/us_radar.html" class="nav-btn">◀ Back to Radar</a>
        <h2>Runner Performance Protocol</h2>
        <p class="subtitle" style="margin-bottom:10px;color:#999999;">Generated {timestamp} EDT</p>
        <p class="subtitle" style="color:#ff8c00;font-weight:bold">
            Click ticker ↓ to see full sniper details
        </p>
        {table}
    """
    return _wrap_html("Sniper - Runner Performance Protocol", body)


# ══════════════════════════════════════════════════════════════
#  3. SINGLE SNIPER DASHBOARD  (per ticker)
# ══════════════════════════════════════════════════════════════

_SINGLE_EXTRA_CSS = """
.status-container {
    display: flex;
    gap: 20px;
    margin-bottom: 36px;
}
.status-box {
    flex: 1;
    background: #0d0d0d;
    border: 1px solid #222;
    border-top: 3px solid #ff8c00;
    padding: 24px;
    line-height: 2;
    font-size: 15px;
}
.verdict-box {
    flex: 1;
    background: #0d0d0d;
    border: 1px solid #ff8c00;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 8px;
}
.score-value {
    font-size: 52px;
    font-weight: 600;
    color: #ff8c00;
    line-height: 1;
}
.verdict-text {
    font-size: 15px;
    color: #ffffff;
    letter-spacing: 1px;
}
.score-label {
    font-size: 11px;
    letter-spacing: 3px;
    color: #555;
    text-transform: uppercase;
}
.char-tag {
    font-size: 12px;
    letter-spacing: 1.5px;
    color: #888888;
    margin-top: 4px;
}
.section-title {
    font-size: 13px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #ff8c00;
    border-left: 3px solid #ff8c00;
    padding-left: 12px;
    margin: 36px 0 14px;
}
.blinking {
    color: #ff8c00;
    font-size: 18px;
    font-weight: bold;
    animation: blink 1.5s infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}
.footer {
    color: #555555;
    font-size: 13px;
    text-align: center;
    margin-top: 60px;
    letter-spacing: 1px;
}
/* ── TWO-PANEL SECTION ── */
.two-panel {
    display: flex;
    gap: 16px;
    align-items: stretch;
    margin-bottom: 0;
}
.two-panel-table { flex: 2; min-width: 0; }
.two-panel-table table { width: 100%; table-layout: fixed; }
.two-panel-table.reliability th:nth-child(1),
.two-panel-table.reliability td:nth-child(1) { width: 50%; }
.two-panel-table.reliability th:nth-child(2),
.two-panel-table.reliability td:nth-child(2) { width: 50%; }
.two-panel-table.profitability th:nth-child(1),
.two-panel-table.profitability td:nth-child(1) { width: 33.3%; }
.two-panel-table.profitability th:nth-child(2),
.two-panel-table.profitability td:nth-child(2) { width: 33.3%; }
.two-panel-table.profitability th:nth-child(3),
.two-panel-table.profitability td:nth-child(3) { width: 33.3%; }
.two-panel-table th,
.two-panel-table td {
    padding: 12px 14px !important;
    font-size: 14px !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.side-box {
    flex: 1;
    background: #0d0d0d;
    border: 1px solid #ff8c00;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 6px;
}
.side-box-label {
    font-size: 10px;
    letter-spacing: 2.5px;
    color: #555555;
    text-transform: uppercase;
}
.side-box-value {
    font-size: 38px;
    font-weight: 600;
    line-height: 1.1;
}
.side-box-status {
    font-size: 11px;
    letter-spacing: 1px;
    margin-top: 4px;
}
.header-container {
    display: flex;
    align-items: flex-start;
    gap: 20px;
    margin-bottom: 20px;
}
.company-logo {
    width: 70px;
    height: 70px;
    background-color: transparent;
    border: none;
    border-radius: 12px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.company-logo img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}
.info-text {
    display: flex;
    flex-direction: column;
}
"""

SECTOR_EMOJI = {
    "Technology": "💻",
    "Consumer Cyclical": "🛍️",
    "Healthcare": "💊",
    "Financial Services": "💰",
    "Industrials": "⚙️",
    "Communication Services": "📡",
    "Consumer Defensive": "🛒",
    "Basic Materials": "⛏️",
    "Energy": "🛢️",
    "Real Estate": "🏠",
    "Utilities": "💡",
    "Exchange Traded Fund": "📦",
}

def get_ticker_info(ticker: str):
    base_path = Path(__file__).resolve().parent
    csv_path  = (base_path / "../config/ticker_universe.csv").resolve()
    df        = pd.read_csv(csv_path)
    row       = df[df["ticker"] == ticker]
    if row.empty:
        return "Unknown", "❓"
    sektor   = row.iloc[0]["sektor"]
    industry = row.iloc[0]["industry"]
    emoji    = SECTOR_EMOJI.get(sektor, "❓")
    return industry, emoji


def _build_signal_table(df: pd.DataFrame) -> str:
    cols = ["Date", "Signal_Score", "Entry", "Return_5d (%)", "Return_10d (%)", "Return_20d (%)", "W/L"]
    if df.index.name == "Rank":
        df   = df.reset_index()
        cols = ["Rank"] + cols
    header = "".join(f"<th>{c}</th>" for c in cols)
    rows   = []
    for _, row in df.iterrows():
        cells = []
        for col in cols:
            val = row[col]
            if   col == "Rank":   style = "color:#aaaaaa;"
            elif col == "Date":   style = "color:#888888;"
            elif col == "Signal_Score": style = "color:#ff8c00;font-weight:bold;"
            elif col == "Entry":  style = "color:#ffffff;"
            elif col in ["Return_5d (%)", "Return_10d (%)", "Return_20d (%)"]:
                style = _color_return(float(val))
            elif col == "W/L":
                style = "color:#00ff88;" if "WIN" in str(val) else "color:#ff4d4d;"
            else: style = "color:#ffffff;"
            cells.append(f'<td style="{style}">{val}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _build_stats_table(stats_df: pd.DataFrame) -> str:
    header = "<th></th><th>Avg Return (%)</th><th>Win Rate (%)</th>"
    rows   = []
    for idx, row in stats_df.iterrows():
        ar = float(row["Avg Return (%)"])
        wr = float(row["Win Rate (%)"])
        cells = [
            f'<td style="color:#555555;">{idx}</td>',
            f'<td style="{_color_return(ar)}">{ar:.2f}</td>',
            f'<td style="{_color_winrate(wr)}">{wr:.2f}</td>',
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_single_dashboard(result: dict) -> str:
    meta    = result["meta"]
    ticker  = meta["ticker"]
    company = meta["company"]
    price   = meta["current_price"]
    score   = meta["current_score"]
    thr     = meta["threshold"]
    edge    = meta["edge_score"]
    char    = meta["characteristic"]
    sniper  = meta["sniper_score"]
    verdict = meta["verdict"]
    sharia  = meta["sharia"]

    status_label  = "✅ RADAR CONFIRMED" if score > thr else "😴 Waiting for Momentum"
    status_cls    = "blinking" if score > thr else ""
    sniper_color  = _color_sniper(sniper).replace("font-weight:bold;", "")
    q             = meta["quality_score"]
    e             = meta["edge_score"]
    quality_color = _color_quality(q).replace("font-weight:bold;", "")
    edge_color    = _color_edge(e).replace("font-weight:bold;", "")
    n             = result["summary"]["Sample"]

    yahoo_url = f"https://finance.yahoo.com/quote/{ticker}/"
    style     = f"<style>{_FONT_IMPORT}{_BASE_CSS}{_SINGLE_EXTRA_CSS}</style>"

    stats_table  = _build_stats_table(result["stats"])
    recent_table = _build_signal_table(result["recent"].copy())
    power_table  = _build_signal_table(result["power_ranking"].reset_index())
    industry, emoji = get_ticker_info(ticker)

    logo_path = f"../../../config/logos/{ticker}.svg"
    logo_html = f'''
        <div class="company-logo">
            <img src="{logo_path}" alt="{ticker}" onerror="this.src='https://via.placeholder.com/80?text={ticker}';">
        </div>
    '''

    def _rtd(label, val, color):
        return f'<tr><td style="color:#555555;padding:12px 14px;">{label}</td><td style="{color}padding:12px 14px;font-size:15px;">{val}</td></tr>'

    reliability_rows = "".join([
        _rtd("Sample Signals",  n,                             "color:#ffffff;"),
        _rtd("Sample Quality",  meta["sample_score"],          _color_quality(meta["sample_score"])),
        _rtd("Cluster Spread",  meta["cluster_score"],         _color_quality(meta["cluster_score"])),
        _rtd("Stability",       meta["stability_score"],       _color_quality(meta["stability_score"])),
    ])
    reliability_table = f'''<table style="background:#0a0a0a;border:1px solid #222;">
        <thead><tr>
            <th style="background:#111;color:#fff;font-size:12px;letter-spacing:1.5px;padding:14px;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;font-weight:400;">METRIC</th>
            <th style="background:#111;color:#fff;font-size:12px;letter-spacing:1.5px;padding:14px;border-bottom:1px solid #333;font-weight:400;">VALUE</th>
        </tr></thead>
        <tbody>{reliability_rows}</tbody>
    </table>'''

    body = f"""
        <a href="../index.html" class="nav-btn">◀ Back to Sniper</a>

        <div class="header-container">
            {logo_html}
            <div class="info-text">
                <h2 style="text-align:left;letter-spacing:2px;font-size:24px;margin:0;line-height:1.2;">
                    <strong>
                        {company}
                        <a href="{yahoo_url}" target="_blank"
                           style="color:#ff8c00;text-decoration:none;">({ticker})</a>
                    </strong>
                </h2>
                <p class="subtitle" style="text-align:left;margin:4px 0;font-size:15px;">
                    {emoji} <span style="color:#ff8c00;">{industry}</span>
                </p>
                <p class="subtitle" style="text-align:left;margin:0;font-size:15px;">
                    Sharia: <span style="{_color_sharia(sharia)}">{sharia}</span>
                </p>
            </div>
        </div>

        <div class="status-container">
            <div class="status-box">
                <p>💵 Last Price: <b style="color:#ffffff;">{price:.2f}</b></p>
                <p>🎯 Radar Score: <b style="font-size:22px;color:#ff8c00;">{score:.2f}</b></p>
                <p>🛡️ Threshold (95%): <span style="color:#aaaaaa;">{thr:.2f}</span></p>
                <p>⚡ Status: <span class="{status_cls}">{status_label}</span></p>
            </div>
            <div class="verdict-box">
                <span class="score-label">Sniper Score</span>
                <div class="score-value" style="{sniper_color}">{sniper}</div>
                <div class="verdict-text">{verdict}</div>
                <div class="char-tag">Type: <span style="{_color_characteristic(char)}">{char}</span></div>
            </div>
        </div>

        <div class="section-title">🔬 Robustness and Consistency (Reliability)</div>
        <div class="two-panel">
            <div class="two-panel-table reliability">{reliability_table}</div>
            <div class="side-box" style="border-color:{quality_color.split(':')[1].split(';')[0] if 'color:' in quality_color else '#ff8c00'};">
                <span class="side-box-label">Quality Score</span>
                <div class="side-box-value" style="{quality_color}">{q}</div>
                <div class="side-box-status" style="{quality_color}">{_quality_status(q)}</div>
            </div>
        </div>

        <div class="section-title">📊 Average Strategy Performance (Profitability)</div>
        <div class="two-panel">
            <div class="two-panel-table profitability">{stats_table}</div>
            <div class="side-box" style="border-color:{edge_color.split(':')[1].split(';')[0] if 'color:' in edge_color else '#ff8c00'};">
                <span class="side-box-label">Edge Score</span>
                <div class="side-box-value" style="{edge_color}">{e}</div>
                <div class="side-box-status" style="{edge_color}">{_edge_status(e)}</div>
            </div>
        </div>

        <div class="section-title">📅 10 Recent Signals — Regime Check</div>
        {recent_table}

        <div class="section-title">🏆 The Complete Power Ranking</div>
        {power_table}

        <p class="footer">Generated {pd.Timestamp.now(pytz.timezone("US/Eastern")).strftime('%Y-%m-%d %H:%M:%S')} EDT</p>
    """

    favicon_link = '<link rel="icon" type="image/png" href="../../../../assets/logo.png">'
    return f"<html><head>{favicon_link}<title>Sniper - {ticker}</title>{style}</head><body>{body}</body></html>"


# ══════════════════════════════════════════════════════════════
#  4. TRACKING INDEX  (month selector)
# ══════════════════════════════════════════════════════════════

def build_tracking_index(available_months: list[str]) -> str:
    def _month_label(m: str) -> str:
        dt = pd.to_datetime(m + "-01")
        return dt.strftime("%B %Y").upper()

    buttons = ""
    for m in available_months:
        label   = _month_label(m)
        buttons += f'\n        <a href="{m}.html" class="month-btn">{label} ▶</a>'

    extra_css = """
    <style>
    .month-btn {
        display: block;
        width: 100%;
        max-width: 400px;
        margin: 0 auto 12px;
        padding: 18px 24px;
        font-family: "IBM Plex Mono", monospace;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        text-decoration: none;
        color: #000000;
        background: #ff8c00;
        text-align: left;
        transition: background 0.15s;
    }
    .month-btn:hover { background: #ffaa33; }
    .back-btn {
        position: fixed;
        top: 24px;
        right: 28px;
        font-family: "IBM Plex Mono", monospace;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #000000;
        background: #ff8c00;
        padding: 10px 18px;
        text-decoration: none;
        z-index: 999;
    }
    .back-btn:hover { background: #ffaa33; }
    </style>"""

    body = f"""
        {extra_css}
        <a href="../../../us_hub.html" class="back-btn">◀ Back to Hub</a>
        <div style="padding-top:80px;">
            <p style="text-align:center;font-size:11px;letter-spacing:3px;color:#444;text-transform:uppercase;margin-bottom:12px;">
                US Market / Tracker Matrix
            </p>
            <h2 style="text-align:center;letter-spacing:5px;margin-bottom:8px;">TRACKER MATRIX</h2>
            <p class="subtitle" style="text-align:center;margin-bottom:40px;">
                Post-Mortem Interval Array — Select a month to view
            </p>
            {buttons if buttons else '<p style="text-align:center;color:#444;">No data yet.</p>'}
        </div>
    """
    favicon = '<link rel="icon" type="image/png" href="../../../../assets/logo.png">'
    style   = f"<style>{_FONT_IMPORT}{_BASE_CSS}</style>"
    return f"<html><head>{favicon}<title>Tracker Matrix</title>{style}</head><body>{body}</body></html>"


# ══════════════════════════════════════════════════════════════
#  5. TRACKING MONTH DASHBOARD  (multihead heatmap table)
# ══════════════════════════════════════════════════════════════

def build_tracking_month(df: pd.DataFrame, month_key: str) -> str:
    if df.empty:
        body    = "<p style='color:#444;text-align:center;margin-top:100px;'>No data for this month.</p>"
        favicon = '<link rel="icon" type="image/png" href="../../../../assets/logo.png">'
        style   = f"<style>{_FONT_IMPORT}{_BASE_CSS}</style>"
        return f"<html><head>{favicon}<title>Tracker {month_key}</title>{style}</head><body>{body}</body></html>"

    month_label = pd.to_datetime(month_key + "-01").strftime("%B %Y").upper()

    dates   = sorted(df["Date"].unique(), reverse=True)
    tickers = sorted(df["Ticker"].unique())
    idx     = df.set_index(["Date", "Ticker"])

    # ── Heatmap helpers ───────────────────────────────────────────────────────
    max_dist = df["Distance_%"].abs().max() if not df.empty else 1

    def _radar_bg(dist: float) -> str:
        if dist is None:
            return "#0a0a0a"
        if dist > 0:
            # Green: intensity based on distance
            ratio = min(dist / max(max_dist, 1), 1.0)
            g = int(ratio * 255)
            b = int(ratio * 136)
            return f"rgb(0,{g},{b})"
        elif dist < 0:
            # Red: intensity based on how negative
            ratio = min(abs(dist) / max(max_dist, 1), 1.0)
            r = int(80 + ratio * 175)  # #500000 → #ff0000
            return f"rgb({r},0,0)"
        else:
            return "#0a0a0a"

    def _sniper_bg(score: float) -> str:
        if score is None: return "#0a0a0a"
        ratio = min(score / 100, 1.0)
        if ratio >= 0.75:   return f"rgba(0,255,136,{0.15 + ratio*0.25:.2f})"
        elif ratio >= 0.60: return f"rgba(124,252,0,{0.1 + ratio*0.2:.2f})"
        elif ratio >= 0.50: return f"rgba(255,165,0,{0.1 + ratio*0.15:.2f})"
        else:               return f"rgba(255,77,77,{0.05 + ratio*0.1:.2f})"

    def _price_style(change) -> str:
        if change is None: return "color:#555555;"
        return "color:#00ff88;font-weight:bold;" if change >= 0 else "color:#ff4d4d;font-weight:bold;"

    def _price_arrow(change) -> str:
        if change is None: return "—"
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {abs(change):.2f}%"

    # ── Build table ───────────────────────────────────────────────────────────
    th_tickers = '<th style="background:#0a0a0a;border:none;position:sticky;left:0;z-index:3;"></th>'
    for t in tickers:
        yf_url = f"https://finance.yahoo.com/quote/{t}/"
        th_tickers += f'<th colspan="3" class="ticker-head" style="background:#111;color:#ff8c00;font-size:12px;letter-spacing:2px;text-align:center;padding:12px;border-bottom:1px solid #333;border-right:1px solid #333;position:sticky;top:0;z-index:2;"><a href="{yf_url}" target="_blank" style="color:#ff8c00;text-decoration:none;">{t}</a></th>'

    th_sub = '<th style="background:#111;color:#555;font-size:10px;letter-spacing:1px;padding:10px 8px;border-bottom:1px solid #222;position:sticky;top:37px;left:0;z-index:3;">DATE</th>'
    for _ in tickers:
        th_sub += '<th style="background:#111;color:#666;font-size:10px;letter-spacing:1px;padding:10px 8px;border-bottom:1px solid #222;text-align:center;position:sticky;top:37px;z-index:2;">RADAR</th>'
        th_sub += '<th style="background:#111;color:#666;font-size:10px;letter-spacing:1px;padding:10px 8px;border-bottom:1px solid #222;text-align:center;position:sticky;top:37px;z-index:2;">PRICE</th>'
        th_sub += '<th style="background:#111;color:#666;font-size:10px;letter-spacing:1px;padding:10px 8px;border-bottom:1px solid #222;border-right:1px solid #222;text-align:center;position:sticky;top:37px;z-index:2;">SNIPER</th>'

    data_rows = ""
    for dt in dates:
        row_html = f'<td style="color:#555555;font-size:12px;padding:10px 12px;white-space:nowrap;position:sticky;left:0;background:#0a0a0a;z-index:1;">{dt}</td>'
        for t in tickers:
            try:
                r      = idx.loc[(dt, t)]
                dist   = float(r["Distance_%"]) if r["Distance_%"] is not None and str(r["Distance_%"]) != "nan" else None
                change = float(r["Price_Change"]) if r["Price_Change"] is not None and str(r["Price_Change"]) != "nan" else None
                sniper = float(r["Sniper_Score"]) if r["Sniper_Score"] is not None and str(r["Sniper_Score"]) != "nan" else None

                radar_bg      = _radar_bg(dist)
                sniper_bg     = _sniper_bg(sniper) if sniper is not None else "#0a0a0a"
                sniper_display = f"{sniper:.1f}" if sniper is not None else "—"
                dist_display  = f"{dist:.1f}%" if dist is not None else "—"

                row_html += f'<td style="background:{radar_bg};color:#ffffff;font-size:12px;padding:10px 8px;text-align:center;">{dist_display}</td>'
                price_val     = float(r["Price"]) if r["Price"] is not None and str(r["Price"]) != "nan" else None
                price_display = f"{price_val:.2f}" if price_val is not None else "—"
                row_html += f'<td style="font-size:12px;padding:10px 8px;text-align:center;{_price_style(change)}">{price_display}</td>'
                row_html += f'<td style="background:{sniper_bg};color:#ffffff;font-size:12px;padding:10px 8px;text-align:center;border-right:1px solid #1a1a1a;">{sniper_display}</td>'
            except KeyError:
                row_html += '<td style="background:#0a0a0a;color:#222;font-size:11px;padding:10px 8px;text-align:center;">—</td>'
                row_html += '<td style="background:#0a0a0a;color:#222;font-size:11px;padding:10px 8px;text-align:center;">—</td>'
                row_html += '<td style="background:#0a0a0a;color:#222;font-size:11px;padding:10px 8px;text-align:center;border-right:1px solid #1a1a1a;">—</td>'

        data_rows += f"<tr>{row_html}</tr>"

    extra_css = """
    <style>
    .tracking-table {
        width: 100%;
        border-collapse: collapse;
        background: #0a0a0a;
        border: 1px solid #222;
    }
    .tracking-wrap {
        overflow-x: auto;
        overflow-y: auto;
        max-height: calc(100vh - 180px);
        position: relative;
    }
    #tkSearch:focus { outline: none; border-color: #ffaa33; }
    </style>"""

    search_js = """
    <script>
    function doSearch() {
        var q = document.getElementById('tkSearch').value.trim().toUpperCase();
        // Remove previous highlights
        document.querySelectorAll('th.ticker-hl').forEach(el => {
            el.style.outline = '';
            el.classList.remove('ticker-hl');
        });
        if (!q) return;
        var headers = document.querySelectorAll('th.ticker-head');
        var found = null;
        headers.forEach(function(th) {
            if (th.textContent.trim().toUpperCase() === q) {
                th.style.outline = '2px solid #ff8c00';
                th.classList.add('ticker-hl');
                if (!found) found = th;
            }
        });
        if (found) found.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
    document.addEventListener('DOMContentLoaded', function() {
        var inp = document.getElementById('tkSearch');
        inp.addEventListener('input', doSearch);
        inp.addEventListener('keydown', function(e) { if (e.key === 'Escape') { inp.value = ''; doSearch(); } });
    });
    </script>
    """

    body = f"""
        {extra_css}
        {search_js}
        <a href="index.html" class="nav-btn">◀ Back</a>
        <div style="position:fixed;top:64px;right:28px;z-index:998;">
            <input id="tkSearch" type="text" placeholder="Search ticker..."
                style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                       letter-spacing:1px;background:#111;color:#ffffff;
                       border:1px solid #ff8c00;padding:8px 14px;width:180px;
                       outline:none;">
        </div>
        <h2 style="margin-bottom:4px;">{month_label}</h2>
        <p class="subtitle" style="text-align:left;margin-bottom:20px;color:#555555;">
            Tracker Matrix — Post-Mortem Interval Array
        </p>
        <div class="tracking-wrap">
            <table class="tracking-table">
                <thead>
                    <tr>{th_tickers}</tr>
                    <tr>{th_sub}</tr>
                </thead>
                <tbody>{data_rows}</tbody>
            </table>
        </div>
        <p class="footer" style="margin-top:40px;">
            Radar = Distance % above threshold &nbsp;|&nbsp;
            Price = Close (color = daily change) &nbsp;|&nbsp;
            Sniper = 0–100 combined score
        </p>
    """

    favicon = '<link rel="icon" type="image/png" href="../../../../assets/logo.png">'
    style   = f"<style>{_FONT_IMPORT}{_BASE_CSS}</style>"
    return f"<html><head>{favicon}<title>Tracker {month_key}</title>{style}</head><body>{body}</body></html>"