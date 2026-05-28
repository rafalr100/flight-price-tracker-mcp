# Flight Price Tracker MCP

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet.svg)](https://modelcontextprotocol.io)
[![API](https://img.shields.io/badge/data-Sky%20Scrapper%20%28RapidAPI%29-orange.svg)](https://rapidapi.com/apiheya/api/sky-scrapper)

> Track flight prices over time and learn **when to buy** — powered by real Skyscanner data via RapidAPI.

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets Claude track flight prices for routes you care about, build a price history automatically, and tell you whether today's price is a good deal or worth waiting on.

## Why this exists

Airlines don't give away day-by-day price history for free. But there's a simple trick: **save the price every time you check it.** After a few weeks you have your own dataset — enough to judge whether today's price is a good deal or worth waiting on.

It's like keeping your own price diary for a product you want. The shop won't tell you if a "sale" is real — but if you've tracked the price for a month, you know.

This MCP server does that journaling automatically and gives Claude the tools to analyze it. Everything is stored locally in SQLite — no data leaves your machine.

## Data source

Live prices come from the **[Sky Scrapper API](https://rapidapi.com/apiheya/api/sky-scrapper)** on RapidAPI — a Skyscanner data wrapper available to individual developers.

| Plan | Requests/month | Cost |
|------|---------------|------|
| BASIC (free) | 100 | $0 |
| PRO | 1,000 | ~$10 |

**100 requests/month is plenty for personal use** — airport lookups are cached locally so each check_price call costs exactly 1 request (2 only on first use of a new airport).

## Tools

| Tool | What it does |
|------|--------------|
| `add_route` | Register a route to track (from, to, dates) |
| `list_routes` | Show all tracked routes and their snapshot counts |
| `check_price` | Fetch the current cheapest price and save a snapshot |
| `price_history` | Return the full saved price history for a route |
| `analyze_route` | Compute min/max/avg, percentile, trend and a buy/wait verdict |

## How the verdict works

A fully transparent heuristic — no black box:

| Verdict | Condition |
|---------|-----------|
| **BUY — lowest ever** | current price ≤ all-time minimum |
| **BUY — good deal** | cheaper than 70% of past readings |
| **WAIT — expensive** | pricier than 70% of past readings |
| **NEUTRAL** | around the average |
| **not enough data** | fewer than 5 snapshots — keep checking |

The more often you check a route, the smarter the recommendation.

## Architecture

```
Claude  ──►  Flight Tracker MCP  ──►  Sky Scrapper API / RapidAPI
                    │                   (live prices, Skyscanner data)
                    ▼
              SQLite (local)
           routes + snapshots
           + airport cache
```

## Quick start

```bash
git clone https://github.com/rafalr100/flight-price-tracker-mcp.git
cd flight-price-tracker-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then add it to your Claude Desktop config — see [INSTALL.md](INSTALL.md) for full instructions.

```json
{
  "mcpServers": {
    "flight-price-tracker": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/src/server.py"],
      "env": {
        "SKY_SCRAPPER_API_KEY": "YOUR_RAPIDAPI_KEY"
      }
    }
  }
}
```

Get your free key at [rapidapi.com/apiheya/api/sky-scrapper](https://rapidapi.com/apiheya/api/sky-scrapper) — subscribe to the **BASIC** (free) plan.

**Without a key the server runs in demo mode**, generating realistic prices so you can test the full flow before connecting real data.

## Demo mode

With no API key set, the server generates plausible prices — deterministic per route, with a daily wander — so you can walk the whole loop (`add_route` → `check_price` a few times → `analyze_route`) and watch the history build before connecting a real data source.

## Example conversation

> **You:** Track Kraków → Barcelona, departing 15 Aug, returning 22 Aug, call it "Holiday".
> **Claude:** *(add_route)* Added route #1 "Holiday": KRK → BCN…
>
> **You:** Check the price.
> **Claude:** *(check_price)* Current cheapest: 1,240 PLN (Ryanair). Snapshot saved…
>
> *(after a few weeks of regular checks)*
>
> **You:** Should I buy the Holiday tickets now?
> **Claude:** *(analyze_route)* At 1,090 PLN this is cheaper than 80% of past readings. **BUY — good deal.**

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE).
