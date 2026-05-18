# ANTARA — Multi-Modal Transportation Price Comparison

[![Made with Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/)

> **Pengembangan Komputasi Kreatif** — Politeknik Negeri Bandung — 2026
> Dosen Pembimbing: **Beri Noviansyah**
> Tim: **Lunaraya, Nesya, Nurul, Umarwa**

---

## 1. Tentang ANTARA

ANTARA adalah aplikasi web berbasis Streamlit yang **membandingkan harga dan durasi tiket kereta dan pesawat** untuk perjalanan antar-kota di Indonesia secara real-time melalui web scraping. ANTARA bukan agregator booking — fokusnya pada **analisis dan rekomendasi rute terbaik**, termasuk rute multi-modal (gabungan kereta + pesawat) yang sering tidak tersedia di OTA konvensional.

### Fitur Utama

- **🔍 Pencarian multi-modal** — kombinasi kereta + pesawat dengan transit otomatis (maks. 2 transit). Contoh: Jakarta → Surabaya (kereta) → Denpasar (pesawat).
- **🔄 Real-time scraping** — data langsung dari Traveloka (kereta via KAI) dan tiket.com (pesawat), berjalan paralel untuk efisiensi waktu.
- **⚡ Price cache** — hasil scraping disimpan ke SQLite. Pencarian rute yang sama dalam 60 menit tidak melakukan scraping ulang.
- **📊 Sort By** — user bisa pilih prioritas: Cheapest (kereta sering menang), Fastest (pesawat sering menang), atau Best Value (weighted 60% harga + 40% durasi).
- **📈 Visualisasi interaktif** — scatter plot harga vs durasi, tren harga per jam keberangkatan, dan rating comparison antar operator.
- **⭐ Saved Routes** — simpan rute favorit ke database lokal.
- **🕐 Riwayat pencarian** — setiap pencarian otomatis tersimpan ke SQLite.

### Status Implementasi

| Komponen | Status | Keterangan |
|---|---|---|
| TrainScraper (Traveloka KAI) | ✅ Berfungsi | Playwright async, anti-detection, multi-strategy parser |
| PlaneScraper (tiket.com) | ✅ Berfungsi | Playwright async, deduplikasi, parser maskapai + harga |
| BusScraper (tiket.com) | ✅ Berfungsi | Playwright async, anti-detection, durasi otomatis, parser operator + harga diskon |
| Smart Route Optimizer | ✅ Berfungsi | Weighted scoring, multimodal via transit hub, city alias |
| Price Cache (SQLite) | ✅ Berfungsi | TTL 60 menit, terintegrasi di loading + visualization |
| Database (4 tabel) | ✅ Berfungsi | search_history, user_preferences, price_cache, saved_routes |
| Parallel Scraping | ✅ Berfungsi | ThreadPoolExecutor, train + flight scrape bersamaan |
| Sort By Dropdown | ✅ Berfungsi | Cheapest / Fastest / Best Value |
| Visualization | ✅ Berfungsi | Pakai cache jika rute sama, scrape ulang jika beda |
| First-mile / Last-mile | 🧪 Stub | Arsitektur siap di `engine/local_data.py`, belum real scraping |
| Unit test | ✅ 63 test passing | models, database (4 tabel + TTL cache), optimizer pipeline |

---

## 2. Instalasi

### Prasyarat

- Python **3.10 atau lebih baru**
- pip
- Koneksi internet (untuk install Playwright Chromium ~170 MB dan untuk scraping)

### Langkah

```bash
# 1. Clone repo
git clone <url-repo>
cd ANTARA_PROJECT/

# 2. (Disarankan) buat virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install browser Chromium untuk Playwright
playwright install chromium

# 5. Jalankan aplikasi
streamlit run app.py
```

App akan terbuka di **http://localhost:8501**.

### Login Demo

Gunakan akun berikut untuk mencoba aplikasi tanpa registrasi:
- **Email:** `admin@antara.com`
- **Password:** `123`

---

## 3. Struktur Project

```
ANTARA_PROJECT/
├── app.py                        # Landing page + modal login/signup
├── models.py                     # Dataclass: LocalSegment, TransportSegment,
│                                 # RouteCombo, SearchCriteria, OptimizerResult
├── requirements.txt              # Dependencies (Playwright, Streamlit, Plotly)
├── style.css                     # Design system (warna, card, button, scrollbar)
├── README.md                     # File ini
│
├── database/
│   ├── __init__.py
│   └── database.py               # DatabaseManager — SQLite 4 tabel + full CRUD
│
├── engine/
│   ├── __init__.py
│   ├── optimizer.py              # SmartRouteOptimizer, DummyDataGenerator,
│   │                             # TRANSIT_HUBS, CITY_ALIASES, weighted scoring
│   ├── data_source.py            # MultiModalDataSource — parallel scraping +
│   │                             # price cache + soft route filter
│   ├── local_data.py             # LocalSegmentGenerator (first/last-mile stub)
│   └── visualizer.py             # Builder chart Plotly (modul mandiri)
│
├── scraper/
│   ├── __init__.py
│   ├── base_scraper.py           # Abstract base class, AIRPORT_CODES, STATION_CODES
│   ├── train_scraper.py          # ✅ Traveloka KAI — Playwright async
│   ├── plane_scraper.py          # ✅ tiket.com — Playwright async
│   └── bus_scraper.py            # ✅ tiket.com — Playwright async
│
├── pages/
│   ├── components/
│   │   ├── sidebar.py            # Sidebar navigasi
│   │   └── theme.py              # Tema global
│   ├── dashboard.py              # Halaman hasil pencarian + filter + sort
│   ├── loading.py                # Halaman loading saat scraping berjalan
│   ├── result.py                 # Detail rute yang dipilih
│   ├── visualization.py          # Chart perbandingan harga, durasi, rating
│   ├── favorite_routes.py        # Rute tersimpan
│   ├── profile.py                # Profil user
│   ├── settings.py               # Pengaturan aplikasi
│   ├── login.py                  # Halaman login
│   └── signup.py                 # Halaman registrasi
│
├── tests/
│   ├── test_models.py            # 23 test dataclass
│   ├── test_database.py          # 25 test DB (4 tabel + TTL cache)
│   └── test_optimizer.py        # 15 test optimizer + multimodal + local
│
├── assets/                       # Gambar UI (logo, ilustrasi moda transportasi)
└── data/                         # SQLite DB (otomatis dibuat saat pertama run)
    └── antara.db
```

---

## 4. Alur Aplikasi

```
Landing Page (app.py)
    │
    ├── Login / Sign Up → Dashboard
    │
    └── Search Routes → Loading (pages/loading.py)
                              │
                              ├── Scraping paralel: TrainScraper + PlaneScraper
                              ├── Simpan hasil ke session_state + SQLite cache
                              └── Redirect ke Dashboard (pages/dashboard.py)
                                        │
                                        ├── Filter: moda, harga, airlines
                                        ├── Sort: Cheapest / Fastest / Best Value
                                        └── Select → Result (pages/result.py)
```

---

## 5. Cara Kerja: Smart Route Optimizer

### 5.1 Pipeline pencarian

```
SearchCriteria → SmartRouteOptimizer.optimize()
                        │
                        ▼
              MultiModalDataSource.get_segments()
              (parallel: TrainScraper + PlaneScraper)
                        │
                        ▼
              List[TransportSegment]
                        │
         ┌──────────────┼──────────────────────┐
         ▼              ▼                      ▼
    Rute Langsung  Rute Transit-1       Rute Transit-2
    (1 segmen)     (2 segmen)           (3 segmen, max)
         │              │                      │
         └──────┬────────┴──────────────────────┘
                ▼
         Dedup → Sort (by user preference) → OptimizerResult
```

### 5.2 Constraint multi-modal

- **Maks. transit:** 2 kota transit (maks. 3 leg per rute)
- **Min. waiting time per transfer:** 60 menit
- **Maks. waiting time per transfer:** 300 menit
- Combo di luar rentang ini otomatis di-drop

### 5.3 Opsi Sort By

User memilih sendiri prioritas di dropdown filter:

| Pilihan | Cara kerja | Biasanya menang |
|---|---|---|
| **Cheapest** | `sort(price_raw)` murni | Kereta |
| **Fastest** | `sort(duration_minutes)` murni | Pesawat |
| **Best Value** | `0.6 × normalized_price + 0.4 × normalized_duration` | Mix |

### 5.4 City Alias & Transit Hub

Kota yang punya nama alternatif (Denpasar = Bali) otomatis di-resolve via `CITY_ALIASES`. Kota yang belum terdaftar di `TRANSIT_HUBS` tetap dicoba scraping-nya menggunakan `DEFAULT_TRANSIT_HUBS` sebagai fallback — tidak perlu declare manual untuk setiap kota baru.

### 5.5 Price Cache

```
Request pencarian
    │
    ├── Cek SQLite (TTL 60 menit)
    │       │
    │       ├── Cache HIT  → langsung return data (< 1 detik)
    │       └── Cache MISS → scraping → simpan ke cache → return data
    └──────────────────────────────────────────────────────────────────
```

---

## 6. Database

Path default: `data/antara.db` (otomatis dibuat saat pertama run).

### Skema

| Tabel | Tujuan | Kolom utama |
|---|---|---|
| `search_history` | Riwayat pencarian user | origin, destination, date, best_route_combo_json, searched_at |
| `user_preferences` | Preferensi user (key-value JSON) | key, value_json, updated_at |
| `price_cache` | Cache hasil scraping (TTL 60 menit) | cache_key, segments_json, cached_at |
| `saved_routes` | Bookmark rute favorit | combo_id, route_label, total_price, notes, starred |

---

## 7. Testing

```bash
# Jalankan semua unit test
pytest tests/ -v

# Smoke test individual komponen (tanpa jalankan Streamlit)
python -m engine.optimizer      # demo dummy data → combos Jakarta-Surabaya
python -m database.database     # smoke test CRUD semua 4 tabel
python -m engine.local_data     # demo estimasi first/last-mile
```

Coverage saat ini: **63 unit test passing** — models (23), database (25), optimizer (15).

---

## 8. Untuk Tim: Implementasi Bus Scraper

File `scraper/bus_scraper.py` sudah berisi arsitektur dan panduan implementasi. Ikuti pola `scraper/plane_scraper.py`:

1. Inherit dari `BaseScraper`, pastikan `MODE = "bus"` sudah ada.
2. Implementasi `_scrape_async()` dengan Playwright async.
3. Target site: **RedBus Indonesia** (`https://www.redbus.id/bus-tickets/{origin}-to-{dest}`). Mapping slug sudah ada di `REDBUS_SLUGS` di file tersebut.
4. Parse: nama PO bus, jam berangkat/tiba, harga, tipe kursi.
5. Return `List[TransportSegment]` dengan `mode="bus"`.
6. Test mandiri: `python scraper/bus_scraper.py`.

Setelah selesai, aktifkan di `app.py` dan `pages/loading.py`:
```python
# Ganti:
enabled_modes=["train", "flight"]
# Jadi:
enabled_modes=["train", "flight", "bus"]
```

---

## 9. Catatan Versi

### v1.1 (Mei 2026) — Current
- PlaneScraper diimplementasi penuh (tiket.com, Playwright async)
- Parallel scraping via ThreadPoolExecutor
- Price cache SQLite terintegrasi di loading + visualization
- Sort By dropdown: Cheapest / Fastest / Best Value
- Bug fix: DuplicateElementKey tombol Select, fastest card salah sort string, tanggal header ikut widget, redirect ke landing setelah loading
- Visualization: ganti dummy data dengan real scraping + cache logic

### v1.0 (Mei 2026)
- Initial release
- TrainScraper berfungsi (Traveloka KAI)
- Database 4 tabel (SQLite)
- Smart Route Optimizer dengan weighted scoring
- Migrasi dari Selenium ke Playwright

---

## 10. Lisensi

Project akademik untuk mata kuliah Pengembangan Komputasi Kreatif, Politeknik Negeri Bandung 2026. Tidak untuk distribusi komersial.
