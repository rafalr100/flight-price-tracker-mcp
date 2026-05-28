"""Tests for the airport cache layer in db.py."""
import sys, os, pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_get_airport_miss():
    import db
    assert db.get_airport("KRK") is None


def test_put_and_get_airport():
    import db
    db.put_airport("KRK", "KRK", "95673370", "Kraków John Paul II")
    result = db.get_airport("KRK")
    assert result is not None
    assert result["sky_id"] == "KRK"
    assert result["entity_id"] == "95673370"
    assert result["name"] == "Kraków John Paul II"


def test_put_airport_upsert():
    import db
    db.put_airport("WAW", "WAW", "old-entity", "Warsaw old")
    db.put_airport("WAW", "WAW", "new-entity", "Warsaw Chopin")
    result = db.get_airport("WAW")
    assert result["entity_id"] == "new-entity"
    assert result["name"] == "Warsaw Chopin"


def test_iata_case_insensitive():
    import db
    db.put_airport("krk", "KRK", "95673370", "Kraków")
    assert db.get_airport("KRK") is not None
    assert db.get_airport("krk") is not None
