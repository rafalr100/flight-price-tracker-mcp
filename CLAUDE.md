# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Create virtualenv and install runtime deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Install dev deps
.venv/bin/pip install -r requirements-dev.txt

# Run all tests
.venv/bin/pytest tests/ -v

# Run a single test
.venv/bin/pytest tests/test_db.py::test_upsert_route_creates_row -v

# Start the MCP server (connects via stdio; used by Claude Desktop)
.venv/bin/python src/server.py
```

There is no linter configured.

## Architecture

This is a Python **MCP (Model Context Protocol) server** using Anthropic's `mcp[cli]` package (`FastMCP`). It exposes 5 tools to a connected Claude client (e.g. Claude Desktop) that track flight prices over time and recommend buy/wait decisions.

```
Claude Desktop ──stdio/JSON-RPC──► server.py (FastMCP)
                                        │
                          ┌─────────────┴─────────────┐
                          ▼                            ▼
                     pricing.py                      db.py
              (Sky Scrapper API / demo)         (SQLite flights.db)
```

**Three source modules (`src/`):**

- **`server.py`** — Entry point. Instantiates `FastMCP`, calls `init_db()` at import time, registers all 5 tools with `@mcp.tool()`, and contains the `_verdict()` heuristic. `mcp.run()` is called under `__main__`.
- **`db.py`** — SQLite persistence. Three tables: `routes`, `snapshots`, `airport_cache`. DB path is controlled by the `FLIGHT_DB_PATH` env var (default: `flights.db` in the project root).
- **`pricing.py`** — Price fetching abstraction. Contains `PriceResult` dataclass and `fetch_cheapest_price()`. Operates in **demo mode** (deterministic seeded random prices) when `SKY_SCRAPPER_API_KEY` is unset, enabling full-flow testing without an API key.

## Key Conventions

**Tool registration:** All tools use the `@mcp.tool()` decorator. The function docstring becomes the tool description shown to Claude. All tools return `str` (human-readable text, never JSON).

```python
@mcp.tool()
def my_tool(required_arg: str, optional_arg: str = "") -> str:
    """Docstring is what Claude sees as the tool description."""
    return "human-readable result"
```

**Error handling:** `pricing.py` returns `PriceResult` with an `.error` field; tools check this field and return a user-friendly error string rather than raising.

**Demo mode:** `pricing.py` sets `DEMO_MODE = not bool(os.getenv("SKY_SCRAPPER_API_KEY"))`. Demo prices are seeded per (route, date) so they are stable within a day. Tests rely on demo mode — no API key is needed.

**The verdict heuristic** (`_verdict()` in `server.py`): requires ≥5 snapshots, then classifies current price by percentile against history — bottom 30% → BUY, top 30% → WAIT, else NEUTRAL.

## Testing Patterns

- Tests use a `tmp_db` pytest fixture (defined per test file) that sets `db.DB_PATH` to a `tmp_path` file, isolating each test's SQLite state.
- Tests import from `src/` via `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))`.
- No external mocking frameworks — real SQLite and real demo pricing; only env vars and module attributes are patched with `monkeypatch`.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SKY_SCRAPPER_API_KEY` | _(unset)_ | RapidAPI key; unset = demo mode |
| `RAPIDAPI_HOST` | `sky-scrapper.p.rapidapi.com` | Override API host |
| `FLIGHT_DB_PATH` | `flights.db` (project root) | SQLite database location |
