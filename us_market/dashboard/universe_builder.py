"""
universe_builder.py
Generates output/universe/index.html — Listed Stocks universe dashboard.
Place this file at: quant-radar/us_market/dashboard/universe_builder.py
"""

from pathlib import Path
import pandas as pd
import base64
import json

# ─────────────────────────────────────────
#  SECTOR EMOJI MAP
# ─────────────────────────────────────────

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

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────

def _load_logo_b64(logo_path: Path) -> str | None:
    """Return base64-encoded SVG data URI, or None if file missing."""
    if logo_path.exists():
        data = logo_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"
    return None


def _price_change_pct(last: float, prev: float) -> float | None:
    if prev and prev != 0:
        return round((last - prev) / prev * 100, 2)
    return None


# ─────────────────────────────────────────
#  STATIC CSS
# ─────────────────────────────────────────

STATIC_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
    background: #000000;
    color: #cccccc;
    font-family: "IBM Plex Mono", "Courier New", monospace;
    min-height: 100vh;
    padding: 20px 16px 60px;
    overflow-x: hidden;         
}

/* ── BACK BUTTON ── */
.back-btn {
    position: fixed;
    top: 24px;
    right: 28px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 12px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #000000;
    background: #ff8c00;
    padding: 10px 18px;
    text-decoration: none;
    transition: background 0.15s;
    z-index: 999;
}
.back-btn:hover { background: #ffaa33; }

/* ── HEADER ── */
.header {
    text-align: center;
    margin-bottom: 24px;      
}
.badge {
    font-size: 11px;
    letter-spacing: 3px;
    color: #444444;
    text-transform: uppercase;
    margin-bottom: 10px;       
}
h1 {
    font-size: 32px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: 5px;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.subtitle {
    font-size: 12px;
    color: #444444;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.subtitle .brand {
    color: #6C63FF;
    text-decoration: none;
}
.subtitle .brand:hover { text-decoration: underline; }

/* ── CONTROLS ── */
.controls {
    display: flex;
    gap: 8px;                  
    max-width: 900px;
    margin: 0 auto 24px;
    align-items: center;
    flex-wrap: nowrap;          
}
.search-wrap {
    flex: 1;
    min-width: 0;                
    position: relative;
}
.search-icon {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: #444;
    font-size: 14px;
    pointer-events: none;
}
#searchInput {
    width: 100%;
    background: #111111;
    border: 1px solid #222222;
    color: #cccccc;
    font-family: "IBM Plex Mono", monospace;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 11px 14px 11px 36px;
    outline: none;
    transition: border-color 0.15s;
}
#searchInput:focus { border-color: #ff8c00; }
#searchInput::placeholder { color: #333333; }

.sort-btn {
    background: transparent;
    border: 1px solid #222222;
    color: #666666;
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 11px 16px;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
}
.sort-btn:hover { border-color: #ff8c00; color: #ff8c00; }
.sort-btn.active { border-color: #ff8c00; color: #ff8c00; background: rgba(255,140,0,0.06); }

.result-count {
    font-size: 11px;
    color: #333333;
    letter-spacing: 1px;
    white-space: nowrap;
    padding: 11px 0;
}
.result-count span { color: #ff8c00; }

/* ── GRID ── */
.grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);  
    gap: 10px;
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;                           
}

/* ── CARD ── */
.card {
    background: #0d0d0d;
    border: 1px solid #1a1a1a;
    padding: 14px 14px 12px;
    display: grid;
    grid-template-rows: auto auto;
    grid-template-columns: 1fr auto;
    gap: 4px 8px;
    transition: border-color 0.15s, background 0.15s;
    position: relative;
}
.card-link {
    text-decoration: none;
    display: block;
    color: inherit;
}
.card-link:hover .card {
    border-color: #ff8c00;
    background: #111111;
}

.card-top {
    display: flex;
    align-items: center;
    gap: 10px;
    grid-column: 1;
    grid-row: 1;
}
.logo-wrap {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    background: #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}
.logo-wrap img {
    width: 28px;
    height: 28px;
    object-fit: contain;
}
.logo-placeholder {
    font-size: 13px;
    font-weight: 600;
    color: #333333;
    letter-spacing: 0;
}
.card-name-wrap { flex: 1; min-width: 0; }
.card-ticker {
    font-size: 14px;
    font-weight: 600;
    color: #ff8c00;
    letter-spacing: 1px;
}
.card-name {
    font-size: 9px;
    color: #ffffff;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
}

.card-sector {
    font-size: 9px;
    color: #555555;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    grid-column: 1;
    grid-row: 2;
    align-self: end;
}
.card-sector .emoji { margin-right: 4px; font-size: 10px; }
.card-sector .industry-text { color: #ff8c00; opacity: 0.7; }

.card-price {
    font-size: 12px;
    font-weight: 600;
    color: #cccccc;
    letter-spacing: 0.5px;
    grid-column: 2;
    grid-row: 1;
    align-self: start;
    text-align: right;
}
.card-change {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    grid-column: 2;
    grid-row: 2;
    align-self: end;
    text-align: right;
}

.card-change.pos { color: #00c07a; }
.card-change.neg { color: #e05050; }
.card-change.neu { color: #444444; }

/* ── HIDDEN ── */
.card-link.hidden { display: none; }

/* ── FOOTER ── */
footer {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 11px;
    color: #2a2a2a;
    letter-spacing: 1px;
    pointer-events: none;
}

/* ── RESPONSIVE ── */
@media (max-width: 1100px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 700px)  { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px)  {
    .grid { grid-template-columns: 1fr; }
    h1 { font-size: 22px; letter-spacing: 3px; }
    .back-btn { font-size: 10px; padding: 8px 14px; top: 16px; right: 16px; }
    .sort-btn { font-size: 10px; padding: 8px 10px; }
    .result-count { font-size: 10px; }
}
"""

# ─────────────────────────────────────────
#  STATIC JS
# ─────────────────────────────────────────

STATIC_JS = """\
(function () {
    const searchInput  = document.getElementById('searchInput');
    const resultCount  = document.getElementById('resultCount');
    const cards        = Array.from(document.querySelectorAll('.card-link'));
    const btnAlpha     = document.getElementById('sortAlpha');
    const btnChange    = document.getElementById('sortChange');
    const grid         = document.getElementById('cardGrid');

    let currentSort = 'alpha';

    function getVisible() {
        return cards.filter(c => !c.classList.contains('hidden'));
    }

    function updateCount() {
        resultCount.innerHTML = '<span>' + getVisible().length + '</span> tickers';
    }

    function applySearch() {
        const q = searchInput.value.trim().toLowerCase();
        cards.forEach(c => {
            const match = !q ||
                c.dataset.ticker.toLowerCase().includes(q) ||
                c.dataset.name.toLowerCase().includes(q) ||
                c.dataset.sector.toLowerCase().includes(q) ||
                c.dataset.industry.toLowerCase().includes(q);
            c.classList.toggle('hidden', !match);
        });
        updateCount();
        applySort(currentSort);
    }

    function applySort(mode) {
        currentSort = mode;
        btnAlpha.classList.toggle('active', mode === 'alpha');
        btnChange.classList.toggle('active', mode === 'change');

        const visible = getVisible();
        visible.sort((a, b) => {
            if (mode === 'alpha') {
                return a.dataset.ticker.localeCompare(b.dataset.ticker);
            } else {
                const ca = parseFloat(a.dataset.change) || -9999;
                const cb = parseFloat(b.dataset.change) || -9999;
                return cb - ca;
            }
        });
        visible.forEach(c => grid.appendChild(c));
    }

    searchInput.addEventListener('input', applySearch);
    btnAlpha.addEventListener('click',  () => applySort('alpha'));
    btnChange.addEventListener('click', () => applySort('change'));

    updateCount();
    applySort('alpha');
})();
"""

# ─────────────────────────────────────────
#  CARD HTML BUILDER
# ─────────────────────────────────────────

def _build_card(row: dict) -> str:
    ticker   = row["ticker"]
    name     = row["nama_perusahaan"]
    sector   = row["sektor"]
    industry = row["industry"]
    price    = row.get("last_price")
    change   = row.get("change_pct")
    logo_uri = row.get("logo_uri")

    emoji = SECTOR_EMOJI.get(sector, "📊")

    # Logo or placeholder
    if logo_uri:
        logo_html = f'<img src="{logo_uri}" alt="{ticker}" loading="lazy">'
    else:
        initials = ticker[:2]
        logo_html = f'<span class="logo-placeholder">{initials}</span>'

    # Price display
    if price is not None:
        price_html = f'${price:,.2f}'
    else:
        price_html = "—"

    # Change display
    if change is not None:
        if change > 0:
            change_class = "pos"
            change_str = f"+{change:.2f}%"
        elif change < 0:
            change_class = "neg"
            change_str = f"{change:.2f}%"
        else:
            change_class = "neu"
            change_str = "0.00%"
    else:
        change_class = "neu"
        change_str = "—"

    change_val = f"{change:.4f}" if change is not None else "-9999"

    # Truncate long names for display
    display_name = name if len(name) <= 28 else name[:25] + "..."
    display_industry = industry if len(industry) <= 22 else industry[:19] + "..."

    return f"""\
<a class="card-link"
   href="https://finance.yahoo.com/quote/{ticker}/"
   target="_blank" rel="noopener"
   data-ticker="{ticker}"
   data-name="{name.lower()}"
   data-sector="{sector.lower()}"
   data-industry="{industry.lower()}"
   data-change="{change_val}">
<div class="card">
  <div class="card-top">
    <div class="logo-wrap">{logo_html}</div>
    <div class="card-name-wrap">
      <div class="card-ticker">{ticker}</div>
      <div class="card-name" title="{name}">{display_name}</div>
    </div>
  </div>
  <div class="card-sector">
    <span class="emoji">{emoji}</span>{sector} | <span class="industry-text">{display_industry}</span>
  </div>
  <span class="card-price">{price_html}</span>
  <span class="card-change {change_class}">{change_str}</span>
</div>
</a>"""


# ─────────────────────────────────────────
#  MAIN BUILD FUNCTION
# ─────────────────────────────────────────

def build_universe_dashboard(base_dir: Path) -> None:
    """
    Reads ticker_universe.csv, logos, and us_radar.csv,
    then writes output/universe/index.html (+ style.css & script.js).
    """

    config_dir  = base_dir / "config"
    logos_dir   = config_dir / "logos"
    radar_csv   = base_dir / "output" / "radar" / "us_radar.csv"
    out_dir     = base_dir / "output" / "universe"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Load ticker universe ──────────────────────────────────────────────────
    universe_csv = config_dir / "ticker_universe.csv"
    df = pd.read_csv(universe_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    # Normalise expected columns
    df = df.rename(columns={
        "nama_perusahaan": "nama_perusahaan",
        "company_name": "nama_perusahaan",
        "name": "nama_perusahaan",
        "sektor": "sektor",
        "sector": "sektor",
        "industry": "industry",
    })
    for col in ["ticker", "nama_perusahaan", "sektor", "industry"]:
        if col not in df.columns:
            df[col] = ""

    # ── Load prices ───────────────────────────────────────────────────────────
    price_map: dict[str, dict] = {}
    if radar_csv.exists():
        rdf = pd.read_csv(radar_csv)
        rdf.columns = [c.strip() for c in rdf.columns]
        for _, row in rdf.iterrows():
            t = str(row.get("Ticker", "")).upper()
            lp = row.get("Last_Price")
            pc = row.get("Prev_Close")
            price_map[t] = {"last": lp, "prev": pc}

    # ── Build cards ───────────────────────────────────────────────────────────
    cards_html = []
    for _, row in df.iterrows():
        ticker = str(row["ticker"]).upper().strip()
        name   = str(row.get("nama_perusahaan", ticker))
        sector = str(row.get("sektor", ""))
        indust = str(row.get("industry", ""))

        logo_uri = _load_logo_b64(logos_dir / f"{ticker}.svg")

        prices = price_map.get(ticker, {})
        last   = prices.get("last")
        prev   = prices.get("prev")

        try:
            last = float(last) if last is not None else None
            prev = float(prev) if prev is not None else None
        except (ValueError, TypeError):
            last = prev = None

        change = _price_change_pct(last, prev) if (last is not None and prev is not None) else None

        cards_html.append(_build_card({
            "ticker": ticker,
            "nama_perusahaan": name,
            "sektor": sector,
            "industry": indust,
            "last_price": last,
            "change_pct": change,
            "logo_uri": logo_uri,
        }))

    total = len(df)
    cards_joined = "\n".join(cards_html)

    # ── Write static CSS & JS ─────────────────────────────────────────────────
    css_path = out_dir / "style.css"
    js_path  = out_dir / "script.js"

    css_path.write_text(STATIC_CSS, encoding="utf-8")
    # print(f"📄 style.css written → {css_path}")

    js_path.write_text(STATIC_JS, encoding="utf-8")
    # print(f"📄 script.js written → {js_path}")
    

    # ── Assemble HTML ─────────────────────────────────────────────────────────
    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="../../assets/logo.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="./style.css">
    <link rel="icon" type="image/png" href="../../../assets/logo.png">
    <title>Listed Stocks — Issuers</title>
</head>
<body>

    <a href="../../us_hub.html" class="back-btn"><strong>◀ Hub</strong></a>

    <div class="header">
        <div class="badge">US Market / Issuers</div>
        <h1>Listed Stocks</h1>
        <p class="subtitle">
            Universe of {total} tickers
            available on <a class="brand" href="https://pluang.com/explore/us-market/stocks" target="_blank" rel="noopener">Pluang</a>
        </p>
    </div>

    <div class="controls">
        <div class="search-wrap">
            <span class="search-icon">⌕</span>
            <input type="text" id="searchInput" placeholder="Search ticker, name, sector...">
        </div>
        <button class="sort-btn active" id="sortAlpha">A–Z</button>
        <button class="sort-btn" id="sortChange">% Change</button>
    </div>

    <div class="grid" id="cardGrid">
{cards_joined}
    </div>

    <footer>© 2026 Quant Radar System</footer>

    <script src="./script.js"></script>
</body>
</html>"""

    out_html = out_dir / "index.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"🌐 Universe dashboard saved → {out_html}")


# ─────────────────────────────────────────
#  STANDALONE ENTRY (optional)
# ─────────────────────────────────────────

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    build_universe_dashboard(base)