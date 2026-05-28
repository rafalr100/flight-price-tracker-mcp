"""Unit tests for the SQLite storage layer."""
import sys, os, tempfile, pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect every test to a fresh temporary database."""
    import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_upsert_route_creates_row():
    import db
    rid = db.upsert_route("WAW", "BCN", "2026-08-01", "", "Test")
    assert rid == 1
    routes = db.get_routes()
    assert len(routes) == 1
    assert routes[0]["origin"] == "WAW"


def test_upsert_route_idempotent():
    import db
    r1 = db.upsert_route("WAW", "BCN", "2026-08-01", "", "")
    r2 = db.upsert_route("WAW", "BCN", "2026-08-01", "", "")
    assert r1 == r2
    assert len(db.get_routes()) == 1


def test_insert_and_get_snapshots():
    import db
    rid = db.upsert_route("KRK", "LON", "2026-09-10", "", "")
    db.insert_snapshot(rid, 850.0, "PLN", "Ryanair")
    db.insert_snapshot(rid, 790.0, "PLN", "Wizz")
    snaps = db.get_snapshots(rid)
    assert len(snaps) == 2
    assert snaps[0]["price"] == 850.0
    assert snaps[1]["carrier"] == "Wizz"


def test_get_route_by_id():
    import db
    rid = db.upsert_route("GDN", "MAD", "2026-07-20", "2026-07-27", "Madrid")
    route = db.get_route_by_id(rid)
    assert route["destination"] == "MAD"
    assert route["label"] == "Madrid"
    assert db.get_route_by_id(9999) is None
