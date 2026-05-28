# Contributing

Thank you for considering a contribution to Flight Price Tracker MCP!

## Getting started

```bash
git clone https://github.com/YOUR_LOGIN/flight-price-tracker-mcp.git
cd flight-price-tracker-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-dev.txt
```

## Running tests

```bash
.venv/bin/pytest tests/ -v
```

## Project structure

```
src/
  server.py    — MCP tools (add_route, check_price, analyze_route, …)
  db.py        — SQLite storage layer
  pricing.py   — Kiwi.com API + demo mode
tests/
  test_smoke.py   — import + tool registration checks
  test_db.py      — storage layer unit tests
  test_pricing.py — demo price generation tests
  test_verdict.py — buy/wait heuristic tests
```

## Guidelines

- Keep each module focused: `db.py` for storage, `pricing.py` for external calls, `server.py` for MCP tool logic.
- New tools go in `server.py` using the `@mcp.tool()` decorator.
- All data stays local — avoid adding any telemetry or external calls beyond the Kiwi API.
- Add or update tests for any changed logic.

## Submitting changes

1. Fork the repo and create a feature branch.
2. Make your changes with clear commit messages.
3. Open a pull request with a short description of what and why.

## Reporting issues

Open a GitHub issue — include your Python version, OS, and the error message if applicable.
