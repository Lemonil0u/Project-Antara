"""
config.py — ANTARA
==================
Konfigurasi terpusat untuk seluruh aplikasi.

Ubah nilai di sini untuk mengatur perilaku scraper tanpa perlu
menyentuh file-file lain.
"""

# ── SCRAPER ───────────────────────────────────────────────────────────────────

# Timeout per request Playwright, dalam detik.
# Rekomendasi: 20 untuk koneksi cepat, 45 untuk koneksi lambat/fluktuatif.
SCRAPER_TIMEOUT: int = 30

# Jalankan browser Playwright tanpa UI (True untuk production/server).
SCRAPER_HEADLESS: bool = True

# Mode transportasi yang diaktifkan.
SCRAPER_ENABLED_MODES: list[str] = ["train", "flight", "bus"]

# ── QUICK SEARCH ──────────────────────────────────────────────────────────────

QUICK_SEARCH_MAX_PER_MODE: int = 5

# ── CACHE ─────────────────────────────────────────────────────────────────────

# Berapa menit hasil scraping disimpan di cache SQLite sebelum expired.
CACHE_TTL_MINUTES: int = 60