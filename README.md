# ANTARA — Multi-Modal Transportation Price Comparison

[![Made with Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/)

> **Pengembangan Komputasi Kreatif** — Politeknik Negeri Bandung — 2026
> Dosen Pembimbing: **Beri Noviansyah**
> Tim: **Lunaraya, Nesya, Nurul, Umarwa**

---

## 1. Tentang ANTARA

ANTARA adalah dashboard berbasis web yang **membandingkan harga & durasi tiket kereta, bus, dan pesawat** untuk perjalanan antar-kota di Indonesia. ANTARA bukan agregator booking — ANTARA fokus pada **analisis dan rekomendasi rute terbaik**, termasuk rute multi-modal yang sering luput dari OTA besar.

### Fitur utama

- **🔍 Pencarian multi-modal** — gabungan kereta + pesawat + bus dengan transit logis (max 2 transit).
- **🏆 Rekomendasi otomatis** — flag *Terhemat* dan *Tercepat* di setiap hasil.
- **📊 Visualisasi interaktif** — scatter plot Harga vs Durasi, tren harga per jam, breakdown moda.
- **⭐ Saved Routes** — simpan rute favorit ke database lokal (SQLite).
- **🕐 Riwayat pencarian** — otomatis tersimpan, satu klik untuk diulangi.
- **⚙️ Pengaturan tersinkron** — preferensi user (bahasa, currency, dll) disimpan di database.

### Status implementasi

| Komponen | Status |
| --- | --- |
| TrainScraper (Traveloka KAI) | ✅ Berfungsi (Playwright async) |
| PlaneScraper | 🚧 Stub — `NotImplementedError` (siap diisi) |
| BusScraper | 🚧 Stub — `NotImplementedError` (siap diisi) |
| Smart Route Optimizer + weighted scoring | ✅ Berfungsi |
| Database (4 tabel: history, prefs, cache, saved) | ✅ Berfungsi |
| First-mile / Last-mile (Gojek/Grab) | 🧪 Stub — arsitektur siap, generator placeholder |
| Dashboard Streamlit (5 halaman) | ✅ Berfungsi |
| Unit test | ✅ 64 test passing |

Plane & Bus scrapers raise `NotImplementedError`; `MultiModalDataSource` menangkap dan men-skip-nya secara otomatis tanpa crash. Saat scraper kedua moda tersebut selesai, mereka langsung aktif tanpa perubahan kode di tempat lain.

---

## 2. Instalasi

### Prasyarat

- Python **3.10 atau lebih baru**
- pip
- Koneksi internet (untuk install Playwright Chromium ± 170 MB)

### Langkah

```bash
# 1. Clone / extract project
cd ANTARA_PROJECT/

# 2. (Opsional tapi disarankan) buat virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
venv\Scripts\activate             # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install browser Chromium untuk Playwright
playwright install chromium

# 5. Jalankan aplikasi
streamlit run app.py
```

App akan terbuka di **http://localhost:8501**.

---

## 3. Struktur Project

```
ANTARA_PROJECT/
├── app.py                      # Entry point Streamlit (5 halaman)
├── models.py                   # Dataclass: LocalSegment, TransportSegment,
│                               # RouteCombo, SearchCriteria, OptimizerResult
├── requirements.txt            # Dependencies (Playwright, bukan Selenium)
├── README.md                   # File ini
│
├── database/
│   ├── __init__.py
│   └── database.py             # DatabaseManager (SQLite, 4 tabel)
│
├── engine/
│   ├── __init__.py
│   ├── optimizer.py            # SmartRouteOptimizer + DummyDataGenerator
│   ├── data_source.py          # MultiModalDataSource (adapter scraper)
│   ├── local_data.py           # LocalSegmentGenerator (first-/last-mile stub)
│   └── visualizer.py           # Builder chart Plotly (modul mandiri)
│
├── scraper/
│   ├── __init__.py
│   ├── base_scraper.py         # Abstract base class
│   ├── train_scraper.py        # ✅ Implementasi penuh (Traveloka KAI)
│   ├── plane_scraper.py        # 🚧 Stub
│   └── bus_scraper.py          # 🚧 Stub
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # 21 test untuk dataclass
│   ├── test_database.py        # 19 test untuk DB (4 tabel)
│   └── test_optimizer.py       # 24 test untuk optimizer + dummy + local
│
├── data/                       # SQLite DB tersimpan di sini (otomatis dibuat)
│   └── antara.db
└── assets/                     # (kosong — placeholder untuk asset statis)
```

---

## 4. Cara Kerja: Algoritma Smart Route

### 4.1 Pipeline pencarian

```
SearchCriteria → SmartRouteOptimizer.optimize()
                      │
                      ▼
                ┌──────────────┐
                │ data_source  │  ← MultiModalDataSource (production)
                │ .get_segments│     atau DummyDataGenerator (testing)
                └──────────────┘
                      │
                      ▼
              List[TransportSegment]
                      │
       ┌──────────────┼──────────────────────┐
       ▼              ▼                      ▼
  Rute Langsung   Rute Transit-1      Rute Transit-2
  (1 segmen)      (2 segmen)          (3 segmen)
       │              │                      │
       └──────┬───────┴──────────────────────┘
              ▼
       (Opsional) Bungkus dengan first-mile + last-mile
              ▼
       Dedup → Sort (weighted) → Slice → Flag cheapest/fastest
              ▼
        OptimizerResult
```

### 4.2 Constraint multi-modal

- **Max transit**: 2 (jadi max 3 leg per rute).
- **Min waiting time per transfer**: 60 menit.
- **Max waiting time per transfer**: 180 menit.

Combo dengan waiting time di luar rentang ini otomatis di-drop.

### 4.3 Weighted scoring

Setelah semua combo dikumpulkan, mereka diurutkan dengan **composite score**:

```
score = 0.6 × normalized_price + 0.4 × normalized_duration
```

Normalisasi pakai min-max ke rentang [0, 1]. **Skor terendah = combo terbaik.** Bobot bisa dikonfigurasi via konstruktor `SmartRouteOptimizer(weight_price=..., weight_duration=...)`.

### 4.4 First-mile / Last-mile (stub)

Saat `criteria.include_local_legs=True` dan `optimizer.local_generator` di-set, setiap combo otomatis dibungkus dengan estimasi transport lokal:

```
🛵 Gojek (Rumah → Stasiun Gambir) +
🚂 KAI Argo Bromo (Jakarta → Surabaya) +
🛵 Grab (Stasiun Gubeng → Hotel)
```

**Catatan: saat ini estimasi nya placeholder** — berdasarkan tabel harga/durasi rata-rata per kota di `engine/local_data.py`. Belum scraping nyata. Combo bertanda `🛵 Door-to-Door` adalah hasil pembungkusan ini.

---

## 5. Database

Path default: `data/antara.db` (otomatis dibuat).

### Skema

| Tabel | Tujuan | Kolom utama |
| --- | --- | --- |
| `search_history` | Riwayat pencarian | origin, destination, date, best_route_combo_json, searched_at |
| `user_preferences` | Preferensi user (key-value JSON) | key, value_json, updated_at |
| `price_cache` | Hindari rescrape rute yang sama | cache_key, segments_json, cached_at |
| `saved_routes` | Bookmark rute favorit | combo_id, route_label, total_price, notes, starred |

### Price cache TTL

Default 60 menit (`cache_ttl_minutes` di `MultiModalDataSource`). Setelah TTL, query rute yang sama akan scraping ulang.

### CRUD lengkap

```python
from database import DatabaseManager
db = DatabaseManager()

# Search history
db.save_search_result(origin="Jakarta", destination="Surabaya", ...)
db.get_search_history(limit=10)
db.clear_search_history()

# Preferences (JSON value, any type)
db.set_preference("dark_mode", True)
db.get_preference("dark_mode", default=False)
db.get_all_preferences()

# Price cache
db.cache_segments(origin, dest, date, mode, segments)
db.get_cached_segments(origin, dest, date, mode, max_age_minutes=60)
db.clear_price_cache()

# Saved routes
db.add_saved_route(combo_id, route_label, ...)
db.get_saved_routes()
db.toggle_starred(route_id)
db.update_saved_route_notes(route_id, notes)
db.delete_saved_route(route_id)
db.clear_saved_routes()
```

---

## 6. Testing

```bash
# Jalankan semua test (butuh pytest, sudah ada di requirements)
pytest tests/ -v

# Atau modul tertentu
pytest tests/test_optimizer.py -v

# Smoke test cepat (tanpa pytest, manual run)
python -m engine.optimizer        # demo dummy data → 15 combos
python -m database.database       # smoke test semua tabel DB
python -m engine.local_data       # demo first-/last-mile generator
```

Coverage saat ini: **64 unit test** mencakup models, database (4 tabel + TTL), dan optimizer (dummy data, sorting, flags, multi-modal, first/last-mile).

---

## 7. Untuk Tim — Cara Implementasi Scraper Plane/Bus

Lihat **`scraper/plane_scraper.py`** dan **`scraper/bus_scraper.py`** — keduanya berisi docstring panduan lengkap. Ikuti pola di **`scraper/train_scraper.py`**:

1. Inherit dari `BaseScraper`, set `MODE = "flight"` / `"bus"`.
2. Implementasikan `_scrape()` yang return `List[TransportSegment]`.
3. Pakai `async_playwright()` (bukan Selenium — sudah migrasi).
4. Pakai `_human_behavior()` helper untuk anti-detection.
5. Test mandiri: `python scraper/plane_scraper.py`.

Setelah selesai, scraper otomatis aktif di app — tidak perlu ubah `app.py`.

---

## 8. Catatan Versi

- **v1.0** — Initial release. Train scraper jalan, plane/bus stub, database 4 tabel, weighted scoring, first/last-mile stub, 64 unit test.
- Migrasi penuh dari Selenium ke Playwright. `webdriver-manager` dan dependency Selenium sudah dihapus dari `requirements.txt`.

---

## 9. Lisensi

Project akademik untuk mata kuliah Pengembangan Komputasi Kreatif, Politeknik Negeri Bandung. Bukan untuk distribusi komersial.
