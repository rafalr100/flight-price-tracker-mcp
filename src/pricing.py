"""
Price-fetching layer for the Flight Price Tracker MCP server.

Live mode:
    Uses the Kiwi.com Tequila search API (https://tequila.kiwi.com). Set the
    environment variable TEQUILA_API_KEY to your API key to enable it. Kiwi's
    Tequila program has a free tier for personal/affiliate use.

Demo mode:
    If no key is set, the server falls back to a deterministic pseudo-random
    price so you can exercise the whole add_route -> check_price -> analyze flow
    without any credentials. Demo prices wander realistically around a base value
    that depends on the route, so the history actually looks like a price curve.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import urllib.parse
import urllib.request
import json
from dataclasses import dataclass
from datetime import datetime

TEQUILA_API_KEY = os.environ.get("TEQUILA_API_KEY", "").strip()
DEMO_MODE = not bool(TEQUILA_API_KEY)
TEQUILA_URL = "https://api.tequila.kiwi.com/v2/search"


@dataclass
class PriceResult:
    price: float = 0.0
    currency: str = "PLN"
    carrier: str = ""
    error: str = ""


def _to_kiwi_date(iso_date: str) -> str:
    """Kiwi wants dd/mm/yyyy."""
    d = datetime.strptime(iso_date, "%Y-%m-%d")
    return d.strftime("%d/%m/%Y")


def _fetch_live(origin, destination, depart_date, return_date) -> PriceResult:
    params = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": _to_kiwi_date(depart_date),
        "date_to": _to_kiwi_date(depart_date),
        "curr": "PLN",
        "limit": 1,
        "sort": "price",
        "one_for_city": 0,
    }
    if return_date:
        params["return_from"] = _to_kiwi_date(return_date)
        params["return_to"] = _to_kiwi_date(return_date)

    url = TEQUILA_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"apikey": TEQUILA_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return PriceResult(error=f"Kiwi API HTTP {e.code} — sprawdź klucz i kody lotnisk.")
    except Exception as e:  # noqa: BLE001
        return PriceResult(error=f"Błąd połączenia z Kiwi API: {e}")

    flights = data.get("data", [])
    if not flights:
        return PriceResult(error="Kiwi nie zwrócił żadnych lotów dla tej trasy/daty.")
    top = flights[0]
    carriers = top.get("airlines", [])
    return PriceResult(
        price=float(top["price"]),
        currency=data.get("currency", "PLN"),
        carrier=", ".join(carriers[:2]),
    )


def _fetch_demo(origin, destination, depart_date, return_date) -> PriceResult:
    """
    Deterministic-ish demo price. Base price is derived from the route so each
    route has a stable 'character', then we add daily wander + a sinusoidal
    seasonal-ish component + noise so the saved history looks like a real curve.
    """
    seed_src = f"{origin}{destination}{depart_date}{return_date}".encode()
    base_seed = int(hashlib.sha256(seed_src).hexdigest(), 16) % 10_000
    base = 350 + (base_seed % 1400)  # 350–1750 PLN base
    if return_date:
        base *= 1.8  # round trips cost more

    # Wander by the current day so repeated checks over days differ.
    day_ordinal = datetime.utcnow().toordinal()
    rng = random.Random(base_seed + day_ordinal)
    seasonal = math.sin(day_ordinal / 9.0) * (base * 0.08)
    noise = rng.uniform(-0.06, 0.06) * base
    price = max(99, round(base + seasonal + noise, -1))  # round to nearest 10
    return PriceResult(price=float(price), currency="PLN", carrier="DEMO Air")


def fetch_cheapest_price(origin, destination, depart_date, return_date=None) -> PriceResult:
    """Public entry point. Picks live or demo mode automatically."""
    return_date = return_date or ""
    if DEMO_MODE:
        return _fetch_demo(origin, destination, depart_date, return_date)
    return _fetch_live(origin, destination, depart_date, return_date)
