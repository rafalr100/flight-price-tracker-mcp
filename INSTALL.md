# Installation & setup

Step-by-step guide to run the Flight Price Tracker MCP server with Claude Desktop.

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **Claude Desktop** app (macOS or Windows)
- Optional: a free **Kiwi.com Tequila** API key for live prices (the server works in demo mode without it)

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
# Path to the Python interpreter inside the venv:
echo "$(pwd)/.venv/bin/python"

# Path to the server script:
echo "$(pwd)/src/server.py"
```

Copy both — you'll paste them in the next step.

## 5. Add to Claude Desktop config

Open the config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

If `mcpServers` already exists, add `flight-price-tracker` inside it. Otherwise create the whole structure:

```json
{
  "mcpServers": {
    "flight-price-tracker": {
      "command": "/Users/you/flight-price-tracker-mcp/.venv/bin/python",
      "args": ["/Users/you/flight-price-tracker-mcp/src/server.py"],
      "env": {
        "TEQUILA_API_KEY": ""
      }
    }
  }
}
```

Replace the two paths with what you copied in step 4. Leave `TEQUILA_API_KEY` empty for demo mode, or paste your key for live prices.

## 6. Restart Claude Desktop

Fully quit (not just close the window) and reopen. The tools appear under the connectors/tools menu. Look for `flight-price-tracker`.

## 7. Try it

Type to Claude:

```
Track a route from KRK to BCN, departing 2026-08-15, returning 2026-08-22, label it "Test".
```

Then:

```
Check the price for that route.
```

Run `check_price` a handful of times (it'll vary day to day even in demo mode), then:

```
Analyze the Test route — should I buy?
```

## Going live with real prices

1. Sign up at [tequila.kiwi.com](https://tequila.kiwi.com) and create a **Search API** solution.
2. Copy the API key.
3. Paste it into `TEQUILA_API_KEY` in the config (step 5).
4. Restart Claude Desktop.

The server auto-detects the key and switches from demo to live. Note that Kiwi expects IATA codes (e.g. `WAW`, `KRK`, `LON`, `BCN`).

## Automating the daily check (optional)

The smarter the verdict, the more snapshots you have — so it helps to check routes automatically. A small daily cron job that calls each route's `check_price` keeps the history growing without you lifting a finger. Ask Claude to generate a `check_all.py` + cron/launchd entry if you want this.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tools don't appear in Claude | Check the JSON is valid (no trailing commas), paths are absolute, then fully restart Claude |
| `spawn ... ENOENT` in logs | The `command` path to Python is wrong — re-run step 4 |
| `not enough data` verdict | You need at least 5 snapshots; run `check_price` more times |
| Live mode returns no flights | Verify IATA codes and that the date isn't in the past |

Claude Desktop logs are at:
- **macOS:** `~/Library/Logs/Claude/`
- **Windows:** `%APPDATA%\Claude\logs\`
