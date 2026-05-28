# Installation & setup

Step-by-step guide to run the Flight Price Tracker MCP server with Claude Desktop.

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **Claude Desktop** app (macOS or Windows)
- Optional: a free **RapidAPI key** for live prices (the server works in demo mode without it)

## 1. Get the code

```bash
git clone https://github.com/rafalr100/flight-price-tracker-mcp.git
cd flight-price-tracker-mcp
```

(Or download the ZIP and unpack it somewhere permanent — not your Downloads folder, since the database lives next to the code.)

## 2. Create a virtual environment and install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows use `.venv\Scripts\pip` instead of `.venv/bin/pip`.

## 3. Test it works (demo mode, no API key needed)

```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import server; print('OK -', len(server.mcp._tool_manager.list_tools()), 'tools registered')"
```

You should see `OK - 5 tools registered`.

## 4. Find your absolute paths

The Claude config needs full absolute paths, not relative ones.

```bash
echo "$(pwd)/.venv/bin/python"   # Python interpreter
echo "$(pwd)/src/server.py"      # Server script
```

Copy both — you'll paste them in the next step.

## 5. Add to Claude Desktop config

Open the config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "flight-price-tracker": {
      "command": "/Users/you/flight-price-tracker-mcp/.venv/bin/python",
      "args": ["/Users/you/flight-price-tracker-mcp/src/server.py"],
      "env": {
        "SKY_SCRAPPER_API_KEY": ""
      }
    }
  }
}
```

Replace the two paths with what you copied in step 4. Leave `SKY_SCRAPPER_API_KEY` empty for demo mode, or paste your key for live prices.

## 6. Restart Claude Desktop

Fully quit (not just close the window) and reopen. Look for `flight-price-tracker` in the tools menu.

## 7. Try it

```
Track a route from KRK to BCN, departing 2026-08-15, returning 2026-08-22, label it "Test".
```

Then: `Check the price for that route.`

## Getting a live API key (free)

1. Go to [rapidapi.com/apiheya/api/sky-scrapper](https://rapidapi.com/apiheya/api/sky-scrapper)
2. Sign in or create a free RapidAPI account
3. Click **Subscribe to Test** → select the **BASIC** plan (free, 100 requests/month)
4. Copy your `X-RapidAPI-Key` from the code snippets panel
5. Paste it into `SKY_SCRAPPER_API_KEY` in your Claude config (step 5)
6. Restart Claude Desktop

### Request budget

| Action | API requests used |
|--------|-----------------|
| `check_price` (new airport) | 2 (lookup + search) |
| `check_price` (known airport) | 1 (search only) |
| `add_route`, `list_routes`, `analyze_route` | 0 |

Airport lookups are cached locally in SQLite — each airport is looked up **once ever**, so after the first check of a route all subsequent checks cost just 1 request.

**Example:** 3 routes checked daily = ~90 requests/month → comfortably within the free 100 limit.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tools don't appear in Claude | Check JSON validity (no trailing commas), paths are absolute, fully restart Claude |
| `spawn ... ENOENT` in logs | The `command` path to Python is wrong — re-run step 4 |
| `not enough data` verdict | Need at least 5 snapshots; run `check_price` more times |
| Live mode: no flights found | Verify IATA codes are correct and date is in the future |
| Live mode: HTTP 429 | Monthly request limit reached; wait for next billing cycle or upgrade plan |

Claude Desktop logs:
- **macOS:** `~/Library/Logs/Claude/`
- **Windows:** `%APPDATA%\Claude\logs\`
