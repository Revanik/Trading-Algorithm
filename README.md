# Stock Research Lab

A Python starting point for stock strategy research, backtesting, and a local simulated
account. The included strategy is an illustrative baseline with **no demonstrated profitable
edge**. Synthetic demo results say nothing about investment performance.

## Run locally

Install Git and Python 3.12 or newer. In Windows PowerShell, clone the setup branch
(use `main` after the pull request is merged):

```powershell
git clone --branch codex/trading-foundation https://github.com/Revanik/Trading-Algorithm.git
cd Trading-Algorithm
py scripts/setup.py
.\.venv\Scripts\python.exe -m stock_lab.cli backtest --csv data/demo.csv --start 2024-08-01 --output reports/demo.json
```

The setup creates an isolated `.venv`, installs the package and dev tools, and runs the
tests and lint checks. No Docker, Codespaces, broker credentials, or PowerShell activation
script is required. If the Windows Python launcher `py` is unavailable, use `python`
instead, ensuring it selects Python 3.12 or newer.

On macOS or Linux, after cloning and entering the repository:

```bash
bash scripts/setup.sh
source .venv/bin/activate
stock-lab backtest --csv data/demo.csv --start 2024-08-01 --output reports/demo.json
```

The full JSON report contains settings, fills, a daily equity curve, total return, maximum
drawdown, transaction costs, and a fully invested buy-and-hold comparison before costs.
That benchmark has different exposure from the capped strategy. There are no runtime
dependencies outside the Python standard library. Dev/build tools need package downloads.

## Codex Cloud development

Codex Cloud can work on the same GitHub repository while you run the code on your computer.
Its checkout, virtual environment, reports, and simulated account are separate from your
local checkout. Exchange code through Git commits and branches.

For the reusable Codex Cloud environment, select `Revanik/Trading-Algorithm`, use Python
3.12 or newer, and run `python3 scripts/setup.py` from the repository root as the setup
command. Until the pull request is merged, use `codex/trading-foundation` for tasks.
Setup needs access to GitHub and Python package downloads; no trading secrets are needed.
See [the environment checklist](docs/codex-cloud.md). This repository supplies setup
instructions; it does not publish or change your Codex environment settings automatically.

## Strategy and risk controls

At each session's open, compare the previous 20-session and 100-session average closes.
Hold a long position when the fast average is higher; otherwise hold cash. Signals use
only earlier rows. Until 100 earlier bars exist, stay in cash. Rebalance daily in whole shares.

Defaults: $10,000 simulated cash, up to 25% exposure **at execution**, and 10 basis points
of combined fees/slippage per buy or sell. The allocation budget includes these costs.
No shorting or leverage. Exposure can drift intraday. A 10% portfolio drawdown measured
at the close from the account's peak latches a halt and targets cash at the next open.
It does not guarantee a 10% loss limit: gaps and the final data row can leave positions
exposed. These are model controls, not broker-enforced controls.

```bash
stock-lab backtest --csv data/private/prices.csv --start 2025-01-01 \
  --fast 20 --slow 100 --cash 10000 --exposure 0.25 \
  --cost-bps 10 --max-drawdown 0.10 --output reports/evaluation.json
```

`--start` starts a fresh account on that date; earlier bars only warm up signals. Choose
and freeze parameters on an earlier period, then evaluate on an untouched later period.
Repeatedly selecting parameters against the later results invalidates that holdout.
Historical profits do not establish future profitability.

## Price data

Supply daily bars for **one stock per CSV**, oldest first, with no duplicate dates:

```csv
date,symbol,open,close
2024-01-02,EXAMPLE,100.00,101.00
2024-01-03,EXAMPLE,101.50,100.75
```

Use completed regular sessions and verify the exchange calendar upstream. The loader
checks ordering and positive finite prices but cannot detect missing sessions. Both price
columns must use a consistent corporate-action adjustment basis. Do not mix raw opens
with adjusted closes. This model does not separately book dividends, splits, interest,
taxes, spreads, market impact, or liquidity limits. Adjusted prices can imply hypothetical
fills; results are research approximations. Keep licensed/private data in ignored
`data/private/`. No market data is downloaded automatically.

`data/demo.csv` is deterministic **synthetic** data with no actual stock prices; it ignores
exchange holidays. Regenerate with `python scripts/generate_demo.py`.

## Local paper account

On Windows (without activating the virtual environment):

```powershell
.\.venv\Scripts\python.exe -m stock_lab.cli paper --csv data/demo.csv --start 2024-08-01 --state state/demo.sqlite3 --output reports/paper.json
```

On macOS/Linux, with the virtual environment activated:

```bash
stock-lab paper --csv data/demo.csv --start 2024-08-01 \
  --state state/demo.sqlite3 --output reports/paper.json
```

This replays CSV bars into a persistent SQLite account. It does not place orders or stream
real-time prices. Append completed sessions to the same CSV and repeat with the same
settings. Unchanged input creates no duplicate ledger entries. Changed/removed historical
rows or changed settings are rejected; use a different state file for a new experiment.
The local account is under ignored `state/`; back it up before deleting a cloud workspace.
No keys or broker account are required.

## Validation and next steps

```bash
python -m unittest discover -s tests -v
ruff check .
```

GitHub Actions runs on Windows and Linux and checks signal timing, costs, cash/exposure constraints,
drawdown halts, evaluation-period isolation, CSV validation, and paper replay safety.

Next: validate vetted historical data on unseen periods, different stocks, and realistic
costs. Then add an external data adapter and a broker's paper environment. A scheduled
cloud worker also needs durable storage, freshness/calendar checks, order reconciliation,
retry and duplicate-order handling, monitoring, alerts, and a manual stop. Store future
credentials in environment secrets, never in this public repository. There is no live
trading code in this project.
