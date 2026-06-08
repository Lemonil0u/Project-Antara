"""
database/database.py — ANTARA Project
=====================================
Lapisan persistensi SQLite untuk ANTARA. Mengelola 5 tabel:

  1. search_history    — riwayat pencarian + ringkasan rute terbaik (JSON) [per-user]
  2. user_preferences  — preferensi user (bahasa, currency, dark mode, dll) [global]
  3. price_cache       — cache hasil scrape agar tidak ulang scraping rute sama [global]
  4. saved_routes      — bookmark user atas rute favorit (CRUD) [per-user]
  5. users             — akun user (registrasi & login)

Prinsip:
  - Raw sqlite3 (no ORM) → ringan, mudah dijelaskan saat sidang.
  - Setiap operasi pakai context manager `with sqlite3.connect()` → auto-commit / rollback.
  - JSON dipakai untuk menyimpan objek kompleks (RouteCombo) di kolom TEXT.
  - Semua method aman terhadap data hilang (tidak crash).
  - Password di-hash SHA-256 sebelum disimpan (tidak pernah plain-text).
  - search_history & saved_routes nyantol ke user lewat kolom user_id.
"""

import hashlib
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

        db.save_search_result(..., user_id=42)
        history = db.get_search_history(user_id=42)
        db.add_saved_route(..., user_id=42)
        db.delete_user_by_email("foo@bar.com")  # cascade ke history + saved_routes
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

    @staticmethod
    def _add_column_if_missing(cur, table: str, column: str, coltype: str) -> None:
        """Helper migrasi: ALTER TABLE ADD COLUMN kalau kolom belum ada."""
        cur.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in cur.fetchall()}
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")

    def _init_schema(self) -> None:
        """Buat semua tabel jika belum ada (idempotent) + migrasi user_id."""
        with self._connect() as conn:
            cur = conn.cursor()

            # 1. Riwayat pencarian (per-user via user_id)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    origin      TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    passengers  INTEGER DEFAULT 1,
                    best_route_combo_json TEXT,
                    total_options INTEGER DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Preferensi user (key-value, JSON value) — tetap global untuk sekarang
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key        TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Price cache (global, dipakai antar-user)
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

            # 4. Saved routes (per-user via user_id)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_routes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER,
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

            # 5. Users (akun registrasi)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name    TEXT NOT NULL,
                    email        TEXT NOT NULL UNIQUE,
                    phone        TEXT DEFAULT '',
                    password_hash TEXT NOT NULL,
                    location     TEXT DEFAULT 'Indonesia',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── MIGRASI: tambah user_id ke DB lama yang belum punya kolom itu
            # Kalau DB sudah fresh (baru dibikin), ini no-op karena kolomnya udah ada.
            self._add_column_if_missing(cur, "search_history", "user_id", "INTEGER")
            self._add_column_if_missing(cur, "saved_routes",   "user_id", "INTEGER")

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
        user_id: Optional[int] = None,
    ) -> int:
        """
        Simpan satu hasil pencarian. Kembalikan id baris baru.

        best_route_combo: dict apa pun yang JSON-serializable, biasanya
            ringkasan combo terbaik {"route": ..., "price": ..., ...}.
        user_id: id user yang melakukan pencarian. None = ga ke-attach ke siapa-siapa.
        """
        combo_json = json.dumps(best_route_combo or {}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO search_history
                    (user_id, origin, destination, date, passengers,
                     best_route_combo_json, total_options)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, origin, destination, date, passengers,
                  combo_json, total_options))
            conn.commit()
            return cur.lastrowid

    def get_search_history(self, limit: int = 10,
                           user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Ambil riwayat pencarian terbaru (sorted DESC by searched_at).
        Jika user_id diberikan, filter hanya milik user itu.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id is not None:
                cur.execute("""
                    SELECT * FROM search_history
                    WHERE user_id = ?
                    ORDER BY searched_at DESC
                    LIMIT ?
                """, (user_id, limit))
            else:
                cur.execute("""
                    SELECT * FROM search_history
                    ORDER BY searched_at DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    # Alias agar tetap kompatibel dengan kode lama
    def save_result(self, origin: str, destination: str, date: str,
                    best_route_combo: Dict[str, Any]) -> int:
        return self.save_search_result(
            origin=origin, destination=destination, date=date,
            passengers=1, best_route_combo=best_route_combo,
        )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.get_search_history(limit=limit)

    def clear_search_history(self, user_id: Optional[int] = None) -> int:
        """Hapus riwayat. Jika user_id diberikan, cuma milik user itu."""
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id is not None:
                cur.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            else:
                cur.execute("DELETE FROM search_history")
            conn.commit()
            return cur.rowcount

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 2: USER PREFERENCES (tetap global)
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
        """Simpan segmen hasil scrape ke cache."""
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
        """Ambil cache jika usianya ≤ max_age_minutes, else None."""
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
    #  TABEL 4: SAVED ROUTES (CRUD, per-user)
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
        user_id: Optional[int] = None,
    ) -> int:
        """Tambah rute favorit. Kembalikan id baru."""
        combo_json = json.dumps(combo_data, ensure_ascii=False, default=str)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO saved_routes
                    (user_id, combo_id, route_label, mode_label,
                     total_price, total_duration_minutes, combo_json, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, combo_id, route_label, mode_label,
                  total_price, total_duration_minutes, combo_json, notes))
            conn.commit()
            return cur.lastrowid

    def get_saved_routes(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Ambil saved routes. Jika user_id diberikan, filter milik user itu."""
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id is not None:
                cur.execute(
                    "SELECT * FROM saved_routes WHERE user_id = ? ORDER BY saved_at DESC",
                    (user_id,),
                )
            else:
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

    def clear_saved_routes(self, user_id: Optional[int] = None) -> int:
        """Hapus saved routes. Jika user_id diberikan, cuma milik user itu."""
        with self._connect() as conn:
            cur = conn.cursor()
            if user_id is not None:
                cur.execute("DELETE FROM saved_routes WHERE user_id = ?", (user_id,))
            else:
                cur.execute("DELETE FROM saved_routes")
            conn.commit()
            return cur.rowcount

    def get_saved_route_by_combo(self, combo_id: str,
                                 user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Cek apakah route ini udah disave oleh user. Buat toggle."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM saved_routes
                WHERE combo_id = ? AND (user_id IS ? OR user_id = ?)
            """, (combo_id, user_id, user_id))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_saved_route_by_combo(self, combo_id: str,
                                    user_id: Optional[int] = None) -> bool:
        """Hapus saved route berdasarkan combo_id + user_id."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM saved_routes
                WHERE combo_id = ? AND (user_id IS ? OR user_id = ?)
            """, (combo_id, user_id, user_id))
            conn.commit()
            return cur.rowcount > 0

    # ─────────────────────────────────────────────────────────────────────────
    #  TABEL 5: USERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, full_name: str, email: str, password: str,
                      phone: str = "", location: str = "Indonesia") -> Dict[str, Any]:
        """
        Daftarkan user baru. Return dict user jika berhasil.
        Raise ValueError jika email sudah terdaftar.
        """
        password_hash = self._hash_password(password)
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO users (full_name, email, phone, password_hash, location)
                    VALUES (?, ?, ?, ?, ?)
                """, (full_name, email.lower(), phone, password_hash, location))
                conn.commit()
                return {
                    "id": cur.lastrowid,
                    "name": full_name,
                    "email": email.lower(),
                    "phone": phone,
                    "location": location,
                }
        except sqlite3.IntegrityError:
            raise ValueError(f"Email '{email}' sudah terdaftar.")

    def get_user_by_email(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Login: cari user by email + verifikasi password.
        Return dict user jika cocok, None jika tidak ditemukan / salah password.
        """
        password_hash = self._hash_password(password)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, full_name, email, phone, location
                FROM users
                WHERE email = ? AND password_hash = ?
            """, (email.lower(), password_hash))
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["full_name"],
            "email": row["email"],
            "phone": row["phone"],
            "location": row["location"],
        }

    def email_exists(self, email: str) -> bool:
        """Cek apakah email sudah terdaftar (untuk validasi sebelum register)."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE email = ?", (email.lower(),))
            return cur.fetchone() is not None

    def delete_user_by_email(self, email: str) -> bool:
        """Hapus user + semua search history & saved routes miliknya."""
        with self._connect() as conn:
            cur = conn.cursor()
            # Cari id dulu
            cur.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
            row = cur.fetchone()
            if row is None:
                return False
            user_id = row["id"]

            # Cascade manual (SQLite ga ada FK default-on)
            cur.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM saved_routes WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True

    def __repr__(self) -> str:
        return f"DatabaseManager(db_path='{self.db_path}')"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  DatabaseManager — Smoke Test")
    print("=" * 60)

    db = DatabaseManager("data/_smoke_test.db")
    print(db)

    # Register test user
    user = db.register_user("Test User", "test@example.com", "password123", phone="081234567890")
    test_uid = user["id"]
    print(f"\nRegistered user id={test_uid}")

    # Search history
    db.save_search_result(
        origin="Jakarta", destination="Surabaya",
        date="2026-05-15", passengers=2,
        best_route_combo={"route": "Jakarta → Surabaya",
                          "price": "Rp 350.000", "duration": "8j 30m"},
        total_options=12,
        user_id=test_uid,
    )
    history = db.get_search_history(user_id=test_uid)
    print(f"\nHistory rows for user {test_uid}: {len(history)}")

    # Saved routes
    sid = db.add_saved_route(
        combo_id="COMBO-0001",
        route_label="Jakarta → Surabaya",
        mode_label="🚂",
        total_price=350_000,
        total_duration_minutes=510,
        combo_data={"foo": "bar"},
        notes="weekend trip",
        user_id=test_uid,
    )
    saved = db.get_saved_routes(user_id=test_uid)
    print(f"\nSaved routes for user {test_uid}: {len(saved)}")
    print(f"  ID {sid}: {saved[0]['route_label']}")

    # Delete user → cascade
    db.delete_user_by_email("test@example.com")
    print(f"\nAfter delete:")
    print(f"  History rows: {len(db.get_search_history(user_id=test_uid))}")
    print(f"  Saved routes: {len(db.get_saved_routes(user_id=test_uid))}")
    print(f"  User exists: {db.email_exists('test@example.com')}")

    # Cleanup
    Path("data/_smoke_test.db").unlink(missing_ok=True)
    print("\n✓ Smoke test passed, cleaned up.")