"""Create deterministic synthetic daily bars for plumbing checks, never strategy evidence."""

import csv
import math
from datetime import date, timedelta
from pathlib import Path

destination = Path(__file__).resolve().parents[1] / "data" / "demo.csv"
destination.parent.mkdir(parents=True, exist_ok=True)
with destination.open("w", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("date", "symbol", "open", "close"))
    day = date(2024, 1, 1)
    previous = 100.0
    for i in range(400):
        while day.weekday() >= 5:
            day += timedelta(days=1)
        opening = previous * (1 + 0.002 * math.sin(i * 0.7))
        closing = 100 * math.exp(0.0006 * i + 0.12 * math.sin(i / 27))
        writer.writerow((day.isoformat(), "SYNTH", f"{opening:.4f}", f"{closing:.4f}"))
        previous = closing
        day += timedelta(days=1)
print(destination)
