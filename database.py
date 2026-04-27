"""
database.py — ANTARA Project
==============================
Semua operasi SQLite: saved routes, recent searches, user preferences.

TODO (Umarwa):
  - Implementasi setiap method yang bertanda TODO
  - File .db disimpan di data/antara.db
  - Jalankan init_db() satu kali saat app pertama kali dijalankan
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from models import RouteCombo, SearchCriteria

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

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi save_route()")


def get_saved_routes(user_id: int) -> list[dict]:
    """
    READ: Ambil semua saved routes milik user.

    Returns:
        List of dict dengan key: id, origin, destination, total_price,
        total_duration, mode_label, notes, is_favorite, saved_at

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi get_saved_routes()")


def update_route_notes(saved_route_id: int, notes: str) -> None:
    """
    UPDATE: Ganti catatan pada saved route.

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi update_route_notes()")


def toggle_favorite(saved_route_id: int) -> bool:
    """
    UPDATE: Toggle status bintang (favorite) sebuah saved route.

    Returns:
        Status is_favorite yang baru (True / False).

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi toggle_favorite()")


def delete_saved_route(saved_route_id: int) -> None:
    """
    DELETE: Hapus saved route berdasarkan ID.

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi delete_saved_route()")


# ══════════════════════════════════════════════════════════════════════════════
#  RECENT SEARCHES
# ══════════════════════════════════════════════════════════════════════════════

def add_recent_search(user_id: int, criteria: SearchCriteria) -> None:
    """
    Simpan kriteria pencarian ke history.
    Otomatis dipanggil setiap kali user melakukan search.

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi add_recent_search()")


def get_recent_searches(user_id: int, limit: int = 10) -> list[dict]:
    """
    Ambil N pencarian terakhir milik user, diurutkan dari yang terbaru.

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi get_recent_searches()")


def clear_recent_searches(user_id: int) -> None:
    """
    Hapus semua history pencarian milik user.

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi clear_recent_searches()")


# ══════════════════════════════════════════════════════════════════════════════
#  USER PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

def get_preferences(user_id: int) -> dict:
    """
    Ambil preferensi user (language, currency, dark_mode, dst.).
    Jika belum ada, kembalikan nilai default.

    TODO (Umarwa): Implementasi ini.
    """
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

    TODO (Umarwa): Implementasi ini.
    """
    raise NotImplementedError("TODO: implementasi update_preferences()")


# ══════════════════════════════════════════════════════════════════════════════
#  QUICK TEST
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Menginisialisasi database...")
    init_db()
    print("Database berhasil dibuat.")
    print(f"Lokasi: {DB_PATH.resolve()}")
