import csv
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from stock_lab.engine import Bar, Config, read_bars, simulate
from stock_lab.paper import replay


def bars(prices):
    return [
        Bar((date(2024, 1, 1) + timedelta(days=i)).isoformat(), "TEST", p, p)
        for i, p in enumerate(prices)
    ]


class EngineTests(unittest.TestCase):
    def test_signal_uses_prior_closes_and_executes_at_next_open(self):
        data = bars([10, 10, 20, 30])
        config = Config(fast=1, slow=2, initial_cash=1000, max_exposure=1, cost_bps=0)
        result = simulate(data, config)
        self.assertEqual(result["fills"][0]["date"], data[3].date)
        self.assertEqual(result["fills"][0]["price"], 30)
        changed = data[:3] + [replace(data[3], close=0.5)]
        self.assertEqual(result["fills"], simulate(changed, config)["fills"])

    def test_costs_charged_on_buys_and_sells(self):
        result = simulate(
            bars([10, 20, 10, 10]),
            Config(fast=1, slow=2, initial_cash=1000, max_exposure=1, cost_bps=100),
        )
        self.assertEqual([f["shares"] for f in result["fills"]], [99, -99])
        self.assertAlmostEqual(result["total_cost"], 19.8)
        self.assertAlmostEqual(result["equity_curve"][-1]["cash"], 980.2)

    def test_drawdown_halts_and_liquidates_next_open(self):
        data = bars([10, 20, 30, 5, 100, 120])
        result = simulate(data, Config(fast=1, slow=2, max_exposure=1, cost_bps=0))
        self.assertTrue(result["equity_curve"][3]["halted"])
        self.assertEqual(result["fills"][-1]["date"], data[4].date)
        self.assertLess(result["fills"][-1]["shares"], 0)
        self.assertEqual(result["equity_curve"][-1]["shares"], 0)

    def test_evaluation_starts_with_fresh_capital_and_prior_signal(self):
        data = bars([10, 20, 30, 40])
        result = simulate(data, Config(fast=1, slow=2, cost_bps=0), data[2].date)
        self.assertEqual(len(result["equity_curve"]), 2)
        self.assertEqual(result["fills"][0]["date"], data[2].date)
        self.assertEqual(result["equity_curve"][0]["equity"], 10000)

    def test_cash_and_exposure_bounded_at_execution(self):
        data = bars([10, 20, 15, 50, 80, 20, 19, 100])
        for costs in (0, 10, 5000):
            result = simulate(data, Config(fast=1, slow=2, cost_bps=costs))
            for row, bar in zip(result["equity_curve"], data, strict=True):
                self.assertGreaterEqual(row["cash"], -1e-8)
                self.assertGreaterEqual(row["shares"], 0)
                equity_at_open = row["cash"] + row["shares"] * bar.open
                self.assertLessEqual(row["shares"] * bar.open, equity_at_open * 0.25 + 1e-8)

    def test_reject_invalid_configuration(self):
        for kwargs in (
            {"fast": 100},
            {"initial_cash": float("nan")},
            {"cost_bps": -1},
            {"max_exposure": 2},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Config(**kwargs)

    def test_csv_rejects_bad_data(self):
        cases = [
            [("2024-01-01", "A", "nan", "10")],
            [("2024-01-01", "A", "0", "10")],
            [("2024-01-01", "A")],
            [("2024-01-01", "A", "10", "10"), ("2024-01-01", "A", "10", "10")],
            [("2024-01-02", "A", "10", "10"), ("2024-01-01", "A", "10", "10")],
            [("2024-01-01", "A", "10", "10"), ("2024-01-02", "B", "10", "10")],
            [],
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bars.csv"
            for rows in cases:
                with path.open("w", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(("date", "symbol", "open", "close"))
                    writer.writerows(rows)
                with self.subTest(rows=rows), self.assertRaises(ValueError):
                    read_bars(path)


class PaperTests(unittest.TestCase):
    def test_replay_is_idempotent_and_append_matches_backtest(self):
        data = bars([10, 20, 15, 30, 40])
        config = Config(fast=1, slow=2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "paper.sqlite3"
            replay(path, data[:3], config)
            second = replay(path, data[:3], config)
            self.assertEqual(second["new_bars"], 0)
            appended = replay(path, data, config)
            self.assertEqual(appended["new_bars"], 2)
            expected = simulate(data, config)
            self.assertEqual(appended["fills"], expected["fills"])
            self.assertEqual(appended["equity_curve"], expected["equity_curve"])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0], 5)

    def test_rejects_rewritten_history_and_settings_without_changing_account(self):
        data = bars([10, 20, 15, 30])
        config = Config(fast=1, slow=2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "paper.sqlite3"
            replay(path, data, config)
            for history, settings in (
                (data[:-1], config),
                ([replace(data[0], close=12)] + data[1:], config),
                (data, replace(config, cost_bps=0)),
            ):
                with self.assertRaises(ValueError):
                    replay(path, history, settings)
            with sqlite3.connect(path) as db:
                saved = json.loads(db.execute("SELECT payload FROM snapshot").fetchone()[0])
                self.assertEqual(saved["bar_count"], 4)
                self.assertEqual(saved["report"]["config"]["cost_bps"], 10)


if __name__ == "__main__":
    unittest.main()
