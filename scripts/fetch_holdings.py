import requests
import pandas as pd
import pandas_market_calendars as mcal
import json
import os
import sys
from datetime import date
from io import BytesIO

DOWNLOAD_URL = (
    "https://www.capitalgroup.com/api/investments/investment-service/v1/etfs/cgdv"
    "/download/daily-holdings?audience=advisor&redirect=true"
)
SHEET_NAME = "Daily Fund Holdings"
HEADER_ROW = 2  # 0-indexed, so row 3 in Excel

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def download_file():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
        "Referer": "https://www.capitalgroup.com/",
    }
    resp = requests.get(DOWNLOAD_URL, headers=headers, allow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.content


def find_column(columns, *keywords):
    for col in columns:
        col_lower = str(col).lower()
        if any(kw.lower() in col_lower for kw in keywords):
            return col
    return None


def parse_holdings(content):
    df = pd.read_excel(BytesIO(content), sheet_name=SHEET_NAME, header=HEADER_ROW)

    cols = df.columns.tolist()
    print("Detected columns: {}".format(cols), file=sys.stderr)

    ticker_col = find_column(cols, "ticker", "symbol")
    pct_col    = find_column(cols, "net assets", "% of", "weight", "percent")
    shares_col = find_column(cols, "shares", "principal")

    missing = [name for name, col in [("ticker", ticker_col), ("pct_net_assets", pct_col), ("shares", shares_col)] if col is None]
    if missing:
        raise ValueError("Could not locate columns: {}. Available columns: {}".format(missing, cols))

    df = df[[ticker_col, pct_col, shares_col]].copy()
    df.columns = ["ticker", "pct_net_assets", "shares"]

    df["ticker"] = df["ticker"].astype(str).str.strip()
    df = df[df["ticker"].notna() & (df["ticker"] != "") & (df["ticker"] != "nan")]

    def safe_float(x):
        try:
            return round(float(x), 6)
        except (TypeError, ValueError):
            return None

    records = []
    for _, row in df.iterrows():
        records.append({
            "ticker":         row["ticker"],
            "pct_net_assets": safe_float(row["pct_net_assets"]),
            "shares":         safe_float(row["shares"]),
        })

    return records


def save_snapshot(records, today_str):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "{}.json".format(today_str))
    payload = {"date": today_str, "holdings": records}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    with open(os.path.join(DATA_DIR, "latest.json"), "w") as f:
        json.dump(payload, f, indent=2)
    print("Saved {} holdings → {}".format(len(records), path), file=sys.stderr)


def find_prior_snapshot(today_str):
    files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.endswith(".json") and f not in ("latest.json", "diff.json", "history.json")
    )
    prior = [f for f in files if f.replace(".json", "") < today_str]
    return os.path.join(DATA_DIR, prior[-1]) if prior else None


def compute_diff(today_records, prior_records, today_str, prior_date_str):
    today_map   = {r["ticker"]: r for r in today_records}
    prior_map   = {r["ticker"]: r for r in prior_records}
    all_tickers = sorted(set(today_map) | set(prior_map))

    rows = []
    for ticker in all_tickers:
        t = today_map.get(ticker)
        p = prior_map.get(ticker)

        if t and p:
            s_today   = t["shares"] or 0
            s_prior   = p["shares"] or 0
            pct_today = t["pct_net_assets"] or 0
            pct_prior = p["pct_net_assets"] or 0

            shares_chg = ((s_today - s_prior) / s_prior * 100) if s_prior != 0 else 0
            pct_chg    = round(pct_today - pct_prior, 4)

            rows.append({
                "ticker":                ticker,
                "status":                "changed" if shares_chg != 0 else "unchanged",
                "shares_today":          s_today,
                "shares_prior":          s_prior,
                "shares_pct_change":     round(shares_chg, 4),
                "pct_net_assets_today":  pct_today,
                "pct_net_assets_prior":  pct_prior,
                "pct_net_assets_change": pct_chg,
            })
        elif t:
            rows.append({
