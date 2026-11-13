# Codex Cloud environment checklist

Run the trading research tools locally; use Codex Cloud for development tasks against
the same GitHub repository. No GitHub Codespace or continuously hosted bot is required.

In the Codex environment settings/onboarding flow:

1. Select repository `Revanik/Trading-Algorithm`.
2. Provide Python 3.12 or newer and Git.
3. Set the setup command, run from the checkout root, to `python3 scripts/setup.py`.
4. Allow repository access to GitHub and package downloads from `pypi.org` and
   `files.pythonhosted.org` during setup. Keep any other required existing access settings.
5. No broker credentials or other application secrets are needed for the current simulator.
6. Save and publish the configuration in Codex's environment settings, then select it for
   future tasks. Until PR #1 is merged, choose branch `codex/trading-foundation` for tasks.

Validate inside a task using that environment:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check .
.venv/bin/python -m stock_lab.cli backtest --csv data/demo.csv --start 2024-08-01
```

Do not assume this checklist has registered or published an environment. The existing
chat's attached cloud workspace is also distinct from your Windows computer. Local
simulation state and reports stay on the machine where the command runs and are ignored
by Git. After cloud code changes are pushed, pull them locally before running the new code.
