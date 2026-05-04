
"""
database.py — ANTARA Project
==============================
Semua operasi SQLite: saved routes, recent searches, user preferences.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Asumsi model RouteCombo dan SearchCriteria ada di file models.py
# Jika tidak ada, perlu didefinisikan atau di-mock untuk tujuan implementasi ini.
# Untuk saat ini, kita akan mengasumsikan mereka adalah dataclass atau Pydantic models
# yang bisa di-serialize/deserialize ke/dari JSON.

# Mock models jika tidak tersedia, untuk memungkinkan kode berjalan
# Dalam aplikasi nyata, ini akan diimpor dari models.py
class RouteCombo:
    def __init__(self, origin, destination, total_price, total_duration, mode_label, details=None):
        self.origin = origin
        self.destination = destination
        self.total_price = total_price
        self.total_duration = total_duration
        self.mode_label = mode_label
        self.details = details # Contoh field tambahan

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)

class SearchCriteria:
    def __init__(self, origin, destination, departure_date, passengers):
        self.origin = origin
        self.destination = destination
        self.departure_date = departure_date
        self.passengers = passengers

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)


# ── Path ke file database ──────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "data" / "antara.db"

# ══════════════════════════════════════════════════════════════════════════════
#  KONEKSI
# ══════════════════════════════════════════════════════════════════════════════
def get_connection() -> sqlite3.Connection:
    """Buka koneksi ke SQLite. Buat folder data/ jika belum ada."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # akses kolom by name: row["username"]
    return conn

# ══════════════════════════════════════════════════════════════════════════════
#  INISIALISASI SCHEMA
# ══════════════════════════════════════════════════════════════════════════════
def init_db() -> None:
    """
    Buat semua tabel jika belum ada.
    Panggil fungsi ini di app.py saat startup.
    """
    with get_connection() as conn:
        conn.executescript("""
            -- Tabel user
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                full_name   TEXT    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now')),
                updated_at  TEXT    DEFAULT (datetime('now'))
            );
            -- Tabel saved routes
            CREATE TABLE IF NOT EXISTS saved_routes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                route_json      TEXT    NOT NULL,   -- RouteCombo di-serialize ke JSON
                origin          TEXT    NOT NULL,
                destination     TEXT    NOT NULL,
                total_price     REAL    NOT NULL,
                total_duration  INTEGER NOT NULL,
                mode_label      TEXT    NOT NULL,
                notes           TEXT,
                is_favorite     INTEGER DEFAULT 0,
                saved_at        TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            -- Tabel recent searches
            CREATE TABLE IF NOT EXISTS recent_searches (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                origin          TEXT    NOT NULL,
                destination     TEXT    NOT NULL,
                departure_date  TEXT    NOT NULL,
                passengers      INTEGER NOT NULL,
                searched_at     TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            -- Tabel user preferences
            CREATE TABLE IF NOT EXISTS user_preferences (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER UNIQUE NOT NULL,
                language            TEXT    DEFAULT 'id',
                currency            TEXT    DEFAULT 'IDR',
                dark_mode           INTEGER DEFAULT 0,
                price_alerts        INTEGER DEFAULT 1,
                booking_reminders   INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
    print(f"[DB] Database siap di: {DB_PATH}")

# ══════════════════════════════════════════════════════════════════════════════
#  SAVED ROUTES — CRUD
# ══════════════════════════════════════════════════════════════════════════════
def save_route(user_id: int, combo: RouteCombo, notes: str = "") -> int:
    """
    CREATE: Simpan RouteCombo ke database.
    Returns:
        ID dari row yang baru disimpan.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO saved_routes (
                user_id, route_json, origin, destination, total_price,
                total_duration, mode_label, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, combo.to_json(), combo.origin, combo.destination,
                combo.total_price, combo.total_duration, combo.mode_label, notes
            )
        )
        conn.commit()
        return cursor.lastrowid

def get_saved_routes(user_id: int) -> list[dict]:
    """
    READ: Ambil semua saved routes milik user.
    Returns:
        List of dict dengan key: id, origin, destination, total_price,
        total_duration, mode_label, notes, is_favorite, saved_at
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """SELECT
                id, origin, destination, total_price, total_duration,
                mode_label, notes, is_favorite, saved_at
            FROM saved_routes WHERE user_id = ? ORDER BY saved_at DESC""",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def update_route_notes(saved_route_id: int, notes: str) -> None:
    """
    UPDATE: Ganti catatan pada saved route.
    """
    with get_connection() as conn:
        conn.execute(
            """UPDATE saved_routes SET notes = ? WHERE id = ?""",
            (notes, saved_route_id)
        )
        conn.commit()

def toggle_favorite(saved_route_id: int) -> bool:
    """
    UPDATE: Toggle status bintang (favorite) sebuah saved route.
    Returns:
        Status is_favorite yang baru (True / False).
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """SELECT is_favorite FROM saved_routes WHERE id = ?""",
            (saved_route_id,)
        )
        current_status = cursor.fetchone()["is_favorite"]
        new_status = 1 if current_status == 0 else 0
        conn.execute(
            """UPDATE saved_routes SET is_favorite = ? WHERE id = ?""",
            (new_status, saved_route_id)
        )
        conn.commit()
        return bool(new_status)

def delete_saved_route(saved_route_id: int) -> None:
    """
    DELETE: Hapus saved route berdasarkan ID.
    """
    with get_connection() as conn:
        conn.execute(
            """DELETE FROM saved_routes WHERE id = ?""",
            (saved_route_id,)
        )
        conn.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  RECENT SEARCHES
# ══════════════════════════════════════════════════════════════════════════════
def add_recent_search(user_id: int, criteria: SearchCriteria) -> None:
    """
    Simpan kriteria pencarian ke history.
    Otomatis dipanggil setiap kali user melakukan search.
    """
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO recent_searches (
                user_id, origin, destination, departure_date, passengers
            ) VALUES (?, ?, ?, ?, ?)""",
            (
                user_id, criteria.origin, criteria.destination,
                criteria.departure_date, criteria.passengers
            )
        )
        conn.commit()

def get_recent_searches(user_id: int, limit: int = 10) -> list[dict]:
    """
    Ambil N pencarian terakhir milik user, diurutkan dari yang terbaru.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """SELECT
                id, origin, destination, departure_date, passengers, searched_at
            FROM recent_searches WHERE user_id = ?
            ORDER BY searched_at DESC LIMIT ?""",
            (user_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

def clear_recent_searches(user_id: int) -> None:
    """
    Hapus semua history pencarian milik user.
    """
    with get_connection() as conn:
        conn.execute(
            """DELETE FROM recent_searches WHERE user_id = ?""",
            (user_id,)
        )
        conn.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  USER PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════
def get_preferences(user_id: int) -> dict:
    """
    Ambil preferensi user (language, currency, dark_mode, dst.).
    Jika belum ada, kembalikan nilai default.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """SELECT
                language, currency, dark_mode, price_alerts, booking_reminders
            FROM user_preferences WHERE user_id = ?""",
            (user_id,)
        )
        prefs = cursor.fetchone()
        if prefs:
            # Convert INTEGER (0/1) to boolean for dark_mode, price_alerts, booking_reminders
            prefs_dict = dict(prefs)
            prefs_dict['dark_mode'] = bool(prefs_dict['dark_mode'])
            prefs_dict['price_alerts'] = bool(prefs_dict['price_alerts'])
            prefs_dict['booking_reminders'] = bool(prefs_dict['booking_reminders'])
            return prefs_dict
        else:
            return {
                "language": "id",
                "currency": "IDR",
                "dark_mode": False,
                "price_alerts": True,
                "booking_reminders": True,
            }

def update_preferences(user_id: int, prefs: dict) -> None:
    """
    Simpan/update preferensi user.
    """
    with get_connection() as conn:
        # Convert boolean to INTEGER (0/1) for database storage
        dark_mode_int = 1 if prefs.get('dark_mode') else 0
        price_alerts_int = 1 if prefs.get('price_alerts') else 0
        booking_reminders_int = 1 if prefs.get('booking_reminders') else 0

        conn.execute(
            """INSERT INTO user_preferences (
                user_id, language, currency, dark_mode, price_alerts, booking_reminders
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                currency = excluded.currency,
                dark_mode = excluded.dark_mode,
                price_alerts = excluded.price_alerts,
                booking_reminders = excluded.booking_reminders
            """,
            (
                user_id, prefs.get('language', 'id'), prefs.get('currency', 'IDR'),
                dark_mode_int, price_alerts_int, booking_reminders_int
            )
        )
        conn.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  QUICK TEST
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Menginisialisasi database...")
    init_db()
    print("Database berhasil dibuat.")
    print(f"Lokasi: {DB_PATH.resolve()}")

    # Contoh penggunaan (Anda bisa menambahkan lebih banyak tes di sini)
    # Pastikan Anda memiliki instance RouteCombo dan SearchCriteria yang valid
    # sebelum menjalankan ini.

    # Membuat user dummy
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, username, email, password, full_name) VALUES (?, ?, ?, ?, ?)",
                     (1, 'testuser', 'test@example.com', 'password123', 'Test User'))
        conn.commit()

    user_id = 1

    # Test save_route
    route1 = RouteCombo("Jakarta", "Surabaya", 500000.0, 720, "Kereta")
    route_id = save_route(user_id, route1, "Perjalanan bisnis")
    print(f"Route disimpan dengan ID: {route_id}")

    # Test get_saved_routes
    saved_routes = get_saved_routes(user_id)
    print("Saved Routes:", saved_routes)

    # Test update_route_notes
    update_route_notes(route_id, "Perjalanan bisnis penting")
    saved_routes = get_saved_routes(user_id)
    print("Saved Routes setelah update notes:", saved_routes)

    # Test toggle_favorite
    is_fav = toggle_favorite(route_id)
    print(f"Route ID {route_id} favorit: {is_fav}")
    saved_routes = get_saved_routes(user_id)
    print("Saved Routes setelah toggle favorit:", saved_routes)

    # Test add_recent_search
    search1 = SearchCriteria("Bandung", "Yogyakarta", "2026-06-01", 2)
    add_recent_search(user_id, search1)
    print("Pencarian terakhir ditambahkan.")

    # Test get_recent_searches
    recent_searches = get_recent_searches(user_id)
    print("Recent Searches:", recent_searches)

    # Test get_preferences (akan mengembalikan default jika belum ada)
    prefs = get_preferences(user_id)
    print("User Preferences (default/existing):", prefs)

    # Test update_preferences
    new_prefs = {"language": "en", "currency": "USD", "dark_mode": True, "price_alerts": False}
    update_preferences(user_id, new_prefs)
    prefs = get_preferences(user_id)
    print("User Preferences (setelah update):", prefs)

    # Test clear_recent_searches
    clear_recent_searches(user_id)
    recent_searches = get_recent_searches(user_id)
    print("Recent Searches setelah clear:", recent_searches)

    # Test delete_saved_route
    delete_saved_route(route_id)
    saved_routes = get_saved_routes(user_id)
    print("Saved Routes setelah delete:", saved_routes)