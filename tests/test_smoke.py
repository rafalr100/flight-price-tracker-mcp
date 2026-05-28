"""Smoke tests — verify the server imports cleanly and all tools are registered."""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_imports():
    import db       # noqa: F401
    import pricing  # noqa: F401
    import server   # noqa: F401


def test_tools_registered():
    import server
    tools = server.mcp._tool_manager.list_tools()
    names = {t.name for t in tools}
    expected = {"add_route", "list_routes", "check_price", "price_history", "analyze_route"}
    assert expected == names, f"Unexpected tools: {names}"


def test_demo_mode_active_without_key(monkeypatch):
    monkeypatch.delenv("SKY_SCRAPPER_API_KEY", raising=False)
    import importlib, pricing
    importlib.reload(pricing)
    assert pricing.DEMO_MODE is True
