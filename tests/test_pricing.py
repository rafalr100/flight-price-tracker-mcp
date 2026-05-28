"""Tests for the pricing / demo-mode layer."""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_demo_returns_price():
    from pricing import _fetch_demo
    result = _fetch_demo("KRK", "BCN", "2026-08-15", "2026-08-22")
    assert result.error == ""
    assert result.price > 0
    assert result.currency == "PLN"


def test_demo_price_is_stable_within_day():
    """Same inputs on the same UTC day → same price."""
    from pricing import _fetch_demo
    r1 = _fetch_demo("WAW", "LON", "2026-10-01", "")
    r2 = _fetch_demo("WAW", "LON", "2026-10-01", "")
    assert r1.price == r2.price


def test_demo_roundtrip_costs_more():
    from pricing import _fetch_demo
    one_way = _fetch_demo("KRK", "BCN", "2026-08-15", "")
    roundtrip = _fetch_demo("KRK", "BCN", "2026-08-15", "2026-08-22")
    assert roundtrip.price > one_way.price
