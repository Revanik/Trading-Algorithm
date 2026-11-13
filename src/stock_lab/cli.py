import argparse
import json
import sqlite3
from pathlib import Path

from stock_lab.engine import Config, read_bars, simulate
from stock_lab.paper import replay


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stock strategy research and local simulated trading"
    )
    parser.add_argument("command", choices=("backtest", "paper"))
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument(
        "--start", help="Evaluation start date YYYY-MM-DD; prior rows warm up signals"
    )
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=100)
    parser.add_argument("--cash", type=float, default=10000)
    parser.add_argument("--exposure", type=float, default=0.25)
    parser.add_argument("--cost-bps", type=float, default=10)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    parser.add_argument("--state", type=Path, default=Path("state/paper.sqlite3"))
    parser.add_argument(
        "--output", type=Path, help="Save full JSON report including fills and equity"
    )
    args = parser.parse_args()
    try:
        config = Config(
            args.fast, args.slow, args.cash, args.exposure, args.cost_bps, args.max_drawdown
        )
        bars = read_bars(args.csv)
        if args.command == "paper":
            report = replay(args.state, bars, config, args.start)
        else:
            report = simulate(bars, config, args.start)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {k: v for k, v in report.items() if k not in ("fills", "equity_curve")}, indent=2
            )
        )
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(2, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
