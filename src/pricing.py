"""
Price-fetching layer for the Flight Price Tracker MCP server.

Live mode  (SKY_SCRAPPER_API_KEY set):
    Uses the Sky Scrapper API on RapidAPI (rapidapi.com/apiheya/api/sky-scrapper).
    Free tier: 100 requests/month.
    Strategy to stay within the limit:
      - IATA → Skyscanner skyId/entityId lookups are cached locally in SQLite.
        Once resolved, an airport is never looked up again → saves 1 request per check.
      - Each check_price call costs 1 API request (2 on first use of a new airport).

Demo mode  (no key):
    Deterministic pseudo-random prices — no network calls, no quota consumed.
    Safe for testing the full add_route → check_price → analyze_route flow.

Environment variables:
    SKY_SCRAPPER_API_KEY   RapidAPI key subscribed to Sky Scrapper (apiheya)
    RAPIDAPI_HOST          Override host (default: sky-scrapper.p.rapidapi.com)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from db import get_airport, put_airport

SKY_SCRAPPER_API_KEY = os.environ.get("SKY_SCRAPPER_API_KEY", "").strip()
DEMO_MODE = not bool(SKY_SCRAPPER_API_KEY)
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "sky-scrapper.p.rapidapi.com")

_BASE = f"https://{RAPIDAPI_HOST}/api/v1"
_HEADERS = {
    "X-RapidAPI-Key": SKY_SCRAPPER_API_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
}


@dataclass
class PriceResult:
    price: float = 0.0
    currency: str = "PLN"
    carrier: str = ""
    error: str = ""


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, params: dict) -> dict:
    full_url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full_url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _resolve_airport(iata: str) -> tuple[str, str]:
    """
    Return (skyId, entityId) for an IATA code.
    Checks local cache first — only calls the API on first use.
    Costs 1 API request if not cached, 0 if cached.
    """
    cached = get_airport(iata)
    if cached:
        return cached["sky_id"], cached["entity_id"]

    # searchAirport endpoint — finds the Skyscanner IDs for a given query
    data = _get(f"{_BASE}/flights/searchAirport", {"query": iata, "locale": "en-US"})
    airports = data.get("data", [])
    if not airports:
        raise RuntimeError(
            f"Airport '{iata}' not found in Skyscanner. "
            "Check the IATA code — try the full name if the code is unusual."
        )

    # Prefer exact IATA match; fall back to first result
    match = next(
        (a for a in airports if a.get("iata", "").upper() == iata.upper()),
        airports[0],
    )
    sky_id = match.get("skyId", "")
    entity_id = match.get("entityId", "")
    name = match.get("presentation", {}).get("title", "")

    if not sky_id or not entity_id:
        raise RuntimeError(f"Skyscanner returned incomplete data for '{iata}'.")

    put_airport(iata, sky_id, entity_id, name)
    return sky_id, entity_id


# ── live mode ─────────────────────────────────────────────────────────────────

def _fetch_live(origin: str, destination: str, depart_date: str,
                return_date: str) -> PriceResult:
    try:
        origin_sky_id, origin_entity_id = _resolve_airport(origin)
        dest_sky_id, dest_entity_id = _resolve_airport(destination)
    except RuntimeError as e:
        return PriceResult(error=str(e))

    params = {
        "originSkyId": origin_sky_id,
        "destinationSkyId": dest_sky_id,
        "originEntityId": origin_entity_id,
        "destinationEntityId": dest_entity_id,
        "date": depart_date,
        "adults": 1,
        "currency": "PLN",
        "countryCode": "PL",
        "market": "pl-PL",
        "cabinClass": "economy",
        "limit": 5,
    }
    if return_date:
        params["returnDate"] = return_date

    try:
        data = _get(f"{_BASE}/flights/searchFlights", params)
    except RuntimeError as e:
        return PriceResult(error=f"Sky Scrapper search failed: {e}")

    if not data.get("status"):
        msg = data.get("message", "unknown error")
        return PriceResult(error=f"Sky Scrapper returned status=false: {msg}")

    itineraries = data.get("data", {}).get("itineraries", [])
    if not itineraries:
        return PriceResult(
            error="No flights found for this route/date. "
                  "Try a date further in the future or verify the airport codes."
        )

    # First itinerary is cheapest (API returns sorted by price)
    top = itineraries[0]
    price_info = top.get("price", {})
    raw_price = price_info.get("raw", 0.0)
    currency = "PLN"

    legs = top.get("legs", [])
    carriers: list[str] = []
    for leg in legs:
        for carrier in leg.get("carriers", {}).get("marketing", []):
            name = carrier.get("name", "")
            if name and name not in carriers:
                carriers.append(name)

    return PriceResult(
        price=float(raw_price),
        currency=currency,
        carrier=", ".join(carriers[:2]),
    )


# ── demo mode ─────────────────────────────────────────────────────────────────

def _fetch_demo(origin: str, destination: str, depart_date: str,
                return_date: str) -> PriceResult:
    """
    Deterministic pseudo-random price.
    Seed based on route only so one-way and round-trip are comparable.
    Round-trips always cost more than one-way for the same route.
    """
    seed_src = f"{origin}{destination}".encode()
    base_seed = int(hashlib.sha256(seed_src).hexdigest(), 16) % 10_000
    base = 350 + (base_seed % 1400)  # 350–1750 PLN one-way base

    day_ordinal = datetime.now(timezone.utc).toordinal()
    rng = random.Random(base_seed + day_ordinal)
    seasonal = math.sin(day_ordinal / 9.0) * (base * 0.08)
    noise = rng.uniform(-0.06, 0.06) * base
    one_way_price = max(99, round(base + seasonal + noise, -1))

    price = one_way_price * 1.8 if return_date else one_way_price
    return PriceResult(price=float(price), currency="PLN", carrier="DEMO Air")


# ── public entry point ────────────────────────────────────────────────────────

def fetch_cheapest_price(origin: str, destination: str,
                         depart_date: str, return_date: str | None = None) -> PriceResult:
    """Fetch cheapest price. Uses live API if key is set, demo mode otherwise."""
    return_date = return_date or ""
    if DEMO_MODE:
        return _fetch_demo(origin, destination, depart_date, return_date)
    return _fetch_live(origin, destination, depart_date, return_date)
