import pandas as pd

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
    font-weight: 400;
    margin-bottom: 6px;
    text-transform: uppercase;
    text-align: center;
}

.subtitle {
    text-align: center;
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


def _wrap_html(title: str, body: str) -> str:
    style = f"<style>{_FONT_IMPORT}{_BASE_CSS}</style>"
    return f"<html><head><title>{title}</title>{style}</head><body>{body}</body></html>"


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

def _td(content, style="color:#ffffff;"):
    return f'<td style="{style}">{content}</td>'


# ══════════════════════════════════════════════════════════════
#  1. RADAR DASHBOARD  (Signal Surge Amplifier Grid)
# ══════════════════════════════════════════════════════════════

def build_radar_dashboard(df: pd.DataFrame, timestamp: str) -> str:
    """Build the screener radar HTML table."""

    col_names = [
        "Rank", "Ticker", "Last_Price", "Momentum_14d", "Vol_Surge",
        "Range_Pos_325", "Radar_Score", "Threshold", "Distance_%", "Z_Score"
    ]

    header = "".join(f"<th>{c}</th>" for c in col_names)
    thead  = f"<thead><tr>{header}</tr></thead>"

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
        <a href="../../us_hub.html" class="nav-btn" style="right:auto;left:28px;">◀ Hub</a><a href="../sniper/index.html" class="nav-btn">Go to Sniper ▶</a>
        <h2>Signal Surge Amplifier Grid</h2>
        <p class="subtitle">Generated {timestamp}</p>
        {table}
    """
    return _wrap_html("Radar — Signal Surge Amplifier Grid", body)


# ══════════════════════════════════════════════════════════════
#  2. BULK SNIPER DASHBOARD  (Runner Performance Protocol)
# ══════════════════════════════════════════════════════════════

def build_bulk_dashboard(summary_df: pd.DataFrame, timestamp: str) -> str:
    """Build the bulk sniper HTML — Runner Performance Protocol."""

    col_names = [
        "Rank", "Ticker", "WinRate_5d", "WinRate_10d", "WinRate_20d",
        "AvgRet_5d", "AvgRet_10d", "AvgRet_20d",
        "Sample", "Sniper_Score", "Sharia"
    ]

    header = "".join(f"<th>{c}</th>" for c in col_names)
    rows   = []

    for i, row in summary_df.iterrows():
        cells = [
            _td(row["Rank"], "color:#aaaaaa;"),
            _td(f'<a href="html/{row["Ticker"]}.html" style="color:#ff8c00;text-decoration:none;font-weight:bold;">{row["Ticker"]}</a>'),
            _td(row["WinRate_5d"],  _color_winrate(float(row["WinRate_5d"]))),
            _td(row["WinRate_10d"], _color_winrate(float(row["WinRate_10d"]))),
            _td(row["WinRate_20d"], _color_winrate(float(row["WinRate_20d"]))),
            _td(row["AvgRet_5d"],   _color_return(float(row["AvgRet_5d"]))),
            _td(row["AvgRet_10d"],  _color_return(float(row["AvgRet_10d"]))),
            _td(row["AvgRet_20d"],  _color_return(float(row["AvgRet_20d"]))),
            _td(row["Sample"], "color:#ffffff;"),
            _td(row["Sniper_Score"],    "color:#ff8c00;font-weight:bold;"),
            _td(row["Sharia"],         _color_sharia(str(row["Sharia"]))),
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')

    table = f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"

    body = f"""
        <a href="../../us_hub.html" class="nav-btn" style="right:auto;left:28px;">◀ Hub</a><a href="../radar/us_radar.html" class="nav-btn">Back to Radar ▶</a>
        <h2>Runner Performance Protocol</h2>
        <p class="subtitle">Generated {timestamp}</p>
        <p style="text-align:center;color:#555555;font-size:12px;letter-spacing:1px;margin-bottom:20px;">
            ↓ Click ticker to see full sniper details
        </p>
        {table}
    """
    return _wrap_html("Sniper — Runner Performance Protocol", body)


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
    color: #333;
    font-size: 11px;
    text-align: center;
    margin-top: 60px;
    letter-spacing: 1px;
}
"""


def _build_signal_table(df: pd.DataFrame) -> str:
    """Render a signals DataFrame (recent or power ranking) as an HTML table."""
    cols = ["Date", "Signal_Score", "Entry", "Return_5d (%)", "Return_10d (%)", "Return_20d (%)", "W/L"]

    # If df has Rank as index, reset it
    if df.index.name == "Rank":
        df = df.reset_index()
        cols = ["Rank"] + cols

    header = "".join(f"<th>{c}</th>" for c in cols)
    rows   = []

    for _, row in df.iterrows():
        cells = []
        for col in cols:
            val = row[col]
            if col == "Rank":
                style = "color:#aaaaaa;"
            elif col == "Date":
                style = "color:#888888;"
            elif col == "Signal_Score":
                style = "color:#ff8c00;font-weight:bold;"
            elif col == "Entry":
                style = "color:#ffffff;"
            elif col in ["Return_5d (%)", "Return_10d (%)", "Return_20d (%)"]:
                style = _color_return(float(val))
            elif col == "W/L":
                style = "color:#00ff88;" if "WIN" in str(val) else "color:#ff4d4d;"
            else:
                style = "color:#ffffff;"
            cells.append(f'<td style="{style}">{val}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')

    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _build_stats_table(stats_df: pd.DataFrame) -> str:
    """Render strategy stats (5/10/20 day avg return & win rate)."""
    header = "<th></th><th>Avg Return (%)</th><th>Win Rate (%)</th>"
    rows   = []
    for idx, row in stats_df.iterrows():
        ar  = float(row["Avg Return (%)"])
        wr  = float(row["Win Rate (%)"])
        cells = [
            f'<td style="color:#555555;">{idx}</td>',
            f'<td style="{_color_return(ar)}">{ar:.2f}</td>',
            f'<td style="{_color_winrate(wr)}">{wr:.2f}</td>',
        ]
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_single_dashboard(result: dict) -> str:
    """
    Build per-ticker sniper HTML dashboard.

    Args:
        result : dict returned by run_single_sniper()

    Returns:
        HTML string
    """
    meta    = result["meta"]
    ticker  = meta["ticker"]
    company = meta["company"]
    price   = meta["current_price"]
    score   = meta["current_score"]
    thr     = meta["threshold"]
    sniper  = meta["sniper_score"]
    verdict = meta["verdict"]
    sharia  = meta["sharia"]

    status_label = "🔥 READY TO EXECUTE" if score > thr else "😴 Wait for Momentum"
    status_cls   = "blinking" if score > thr else ""

    yahoo_url = f"https://finance.yahoo.com/quote/{ticker}/"

    style = f"<style>{_FONT_IMPORT}{_BASE_CSS}{_SINGLE_EXTRA_CSS}</style>"

    stats_table  = _build_stats_table(result["stats"])
    recent_table = _build_signal_table(result["recent"].copy())
    power_table  = _build_signal_table(result["power_ranking"].reset_index())

    body = f"""
        <a href="../index.html" class="nav-btn">◀ Back to Sniper</a>
        <h2 style="text-align:left;letter-spacing:2px;font-size:22px;margin-bottom:4px;">
        <strong>
            {company}
            <a href="{yahoo_url}" target="_blank"
               style="color:#ff8c00;text-decoration:none;">({ticker})</a>
        <strong>
        </h2>
        
        <p class="subtitle" style="text-align:left;margin-bottom:28px;font-size:15px;">
            Sharia: <span style="{_color_sharia(sharia)}">{sharia}</span>
        </p>

        <div class="status-container">
            <div class="status-box">
                <p>💵 Last Price: <b style="color:#ffffff;">{price:.2f}</b></p>
                <p>🎯 Radar Score: <b style="font-size:22px;color:#ff8c00;">{score:.2f}</b></p>
                <p>🛡️ Threshold (95%): <span style="color:#aaaaaa;">{thr:.2f}</span></p>
                <p>⚡ Status: <span class="{status_cls}">{status_label}</span></p>
            </div>
            <div class="verdict-box">
                <span class="score-label">Historical Sniper Score</span>
                <div class="score-value">{sniper}</div>
                <div class="verdict-text">{verdict}</div>
            </div>
        </div>

        <div class="section-title">📊 Average Strategy Performance</div>
        {stats_table}

        <div class="section-title">📅 10 Recent Signals — Regime Check</div>
        {recent_table}

        <div class="section-title">🏆 The Complete Power Ranking</div>
        {power_table}

        <p class="footer">Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """

    return f"<html><head><title>Sniper — {ticker}</title>{style}</head><body>{body}</body></html>"