import argparse
import os

import pandas as pd
import yfinance as yf


def fetch_and_save(ticker, period="1y", interval="1d", out_dir="data"):
    os.makedirs(out_dir, exist_ok=True)

    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"yfinance returned no data for ticker={ticker!r}, period={period!r}, interval={interval!r}")

    if isinstance(df.columns, pd.MultiIndex):
        # yfinance returns a (field, ticker) MultiIndex even for a single
        # ticker -- flatten it so the saved CSV has a plain, single-row
        # header (just "Close", "High", "Low", "Open", "Volume").
        df.columns = df.columns.get_level_values(0)

    out_path = os.path.join(out_dir, f"{ticker}_{interval}.csv")
    df.to_csv(out_path)
    print(f"Saved {len(df)} rows to {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch historical price data via yfinance and save as CSV.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. AAPL, BTC-USD, EURUSD=X")
    parser.add_argument("--period", default="1y", help="How far back to fetch, e.g. 1mo, 6mo, 1y, 5y, max")
    parser.add_argument("--interval", default="1d", help="Bar size, e.g. 1m, 5m, 1h, 1d (intraday intervals are limited to recent history by Yahoo)")
    parser.add_argument("--out-dir", default="data", help="Directory to save the CSV into")
    args = parser.parse_args()

    fetch_and_save(args.ticker, period=args.period, interval=args.interval, out_dir=args.out_dir)
