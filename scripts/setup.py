"""Set up the project on Windows, macOS, Linux, or Codex Cloud."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if sys.version_info < (3, 12):  # noqa: UP036 - bootstrap also runs on unsupported Python.
        raise SystemExit("Python 3.12 or newer is required. Install it and run setup again.")
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "-m", "venv", str(root / ".venv")], check=True)
    folder, executable = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    python = root / ".venv" / folder / executable
    commands = [
        ["-m", "pip", "install", "--disable-pip-version-check", "-e", ".[dev]"],
        ["-m", "unittest", "discover", "-s", "tests", "-v"],
        ["-m", "ruff", "check", "."],
    ]
    for command in commands:
        subprocess.run([str(python), *command], cwd=root, check=True)
    print("Ready. Run the synthetic demo (from the repository root):", flush=True)
    prefix = "& " if os.name == "nt" else ""
    print(f'{prefix}"{python}" -m stock_lab.cli backtest --csv data/demo.csv', flush=True)


if __name__ == "__main__":
    main()
