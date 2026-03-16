def build_radar_dashboard(df, timestamp):

    table = df.to_html(index=False)

    html_style = """
    <style>

    body{
        font-family: "SF Mono","Monaco","Cascadia Code","Fira Code","DejaVu Sans Mono","Liberation Mono",monospace;
        background: radial-gradient(circle at top, #1a1a2e, #0f0f17);
        color:#e6edf3;
        padding:40px;
    }

    h2{
        text-align:center;
        font-size:28px;
        letter-spacing:2px;
        color:#58a6ff;
        margin-bottom:30px;
    }

    table{
        width:100%;
        border-collapse:collapse;
        background:#0d1117;
        border-radius:8px;
        overflow:hidden;
        box-shadow:0 0 30px rgba(0,0,0,0.8);
    }

    th{
        background:#161b22;
        color:#58a6ff;
        font-size:13px;
        text-transform:uppercase;
        letter-spacing:1px;
        padding:14px;
        border-bottom:1px solid #30363d;
    }

    td{
        padding:12px;
        border-bottom:1px solid #21262d;
    }

    tr:hover{
        background:#161b22;
        transition:0.2s;
    }

    /* rank column */
    td:first-child{
        color:#8b949e;
    }

    /* top 5 glow */
    tr:nth-child(-n+5){
        background:linear-gradient(90deg,#0f2027,#203a43);
        font-weight:bold;
    }

    /* score highlight */
    td:last-child{
        color:#00ffa6;
        font-weight:bold;
    }

    /* momentum positive */
    td:nth-child(4){
        color:#58a6ff;
    }

    /* volume surge */
    td:nth-child(5){
        color:#d2a8ff;
    }

    </style>
    """

    html = f"""
    <html><head>{html_style}</head><body>
    <h2>🚀 US MARKET QUANT RADAR</h2>
    <p style='text-align:center;color:#8b949e;'>Generated {timestamp}</p>
    {table}
    </body></html>
    """

    return html