"""
IDX (Indonesia Stock Exchange) Trading Summary Scraper

Fetches daily trading summary data from idx.co.id and exports to Parquet format.
Designed for GitHub Actions automation.

Usage:
    python -m id_market.scraper [--date YYYYMMDD]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.idx.co.id/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_trading_summary(date_str: str) -> dict | None:
    """
    Fetch trading summary JSON from IDX API.

    Args:
        date_str: Date in YYYYMMDD format

    Returns:
        Parsed JSON response or None if request fails
    """
    params = {"length": 9999, "start": 0, "date": date_str}

    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return None


def parse_to_dataframe(raw_data: dict) -> pd.DataFrame:
    """
    Parse IDX JSON response into a DataFrame.

    Args:
        raw_data: JSON response from IDX API

    Returns:
        DataFrame with trading summary data
    """
    records = raw_data.get("data", [])

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Convert numeric columns
    numeric_cols = ["freq", "volume", "value"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Calculate average tick size (value / freq)
    df["avg_tick"] = df.apply(
        lambda row: row["value"] / row["freq"] if row["freq"] > 0 else 0.0,
        axis=1
    )

    return df


def export_to_parquet(df: pd.DataFrame, date_str: str, output_dir: Path) -> Path | None:
    """
    Export DataFrame to Parquet file.

    Args:
        df: DataFrame to export
        date_str: Date string for filename
        output_dir: Output directory path

    Returns:
        Path to saved file or None if export fails
    """
    if df.empty:
        print("No data to export", file=sys.stderr)
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}.parquet"

    try:
        df.to_parquet(output_path, index=False)
        return output_path
    except Exception as e:
        print(f"Error writing Parquet: {e}", file=sys.stderr)
        return None


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="IDX Trading Summary Scraper"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime("%Y%m%d"),
        help="Trading date in YYYYMMDD format (default: today)"
    )
    args = parser.parse_args()

    date_str = args.date
    base_dir = Path(__file__).resolve().parents[1]
    output_dir = base_dir / "id_market" / "data" / "daily"

    print(f"Fetching IDX trading summary for {date_str}...")

    # Fetch data
    raw_data = fetch_trading_summary(date_str)
    if raw_data is None:
        print("Failed to fetch data. Market may be closed or API unavailable.", file=sys.stderr)
        sys.exit(1)

    # Parse to DataFrame
    df = parse_to_dataframe(raw_data)
    if df.empty:
        print(f"No trading data found for {date_str}. Possible market holiday.", file=sys.stderr)
        sys.exit(0)

    # Export to Parquet
    output_path = export_to_parquet(df, date_str, output_dir)
    if output_path:
        print(f"Exported {len(df)} records to {output_path}")
    else:
        print("Failed to export data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
