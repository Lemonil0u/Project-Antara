# ANTARA 🛫🚂🚌
**Multi-Modal Transportation Price Comparison Dashboard**

> Proyek I — Pengembangan Perangkat Lunak Desktop  
> D4 Teknik Informatika · Politeknik Negeri Bandung · 2026

---

## 👥 Tim

| Nama | NIM | Jobdesk |
|---|---|---|
| Lunaraya Zenithra Al Aulia Hudaya | 251524074 | Frontend (UI/Pages) |
| Nesya Fadillah Kinantiasa | 251524081 | Backend (Scraper) |
| Nurul Salmahat | 251524083 | Backend (Scraper) |
| Umarwa Muhammad Shellozanof | 251524092 | Engine + Database |

---

## 🗂️ Struktur Project

```
ANTARA_PROJECT/
│
├── app.py              ← Entry point Streamlit (jalankan ini!)
├── models.py           ← Definisi dataclass: TransportSegment, RouteCombo, dst.
├── database.py         ← SQLite CRUD: saved routes, history, user preferences
│
├── scraper/            ← Modul pengambil data (Jobdesk: Nesya & Nurul)
│   ├── __init__.py
│   ├── base_scraper.py ← Abstract base class, WAJIB diikuti semua scraper
│   ├── plane_scraper.py
│   ├── train_scraper.py
│   └── bus_scraper.py
│
├── engine/             ← Logika bisnis (Jobdesk: Umarwa)
│   ├── __init__.py
│   ├── optimizer.py    ← Smart Route Optimizer ✅ SUDAH ADA
│   └── visualizer.py  ← Plotly chart builder
│
├── assets/             ← Logo, CSS, gambar
├── data/               ← File .db SQLite dan cache sementara
│
└── tests/              ← Unit test (jalankan sebelum push!)
    ├── __init__.py
    ├── test_optimizer.py
    ├── test_models.py
    └── test_database.py
```

---

## ⚙️ Setup & Instalasi

### 1. Clone repo
```bash
git clone <url-repo-kalian>
cd ANTARA_PROJECT
```

### 2. Buat virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Cara Menjalankan Aplikasi

```bash
# Pastikan virtual environment aktif
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser: `http://localhost:8501`

---

## 🧪 Cara Testing

### Jalankan semua test sekaligus
```bash
# Dari root folder project
python -m pytest tests/ -v
```

### Jalankan test per file
```bash
python -m pytest tests/test_optimizer.py -v
python -m pytest tests/test_models.py -v
python -m pytest tests/test_database.py -v
```

### Jalankan optimizer secara manual (quick check)
```bash
python engine/optimizer.py
```
Output yang diharapkan: daftar route combo Jakarta → Surabaya dengan flag 💰 Terhemat dan ⚡ Tercepat.

### Jalankan scraper secara manual (saat sudah diimplementasi)
```bash
python scraper/plane_scraper.py
python scraper/train_scraper.py
python scraper/bus_scraper.py
```

---

## 🔗 Kontrak Antar Modul

### Scraper → Optimizer
Setiap scraper **wajib** mengimplementasikan method ini:
```python
def get_segments(
    self,
    origin: str,
    destination: str,
    date_str: str,        # format: "YYYY-MM-DD"
    passengers: int = 1,
    modes: list = None,
) -> list[TransportSegment]:
    ...
```
Selama interface ini diikuti, optimizer tidak perlu diubah sama sekali.

### Optimizer → Visualizer
```python
result: OptimizerResult = optimizer.optimize(criteria)
# Langsung dioper ke visualizer:
fig = visualizer.scatter_price_vs_duration(result.all_combos)
```

### Optimizer → app.py (Streamlit)
```python
from engine.optimizer import SmartRouteOptimizer
from models import SearchCriteria

optimizer = SmartRouteOptimizer()   # pakai DummyData sampai scraper jadi
criteria  = SearchCriteria("Jakarta", "Surabaya", "2026-05-10", passengers=2)
result    = optimizer.optimize(criteria)

# result.all_combos    → list RouteCombo untuk tabel
# result.cheapest      → card "Rute Terhemat"
# result.fastest       → card "Rute Tercepat"
# result.summary()     → string ringkasan
```

---

## 📋 Status Implementasi

| Komponen | File | Status |
|---|---|---|
| Data Models | `models.py` | ✅ Selesai |
| Smart Route Optimizer | `engine/optimizer.py` | ✅ Selesai (dummy data) |
| Dummy Data Generator | `engine/optimizer.py` | ✅ Selesai |
| Plane Scraper | `scraper/plane_scraper.py` | 🔧 TODO |
| Train Scraper | `scraper/train_scraper.py` | 🔧 TODO |
| Bus Scraper | `scraper/bus_scraper.py` | 🔧 TODO |
| Visualizer | `engine/visualizer.py` | 🔧 TODO |
| Database | `database.py` | 🔧 TODO |
| Streamlit App | `app.py` | 🔧 TODO |
| Unit Tests | `tests/` | 🟡 Partial |

---

## 📦 Tech Stack

- **Frontend/UI**: Streamlit
- **Charts**: Plotly
- **Scraping**: Selenium / Puppeteer (via pyppeteer)
- **Database**: SQLite (via sqlite3 bawaan Python)
- **Testing**: pytest
