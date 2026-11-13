"""Persist a local simulated account; never connect to a broker."""

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from stock_lab.engine import Bar, Config, simulate


def fingerprint(bars: list[Bar]) -> str:
    payload = json.dumps([asdict(bar) for bar in bars], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def replay(path: Path, bars: list[Bar], config: Config, start: str | None = None) -> dict:
    """Accept an append-only price history. Commit ledger and snapshot together."""
    report = simulate(bars, config, start)
    settings = json.dumps({"config": asdict(config), "start": start}, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, isolation_level=None) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("CREATE TABLE IF NOT EXISTS snapshot (id INTEGER PRIMARY KEY, payload TEXT)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS ledger (date TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            prior = db.execute("SELECT payload FROM snapshot WHERE id = 1").fetchone()
            old_count = 0
            if prior:
                old = json.loads(prior[0])
                old_count = old["bar_count"]
                if old["settings"] != settings:
                    raise ValueError("Account configuration changed; use a new state file")
                if len(bars) < old_count or fingerprint(bars[:old_count]) != old["history_hash"]:
                    raise ValueError(
                        "Historical bars changed or were removed; use a new state file"
                    )
            for row in report["equity_curve"]:
                db.execute(
                    "INSERT OR IGNORE INTO ledger VALUES (?, ?)",
                    (row["date"], json.dumps(row, sort_keys=True)),
                )
            snapshot = {
                "bar_count": len(bars),
                "history_hash": fingerprint(bars),
                "settings": settings,
                "report": report,
            }
            db.execute("INSERT OR REPLACE INTO snapshot VALUES (1, ?)", (json.dumps(snapshot),))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
    return {**report, "new_bars": len(bars) - old_count, "state_file": str(path)}
