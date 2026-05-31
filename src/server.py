"""
Flight Price Tracker MCP Server

A Model Context Protocol server that tracks flight prices over time and helps you
decide when to buy. It does NOT rely on any paid "price history" API — instead it
builds your own history by saving a snapshot of the price every time you check a
route. After a few weeks of checking, you have a personal dataset that the analysis
tools use to tell you whether the current price is good ("buy now") or likely to
drop ("wait").

Tools exposed:
  - add_route          Register a route you want to track (origin, destination, dates)
  - list_routes        Show all tracked routes
  - check_price        Fetch the current cheapest price for a route and save a snapshot
  - price_history      Return all saved snapshots for a route
  - analyze_route      Compute trend, min/max/avg/percentile and a buy/wait verdict

Price data source:
  By default the server uses the Sky Scrapper API (Skyscanner data) on RapidAPI. Set
  SKY_SCRAPPER_API_KEY to enable live lookups. Without a key, check_price runs in DEMO
  mode and generates a plausible price so you can try the full flow end-to-end before
  wiring real data.
"""

from __future__ import annotations

import os
import statistics
from datetime import datetime, date, timedelta

from mcp.server.fastmcp import FastMCP

from db import (
    init_db,
    upsert_route,
    get_routes,
    get_route_by_id,
    insert_snapshot,
    get_snapshots,
)
from pricing import fetch_cheapest_price, PriceResult, DEMO_MODE

mcp = FastMCP("flight-price-tracker")

# Make sure the local database exists as soon as the server starts.
init_db()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _fmt_price(value: float, currency: str) -> str:
    return f"{value:,.0f} {currency}"


def _verdict(current: float, history: list[float]) -> tuple[str, str]:
    """
    Return a (label, explanation) tuple judging the current price against history.
    Pure heuristic — transparent and explainable, no black box.
    """
    n = len(history)
    if n < 5:
        return (
            "not enough data",
            f"I only have {n} saved prices for this route. "
            f"I need at least 5 to judge whether the price is good. "
            f"Check the route regularly — every check builds up the history.",
        )

    avg = statistics.mean(history)
    lo = min(history)
    hi = max(history)
    # Percentile of the current price within history (0 = cheapest seen, 100 = most expensive).
    below = sum(1 for p in history if p > current)
    percentile = round(100 * below / n)
    delta_pct = round(100 * (current - avg) / avg, 1)

    if current <= lo:
        return (
            "BUY — lowest price on record",
            f"The current price {current:,.0f} is the lowest I've seen "
            f"(previous minimum: {lo:,.0f}). That's {abs(delta_pct)}% below the average.",
        )
    if percentile >= 70:
        return (
            "BUY — good deal",
            f"The price is cheaper than {percentile}% of earlier quotes "
            f"({delta_pct}% vs the average of {avg:,.0f}). Good moment.",
        )
    if percentile <= 30:
        return (
            "WAIT — expensive",
            f"The price is more expensive than {100 - percentile}% of earlier quotes "
            f"(+{delta_pct}% vs the average). It will likely drop.",
        )
    return (
        "NEUTRAL",
        f"The price is around the average ({delta_pct:+}% from {avg:,.0f}). "
        f"No clear signal — you can wait for a better deal or buy if the dates suit you.",
    )


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def add_route(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str = "",
    label: str = "",
) -> str:
    """
    Register a flight route to track.

    Args:
        origin: IATA airport/city code, e.g. "WAW", "KRK".
        destination: IATA airport/city code, e.g. "LON", "BCN".
        depart_date: Departure date in YYYY-MM-DD.
        return_date: Optional return date YYYY-MM-DD for round trips (empty = one-way).
        label: Optional friendly name, e.g. "Spain holiday".

    Returns a confirmation with the new route id.
    """
    origin = origin.strip().upper()
    destination = destination.strip().upper()
    try:
        datetime.strptime(depart_date, "%Y-%m-%d")
        if return_date:
            datetime.strptime(return_date, "%Y-%m-%d")
    except ValueError:
        return "Error: dates must be in YYYY-MM-DD format (e.g. 2026-08-15)."

    route_id = upsert_route(origin, destination, depart_date, return_date, label)
    trip = "round trip" if return_date else "one-way"
    name = f' "{label}"' if label else ""
    return (
        f"Added route #{route_id}{name}: {origin} → {destination}, "
        f"departing {depart_date}{(', returning ' + return_date) if return_date else ''} ({trip}). "
        f"Use check_price to save the first quote."
    )


@mcp.tool()
def list_routes() -> str:
    """List all tracked routes with how many price snapshots each has."""
    routes = get_routes()
    if not routes:
        return "No tracked routes yet. Add your first one with add_route."

    lines = ["Tracked routes:\n"]
    for r in routes:
        snaps = get_snapshots(r["id"])
        last = ""
        if snaps:
            latest = snaps[-1]
            last = f" · last price {latest['price']:,.0f} {latest['currency']} ({latest['checked_at'][:10]})"
        label = f' "{r["label"]}"' if r["label"] else ""
        trip = f", returning {r['return_date']}" if r["return_date"] else ""
        lines.append(
            f"#{r['id']}{label}: {r['origin']} → {r['destination']}, "
            f"departing {r['depart_date']}{trip} — {len(snaps)} snapshots{last}"
        )
    return "\n".join(lines)


@mcp.tool()
def check_price(route_id: int) -> str:
    """
    Fetch the current cheapest price for a tracked route and save a snapshot
    to the local history. Run this regularly (or on a schedule) to build up data.

    Args:
        route_id: The id returned by add_route / shown in list_routes.
    """
    route = get_route_by_id(route_id)
    if not route:
        return f"Route #{route_id} not found. Check list_routes."

    result: PriceResult = fetch_cheapest_price(
        origin=route["origin"],
        destination=route["destination"],
        depart_date=route["depart_date"],
        return_date=route["return_date"] or None,
    )
    if result.error:
        return f"Could not fetch the price: {result.error}"

    insert_snapshot(route_id, result.price, result.currency, result.carrier)

    history = [s["price"] for s in get_snapshots(route_id)]
    mode_note = " (DEMO mode — set SKY_SCRAPPER_API_KEY for live prices)" if DEMO_MODE else ""
    msg = [
        f"Route #{route_id} {route['origin']} → {route['destination']}{mode_note}",
        f"Current cheapest price: {_fmt_price(result.price, result.currency)}"
        + (f" ({result.carrier})" if result.carrier else ""),
        f"Snapshot saved. Total snapshots: {len(history)}.",
    ]
    if len(history) >= 5:
        label, _ = _verdict(result.price, history[:-1] if len(history) > 1 else history)
        msg.append(f"Preliminary verdict: {label} — run analyze_route for details.")
    return "\n".join(msg)


@mcp.tool()
def price_history(route_id: int) -> str:
    """
    Return the full saved price history for a route as a chronological list.

    Args:
        route_id: The route id.
    """
    route = get_route_by_id(route_id)
    if not route:
        return f"Route #{route_id} not found."
    snaps = get_snapshots(route_id)
    if not snaps:
        return f"Route #{route_id} has no snapshots yet. Use check_price."

    lines = [f"Price history for route #{route_id} ({route['origin']} → {route['destination']}):\n"]
    for s in snaps:
        carrier = f" · {s['carrier']}" if s["carrier"] else ""
        lines.append(f"{s['checked_at'][:16]}  {s['price']:,.0f} {s['currency']}{carrier}")
    return "\n".join(lines)


@mcp.tool()
def analyze_route(route_id: int) -> str:
    """
    Analyze the saved price history for a route: min, max, average, current price,
    its percentile within history, the recent trend, and a transparent buy/wait verdict.

    Args:
        route_id: The route id.
    """
    route = get_route_by_id(route_id)
    if not route:
        return f"Route #{route_id} not found."
    snaps = get_snapshots(route_id)
    if not snaps:
        return f"Route #{route_id} has no data yet. Use check_price a few times."

    prices = [s["price"] for s in snaps]
    currency = snaps[-1]["currency"]
    current = prices[-1]
    avg = statistics.mean(prices)

    # Recent trend: compare last third vs first third of the history.
    trend = "stable"
    if len(prices) >= 6:
        third = len(prices) // 3
        early = statistics.mean(prices[:third])
        late = statistics.mean(prices[-third:])
        diff = round(100 * (late - early) / early, 1)
        if diff > 3:
            trend = f"rising (+{diff}% over the observation window)"
        elif diff < -3:
            trend = f"falling ({diff}% over the observation window)"

    label, explanation = _verdict(current, prices)

    days_to_departure = ""
    try:
        d = datetime.strptime(route["depart_date"], "%Y-%m-%d").date()
        delta = (d - date.today()).days
        days_to_departure = f"\nDays to departure: {delta}"
    except ValueError:
        pass

    return "\n".join([
        f"Analysis of route #{route_id}: {route['origin']} → {route['destination']}"
        + (f' "{route["label"]}"' if route["label"] else ""),
        f"Snapshots: {len(prices)}",
        f"Current price: {current:,.0f} {currency}",
        f"Lowest / highest: {min(prices):,.0f} / {max(prices):,.0f} {currency}",
        f"Average: {avg:,.0f} {currency}",
        f"Trend: {trend}" + days_to_departure,
        "",
        f"Verdict: {label}",
        explanation,
    ])


if __name__ == "__main__":
    mcp.run()
