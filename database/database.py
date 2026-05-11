"""
database/database.py — ANTARA Project
=====================================
Lapisan persistensi SQLite untuk ANTARA. Mengelola 4 tabel:

  1. search_history    — riwayat pencarian + ringkasan rute terbaik (JSON)
  2. user_preferences  — preferensi user (bahasa, currency, dark mode, dll)
  3. price_cache       — cache hasil scrape agar tidak ulang scraping rute sama
  4. saved_routes      — bookmark user atas rute favorit (CRUD)

Prinsip:
  - Raw sqlite3 (no ORM) → ringan, mudah dijelaskan saat sidang.
  - Setiap operasi pakai context manager `with sqlite3.connect()` → auto-commit / rollback.
  - JSON dipakai untuk menyimpan objek kompleks (RouteCombo) di kolom TEXT.
  - Semua method aman terhadap data hilang (tidak crash).
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  Lokasi default file DB
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "antara.db"


class DatabaseManager:
    """
    Database manager untuk ANTARA.

    Pemakaian:
        db = DatabaseManager()                  # pakai data/antara.db default
        db = DatabaseManager("custom.db")       # path custom

        db.save_search_result(...)
        history = db.get_search_history()
        db.set_preference("dark_mode", True)
        pref = db.get_preference("dark_mode", default=False)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        # Pastikan folder data/ ada
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ─────────────────────────────────────────────────────────────────────────
    #  KONEKSI & SKEMA
    # ─────────────────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Buka koneksi dengan row_factory agar hasil fetch jadi dict-like."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Buat semua tabel jika belum ada (idempotent)."""
        with self._connect() as conn:
            cur = conn.cursor()

            # 1. Riwayat pencarian
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin      TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    passengers  INTEGER DEFAULT 1,
                    best_route_combo_json TEXT,
                    total_options INTEGER DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Preferensi user (key-value, JSON value)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key        TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Price cache (hindari ulang scrape rute yang sama dalam window pendek)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    cache_key   TEXT PRIMARY KEY,
                    origin      TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    mode        TEXT NOT NULL,
                    segments_json TEXT NOT NULL,
                    cached_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Saved routes (bookmark user)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_routes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    combo_id   TEXT NOT NULL,
                    route_label TEXT NOT NULL,
                    mode_label  TEXT NOT NULL,
                    total_price REAL NOT NULL,
                    total_duration_minutes INTEGER NOT NULL,
                    combo_json TEXT NOT NULL,
                    notes      TEXT DEFAULT '',
                    starred    INTEGER DEFAULT 0,
                    saved_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 1: SEARCH HISTORY
    # ─────────────────────────────────────────────────────────────────────────

    def save_search_result(
        self,
        origin: str,
        destination: str,
        date: str,
        passengers: int,
        best_route_combo: Optional[Dict[str, Any]] = None,
        total_options: int = 0,
    ) -> int:
        """
        Simpan satu hasil pencarian. Kembalikan id baris baru.

        best_route_combo: dict apa pun yang JSON-serializable, biasanya
            ringkasan combo terbaik {"route": ..., "price": ..., ...}.
        """
        combo_json = json.dumps(best_route_combo or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO search_history
                    (origin, destination, date, passengers,
                     best_route_combo_json, total_options)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (origin, destination, date, passengers, combo_json, total_options))
            conn.commit()
            return cur.lastrowid

    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Ambil riwayat pencarian terbaru (sorted DESC by searched_at)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, origin, destination, date, passengers,
                       best_route_combo_json, total_options, searched_at
                FROM search_history
                ORDER BY searched_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    # Alias agar tetap kompatibel dengan kode lama yang panggil db.save_result / db.get_history
    def save_result(self, origin: str, destination: str, date: str,
                    best_route_combo: Dict[str, Any]) -> int:
        return self.save_search_result(
            origin=origin, destination=destination, date=date,
            passengers=1, best_route_combo=best_route_combo,
        )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get_search_history(limit=limit)

    def clear_search_history(self) -> int:
        """Hapus semua riwayat. Kembalikan jumlah baris yang dihapus."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM search_history")
            conn.commit()
            return cur.rowcount

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 2: USER PREFERENCES
    # ─────────────────────────────────────────────────────────────────────────

    def set_preference(self, key: str, value: Any) -> None:
        """Upsert preferensi user. Value harus JSON-serializable."""
        value_json = json.dumps(value, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_preferences (key, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value_json))
            conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Ambil 1 preferensi. Kembalikan default jika tidak ada."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value_json FROM user_preferences WHERE key = ?", (key,))
            row = cur.fetchone()
            if row is None:
                return default
            try:
                return json.loads(row["value_json"])
            except (json.JSONDecodeError, TypeError):
                return default

    def get_all_preferences(self) -> Dict[str, Any]:
        """Ambil semua preferensi sebagai dict."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value_json FROM user_preferences")
            result: Dict[str, Any] = {}
            for row in cur.fetchall():
                try:
                    result[row["key"]] = json.loads(row["value_json"])
                except (json.JSONDecodeError, TypeError):
                    result[row["key"]] = None
            return result

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 3: PRICE CACHE
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(origin: str, destination: str, date: str, mode: str) -> str:
        return f"{origin}|{destination}|{date}|{mode}"

    def cache_segments(
        self,
        origin: str,
        destination: str,
        date: str,
        mode: str,
        segments: List[Dict[str, Any]],
    ) -> None:
        """
        Simpan segmen hasil scrape ke cache.
        segments: list of dict (sudah JSON-serializable).
        """
        key = self._cache_key(origin, destination, date, mode)
        seg_json = json.dumps(segments, ensure_ascii=False, default=str)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO price_cache
                    (cache_key, origin, destination, date, mode, segments_json, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(cache_key) DO UPDATE SET
                    segments_json = excluded.segments_json,
                    cached_at = CURRENT_TIMESTAMP
            """, (key, origin, destination, date, mode, seg_json))
            conn.commit()

    def get_cached_segments(
        self,
        origin: str,
        destination: str,
        date: str,
        mode: str,
        max_age_minutes: int = 60,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Ambil cache jika usianya ≤ max_age_minutes, else None.
        """
        key = self._cache_key(origin, destination, date, mode)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT segments_json, cached_at
                FROM price_cache
                WHERE cache_key = ?
                  AND (strftime('%s','now') - strftime('%s', cached_at)) <= ? * 60
            """, (key, max_age_minutes))
            row = cur.fetchone()
            if row is None:
                return None
            try:
                return json.loads(row["segments_json"])
            except (json.JSONDecodeError, TypeError):
                return None

    def clear_price_cache(self) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM price_cache")
            conn.commit()
            return cur.rowcount

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 4: SAVED ROUTES (CRUD)
    # ─────────────────────────────────────────────────────────────────────────

    def add_saved_route(
        self,
        combo_id: str,
        route_label: str,
        mode_label: str,
        total_price: float,
        total_duration_minutes: int,
        combo_data: Dict[str, Any],
        notes: str = "",
    ) -> int:
        """Tambah rute favorit. Kembalikan id baru."""
        combo_json = json.dumps(combo_data, ensure_ascii=False, default=str)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO saved_routes
                    (combo_id, route_label, mode_label,
                     total_price, total_duration_minutes,
                     combo_json, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (combo_id, route_label, mode_label,
                  total_price, total_duration_minutes, combo_json, notes))
            conn.commit()
            return cur.lastrowid

    def get_saved_routes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM saved_routes ORDER BY saved_at DESC")
            return [dict(row) for row in cur.fetchall()]

    def update_saved_route_notes(self, route_id: int, notes: str) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE saved_routes SET notes = ? WHERE id = ?",
                (notes, route_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def toggle_starred(self, route_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE saved_routes SET starred = 1 - starred WHERE id = ?",
                (route_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_saved_route(self, route_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_routes WHERE id = ?", (route_id,))
            conn.commit()
            return cur.rowcount > 0

    def clear_saved_routes(self) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_routes")
            conn.commit()
            return cur.rowcount

    # ─────────────────────────────────────────────────────────────────────────
    #  UTILITAS
    # ─────────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"DatabaseManager(db_path='{self.db_path}')"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  DatabaseManager — Smoke Test")
    print("=" * 60)

    db = DatabaseManager("data/_smoke_test.db")
    print(db)

    # Search history
    db.save_search_result(
        origin="Jakarta", destination="Surabaya",
        date="2026-05-15", passengers=2,
        best_route_combo={"route": "Jakarta → Surabaya",
                          "price": "Rp 350.000", "duration": "8j 30m"},
        total_options=12,
    )
    history = db.get_search_history()
    print(f"\nHistory rows: {len(history)}")
    print(f"  First row: {history[0]['origin']} → {history[0]['destination']}")

    # Preferences
    db.set_preference("dark_mode", True)
    db.set_preference("language", "Indonesian")
    print(f"\nPreferences: {db.get_all_preferences()}")

    # Cache
    db.cache_segments(
        "Jakarta", "Surabaya", "2026-05-15", "train",
        segments=[{"provider": "Argo Bromo", "price": 350000}],
    )
    cached = db.get_cached_segments("Jakarta", "Surabaya", "2026-05-15", "train")
    print(f"\nCached segments: {cached}")

    # Saved routes
    sid = db.add_saved_route(
        combo_id="COMBO-0001",
        route_label="Jakarta → Surabaya",
        mode_label="🚂",
        total_price=350_000,
        total_duration_minutes=510,
        combo_data={"foo": "bar"},
        notes="weekend trip",
    )
    saved = db.get_saved_routes()
    print(f"\nSaved routes: {len(saved)}")
    print(f"  ID {sid}: {saved[0]['route_label']} — notes: '{saved[0]['notes']}'")

    db.toggle_starred(sid)
    print(f"  After star: starred={db.get_saved_routes()[0]['starred']}")

    # Cleanup smoke test db
    Path("data/_smoke_test.db").unlink(missing_ok=True)
    print("\n✓ Smoke test passed, cleaned up.")
