"""
tests/test_database.py — ANTARA Project
=======================================
Unit test untuk DatabaseManager. Setiap test pakai DB file sementara
agar tidak menyentuh data/antara.db production.
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import DatabaseManager


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    """DatabaseManager dengan file DB di temp dir per-test."""
    db_path = tmp_path / "test_antara.db"
    return DatabaseManager(db_path=str(db_path))


# ─────────────────────────────────────────────────────────────────────────────
#  Initialization
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_init_creates_db_file(self, tmp_path):
        db_path = tmp_path / "x.db"
        assert not db_path.exists()
        DatabaseManager(db_path=str(db_path))
        assert db_path.exists()

    def test_repr(self, db):
        assert "DatabaseManager" in repr(db)
        assert "db_path" in repr(db)


# ─────────────────────────────────────────────────────────────────────────────
#  Search History
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchHistory:
    def test_save_and_retrieve(self, db):
        row_id = db.save_search_result(
            origin="Jakarta", destination="Surabaya",
            date="2026-05-15", passengers=2,
            best_route_combo={"route": "Jakarta → Surabaya"},
            total_options=10,
        )
        assert row_id > 0
        history = db.get_search_history()
        assert len(history) == 1
        assert history[0]["origin"] == "Jakarta"
        assert history[0]["destination"] == "Surabaya"
        assert history[0]["passengers"] == 2
        assert history[0]["total_options"] == 10

    def test_history_ordering_desc(self, db):
        db.save_search_result("Jakarta", "Surabaya", "2026-05-15", 1, {}, 1)
        # SQLite CURRENT_TIMESTAMP resolusi 1 detik — beri jeda agar urutan jelas
        time.sleep(1.1)
        db.save_search_result("Bandung", "Yogyakarta", "2026-05-16", 1, {}, 2)
        history = db.get_search_history()
        # Terbaru dulu
        assert history[0]["origin"] == "Bandung"
        assert history[1]["origin"] == "Jakarta"

    def test_limit_respected(self, db):
        for i in range(5):
            db.save_search_result(f"City{i}", "Surabaya", "2026-05-15", 1, {}, 1)
        assert len(db.get_search_history(limit=3)) == 3

    def test_legacy_aliases_work(self, db):
        """save_result / get_history harus tetap jalan untuk kode lama."""
        db.save_result("Jakarta", "Surabaya", "2026-05-15", {"foo": "bar"})
        assert len(db.get_history()) == 1

    def test_clear_history(self, db):
        db.save_search_result("A", "B", "2026-05-15", 1, {}, 1)
        db.save_search_result("C", "D", "2026-05-16", 1, {}, 1)
        n = db.clear_search_history()
        assert n == 2
        assert db.get_search_history() == []


# ─────────────────────────────────────────────────────────────────────────────
#  User Preferences
# ─────────────────────────────────────────────────────────────────────────────

class TestUserPreferences:
    def test_set_and_get_basic_types(self, db):
        db.set_preference("dark_mode", True)
        db.set_preference("max_results", 25)
        db.set_preference("language", "Indonesian")
        assert db.get_preference("dark_mode") is True
        assert db.get_preference("max_results") == 25
        assert db.get_preference("language") == "Indonesian"

    def test_get_nonexistent_returns_default(self, db):
        assert db.get_preference("missing") is None
        assert db.get_preference("missing", default="fallback") == "fallback"

    def test_set_overrides_existing(self, db):
        db.set_preference("key", "first")
        db.set_preference("key", "second")
        assert db.get_preference("key") == "second"

    def test_get_all_preferences(self, db):
        db.set_preference("a", 1)
        db.set_preference("b", "x")
        db.set_preference("c", [1, 2, 3])
        prefs = db.get_all_preferences()
        assert prefs == {"a": 1, "b": "x", "c": [1, 2, 3]}

    def test_complex_value_round_trip(self, db):
        complex_val = {"nested": {"list": [1, 2], "bool": True}}
        db.set_preference("complex", complex_val)
        assert db.get_preference("complex") == complex_val


# ─────────────────────────────────────────────────────────────────────────────
#  Price Cache
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceCache:
    def test_cache_and_retrieve(self, db):
        segments = [
            {"id": "S1", "provider": "Argo Bromo", "price": 350_000},
            {"id": "S2", "provider": "Gajayana",   "price": 320_000},
        ]
        db.cache_segments("Jakarta", "Surabaya", "2026-05-15", "train", segments)
        cached = db.get_cached_segments("Jakarta", "Surabaya", "2026-05-15", "train")
        assert cached == segments

    def test_cache_miss_returns_none(self, db):
        result = db.get_cached_segments("X", "Y", "2026-05-15", "train")
        assert result is None

    def test_cache_ttl_zero_means_expired(self, db):
        """max_age_minutes=0 berarti cache dianggap kadaluwarsa segera."""
        db.cache_segments("Jakarta", "Surabaya", "2026-05-15", "train", [{"id": "S1"}])
        # Tunggu 1.1 detik agar selisih waktu > 0 detik
        time.sleep(1.1)
        cached = db.get_cached_segments("Jakarta", "Surabaya", "2026-05-15",
                                        "train", max_age_minutes=0)
        assert cached is None

    def test_cache_fresh_within_ttl(self, db):
        db.cache_segments("Jakarta", "Surabaya", "2026-05-15", "train", [{"id": "S1"}])
        cached = db.get_cached_segments("Jakarta", "Surabaya", "2026-05-15",
                                        "train", max_age_minutes=60)
        assert cached is not None

    def test_cache_overwrite_same_key(self, db):
        db.cache_segments("Jakarta", "Surabaya", "2026-05-15", "train", [{"v": 1}])
        db.cache_segments("Jakarta", "Surabaya", "2026-05-15", "train", [{"v": 2}])
        cached = db.get_cached_segments("Jakarta", "Surabaya", "2026-05-15", "train")
        assert cached == [{"v": 2}]

    def test_clear_price_cache(self, db):
        db.cache_segments("A", "B", "2026-05-15", "train", [{"id": "S1"}])
        db.cache_segments("C", "D", "2026-05-15", "flight", [{"id": "S2"}])
        n = db.clear_price_cache()
        assert n == 2
        assert db.get_cached_segments("A", "B", "2026-05-15", "train") is None


# ─────────────────────────────────────────────────────────────────────────────
#  Saved Routes (CRUD)
# ─────────────────────────────────────────────────────────────────────────────

class TestSavedRoutes:
    def test_add_and_list(self, db):
        rid = db.add_saved_route(
            combo_id="C1", route_label="Jakarta → Surabaya",
            mode_label="🚂", total_price=350_000, total_duration_minutes=510,
            combo_data={"foo": "bar"}, notes="weekend",
        )
        assert rid > 0
        routes = db.get_saved_routes()
        assert len(routes) == 1
        assert routes[0]["combo_id"] == "C1"
        assert routes[0]["notes"] == "weekend"
        assert routes[0]["starred"] == 0

    def test_update_notes(self, db):
        rid = db.add_saved_route(
            combo_id="C1", route_label="A", mode_label="🚂",
            total_price=100, total_duration_minutes=60, combo_data={},
        )
        ok = db.update_saved_route_notes(rid, "new note")
        assert ok is True
        assert db.get_saved_routes()[0]["notes"] == "new note"

    def test_update_notes_missing_returns_false(self, db):
        ok = db.update_saved_route_notes(9999, "x")
        assert ok is False

    def test_toggle_starred(self, db):
        rid = db.add_saved_route(
            combo_id="C", route_label="A", mode_label="🚂",
            total_price=1, total_duration_minutes=1, combo_data={},
        )
        assert db.get_saved_routes()[0]["starred"] == 0
        db.toggle_starred(rid)
        assert db.get_saved_routes()[0]["starred"] == 1
        db.toggle_starred(rid)
        assert db.get_saved_routes()[0]["starred"] == 0

    def test_delete(self, db):
        rid = db.add_saved_route(
            combo_id="C", route_label="A", mode_label="🚂",
            total_price=1, total_duration_minutes=1, combo_data={},
        )
        assert db.delete_saved_route(rid) is True
        assert db.get_saved_routes() == []

    def test_delete_missing_returns_false(self, db):
        assert db.delete_saved_route(9999) is False

    def test_clear_all(self, db):
        for i in range(3):
            db.add_saved_route(f"C{i}", "A", "🚂", 1, 1, {})
        n = db.clear_saved_routes()
        assert n == 3
        assert db.get_saved_routes() == []
