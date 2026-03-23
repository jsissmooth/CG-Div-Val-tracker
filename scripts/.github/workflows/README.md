# CGDV Daily Holdings Tracker

Automatically downloads the Capital Group Dividend Value ETF (CGDV) daily holdings Excel file, diffs it against the prior day, and displays changes on a GitHub Pages dashboard.

## What it does

- **Every weekday at 9:30 AM ET**, a GitHub Actions job runs automatically
- It downloads the holdings Excel file, parses Ticker / % of Net Assets / Shares columns
- Saves a dated JSON snapshot to `data/`
- Computes a diff vs. the most recent prior snapshot
- Commits the results back to the repo
- Your GitHub Pages dashboard reflects the latest diff automatically

## Dashboard features

- Summary cards: total holdings, changed, added, removed
- Color coded rows: green = added, red = removed, yellow = changed
- Filter by status, search by ticker, sort multiple ways
- Mini bars showing visual magnitude of each change

## File layout
```
├── index.html                        # Dashboard (served by GitHub Pages)
├── scripts/
│   └── fetch_holdings.py             # Download + parse + diff logic
├── .github/
│   └── workflows/
│       └── daily_holdings.yml        # Scheduled automation
└── data/
    ├── .gitkeep                      # Ensures folder exists in git
    ├── YYYY-MM-DD.json               # Daily snapshot (one per run)
    ├── latest.json                   # Most recent snapshot
    ├── diff.json                     # Most recent diff (what the dashboard reads)
    └── history.json                  # Index of all run dates
```

## Schedule

Runs weekdays only at 9:30 AM ET. The script also checks the NYSE trading calendar and skips federal holidays automatically.
