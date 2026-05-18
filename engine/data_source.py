"""
engine/data_source.py — ANTARA Project
======================================
MultiModalDataSource: adapter yang menggabungkan semua scraper Playwright
(TrainScraper, PlaneScraper, BusScraper) menjadi satu interface yang sama
seperti DummyDataGenerator.

Fitur:
  - Lazy init scraper — yang gagal import / NotImplementedError di-skip.
  - Filter rute geografis dasar (kereta hanya untuk kota di jalur KA).
  - Opsional: integrasi DatabaseManager untuk price cache (hindari rescrape).

Cara pakai:
    from engine.data_source import MultiModalDataSource
    ds = MultiModalDataSource(enabled_modes=["train"])
    optimizer = SmartRouteOptimizer(data_source=ds)

Dengan cache:
    from database import DatabaseManager
    db = DatabaseManager()
    ds = MultiModalDataSource(db=db, cache_ttl_minutes=60)
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from models import TransportSegment

logger = logging.getLogger(__name__)


# ── Kota yang punya layanan kereta ──────────────────────────────────────────
# Note: Ini hanya "known cities" — kota tidak terdaftar TETAP dicoba (soft filter)
TRAIN_CITIES = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Cirebon", "Purwokerto",
    "Bogor", "Tegal", "Pekalongan", "Madiun", "Kediri",
}

# ── Kota yang punya bandara komersial ───────────────────────────────────────
FLIGHT_CITIES = {
    "Jakarta", "Surabaya", "Bali", "Denpasar", "Medan", "Makassar",
    "Yogyakarta", "Semarang", "Bandung", "Batam", "Lombok",
    "Manado", "Padang", "Palembang", "Bandar Lampung", "Malang",
    "Balikpapan", "Pontianak", "Banjarmasin", "Pekanbaru", "Jayapura",
    "Ambon", "Kupang", "Solo", "Banda Aceh",
}

# ── Kota Jawa untuk bus (default) + cross-pulau khusus ──────────────────────
BUS_JAWA = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Bogor", "Cirebon",
}
BUS_CROSS_PULAU = {
    ("Surabaya", "Bali"), ("Bali", "Surabaya"),
    ("Surabaya", "Denpasar"), ("Denpasar", "Surabaya"),
}

# ── Kota-kota Jawa (untuk fallback heuristic train) ─────────────────────────
JAWA_REGION = {
    "Jakarta", "Bogor", "Depok", "Tangerang", "Bekasi", "Bandung",
    "Cirebon", "Tegal", "Pekalongan", "Semarang", "Solo", "Yogyakarta",
    "Madiun", "Kediri", "Malang", "Surabaya", "Purwokerto",
}


class MultiModalDataSource:
    """
    Data source nyata yang menggabungkan semua scraper.
    Interface identik dengan DummyDataGenerator.get_segments().
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        enabled_modes: Optional[List[str]] = None,
        db=None,                       # Optional DatabaseManager untuk cache
        cache_ttl_minutes: int = 60,   # Berapa lama cache valid
    ):
        self.headless           = headless
        self.timeout            = timeout
        self.enabled_modes      = enabled_modes or ["train", "flight", "bus"]
        self.db                 = db
        self.cache_ttl_minutes  = cache_ttl_minutes

        self._scrapers = {}
        self._init_scrapers()

    # ─────────────────────────────────────────────────────────────────────────
    #  INISIALISASI SCRAPER
    # ─────────────────────────────────────────────────────────────────────────

    def _init_scrapers(self):
        """Load scraper yang tersedia. Skip jika gagal import / NotImplemented."""
        if "train" in self.enabled_modes:
            self._try_load("train", "scraper.train_scraper", "TrainScraper")
        if "flight" in self.enabled_modes:
            self._try_load("flight", "scraper.plane_scraper", "PlaneScraper")
        if "bus" in self.enabled_modes:
            self._try_load("bus", "scraper.bus_scraper", "BusScraper")

        if not self._scrapers:
            logger.warning(
                "[DataSource] Tidak ada scraper yang berhasil diinisialisasi. "
                "Pastikan playwright sudah terinstall: `pip install playwright && playwright install chromium`"
            )
        else:
            logger.info(f"[DataSource] Scraper aktif: {list(self._scrapers.keys())}")

    def _try_load(self, mode: str, module_path: str, class_name: str) -> None:
        """Load satu scraper. Skip diam jika belum siap."""
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            self._scrapers[mode] = cls(headless=self.headless, timeout=self.timeout)
            logger.info(f"[DataSource] {class_name} aktif.")
        except (ImportError, AttributeError) as e:
            logger.warning(f"[DataSource] {class_name} gagal load: {e}")
        except Exception as e:
            logger.warning(f"[DataSource] {class_name} error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC — Interface untuk SmartRouteOptimizer
    # ─────────────────────────────────────────────────────────────────────────

    def get_segments(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int = 1,
        modes: Optional[List[str]] = None,
    ) -> List[TransportSegment]:
        """
        Ambil semua TransportSegment dari semua scraper yang relevan.
        
        Optimasi: scraping berjalan PARALEL menggunakan thread pool.
        Train + flight dijalankan bersamaan, jadi total waktu ≈ max(train, flight),
        bukan train + flight.

        Identik dengan DummyDataGenerator.get_segments() — optimizer tidak
        perlu diubah saat dipindah dari dummy ke nyata.
        """
        requested_modes = modes or list(self._scrapers.keys())
        all_segments: List[TransportSegment] = []

        # ── Bangun list task yang perlu di-scrape (cache miss) ──────────────
        scrape_tasks = []   # list of (mode, scraper)
        for mode, scraper in self._scrapers.items():
            if mode not in requested_modes:
                continue
            if not self._route_feasible(mode, origin, destination):
                logger.info(
                    f"[DataSource] Skip {mode}: rute {origin}→{destination} "
                    f"tidak tersedia untuk moda ini."
                )
                continue

            # ── Cek cache dulu (sequential — cepat) ──────────────────────────
            cached = self._get_from_cache(origin, destination, date_str, mode)
            if cached is not None:
                logger.info(f"[DataSource] {mode}: {len(cached)} segmen dari cache.")
                all_segments.extend(cached)
                continue

            # Cache miss → masuk antrian untuk scraping paralel
            scrape_tasks.append((mode, scraper))

        # ── Jalankan semua scraper yang cache-miss SECARA PARALEL ───────────
        if scrape_tasks:
            logger.info(
                f"[DataSource] Scraping paralel: {[m for m, _ in scrape_tasks]} "
                f"untuk {origin}→{destination} ({date_str})"
            )
            with ThreadPoolExecutor(max_workers=len(scrape_tasks)) as pool:
                # Submit semua scraper ke thread pool
                future_to_mode = {
                    pool.submit(
                        self._safe_scrape, scraper, origin, destination,
                        date_str, passengers, mode,
                    ): mode
                    for mode, scraper in scrape_tasks
                }

                # Tunggu hasil satu per satu, urutan tergantung mana yang selesai duluan
                for future in as_completed(future_to_mode):
                    mode = future_to_mode[future]
                    try:
                        segs = future.result()
                    except Exception as e:
                        logger.error(f"[DataSource] {mode}: future error: {e}")
                        continue

                    if segs is None:
                        # NotImplementedError atau error fatal — sudah dilog di _safe_scrape
                        continue

                    logger.info(f"[DataSource] {mode}: {len(segs)} segmen ditemukan.")
                    all_segments.extend(segs)

                    # Simpan ke cache jika ada hasil
                    if segs and self.db is not None:
                        self._save_to_cache(origin, destination, date_str, mode, segs)

        all_segments.sort(key=lambda s: s.departure_time)
        return all_segments

    def _safe_scrape(
        self,
        scraper,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
        mode: str,
    ) -> Optional[List[TransportSegment]]:
        """
        Wrapper aman untuk satu scraper call.
        
        Return None jika error fatal (NotImplementedError, exception).
        Return list of segments jika sukses (mungkin empty list).
        Dipakai oleh ThreadPoolExecutor.
        """
        try:
            return scraper.get_segments(
                origin=origin, destination=destination,
                date_str=date_str, passengers=passengers,
                modes=[mode],
            )
        except NotImplementedError:
            logger.info(f"[DataSource] {mode}: scraper belum diimplementasi, skip.")
            return None
        except Exception as e:
            logger.error(f"[DataSource] {mode}: scrape error: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Cache helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_from_cache(
        self,
        origin: str,
        destination: str,
        date_str: str,
        mode: str,
    ) -> Optional[List[TransportSegment]]:
        if self.db is None:
            return None
        cached = self.db.get_cached_segments(
            origin=origin, destination=destination,
            date=date_str, mode=mode,
            max_age_minutes=self.cache_ttl_minutes,
        )
        if cached is None:
            return None
        try:
            return [self._dict_to_segment(d) for d in cached]
        except Exception as e:
            logger.warning(f"[DataSource] Cache parse error: {e}")
            return None

    def _save_to_cache(
        self,
        origin: str,
        destination: str,
        date_str: str,
        mode: str,
        segments: List[TransportSegment],
    ) -> None:
        try:
            payload = [self._segment_to_dict(s) for s in segments]
            self.db.cache_segments(
                origin=origin, destination=destination,
                date=date_str, mode=mode,
                segments=payload,
            )
        except Exception as e:
            logger.warning(f"[DataSource] Cache save error: {e}")

    @staticmethod
    def _segment_to_dict(seg: TransportSegment) -> dict:
        """Konversi segment → dict JSON-serializable."""
        d = asdict(seg)
        d["departure_time"] = seg.departure_time.isoformat()
        d["arrival_time"]   = seg.arrival_time.isoformat()
        return d

    @staticmethod
    def _dict_to_segment(d: dict) -> TransportSegment:
        """Konversi dict → segment. Reverse dari _segment_to_dict()."""
        return TransportSegment(
            id               = d["id"],
            mode             = d["mode"],
            provider         = d["provider"],
            provider_code    = d.get("provider_code"),
            origin           = d["origin"],
            destination      = d["destination"],
            departure_time   = datetime.fromisoformat(d["departure_time"]),
            arrival_time     = datetime.fromisoformat(d["arrival_time"]),
            duration_minutes = d["duration_minutes"],
            price            = float(d["price"]),
            seat_class       = d.get("seat_class"),
            available_seats  = d.get("available_seats"),
            rating           = d.get("rating"),
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Filter rute
    # ─────────────────────────────────────────────────────────────────────────

    def _route_feasible(self, mode: str, origin: str, destination: str) -> bool:
        """
        Filter rute - SOFT filter (hanya block yang jelas tidak mungkin).

        Logika:
          - TRAIN: hanya di pulau Jawa. Kota di luar Jawa = block firm.
                   Kota tidak dikenal = boleh coba (mungkin kota kecil di Jawa).
          - FLIGHT: hampir semua kota besar punya bandara → selalu coba.
          - BUS  : Jawa + cross-pulau Surabaya-Bali. Lainnya tetap coba.

        Tujuan: rute baru otomatis bekerja TANPA harus declare di whitelist.
        """
        # Daftar kota TIDAK di Jawa (untuk firm-block kereta)
        NON_JAWA = {
            "Bali", "Denpasar", "Medan", "Makassar", "Lombok", "Padang",
            "Palembang", "Manado", "Batam", "Balikpapan", "Pontianak",
            "Banjarmasin", "Pekanbaru", "Jayapura", "Ambon", "Kupang",
            "Banda Aceh", "Bandar Lampung",
        }

        # ── TRAIN: firm-block kalau salah satu kota jelas-jelas di luar Jawa
        if mode == "train":
            if origin in NON_JAWA or destination in NON_JAWA:
                return False
            return True  # Kalau dua-duanya di Jawa atau unknown → coba

        # ── FLIGHT: hampir semua kota besar punya bandara, jadi selalu coba
        if mode == "flight":
            return True

        # ── BUS: Jawa + cross-pulau khusus. Lainnya tetap coba (soft)
        if mode == "bus":
            # Lintas pulau jauh (e.g. Jakarta → Papua) → block
            if origin in {"Jayapura", "Ambon", "Kupang"} or \
               destination in {"Jayapura", "Ambon", "Kupang"}:
                return False
            return True

        return True

    def __repr__(self) -> str:
        aktif = list(self._scrapers.keys())
        return (
            f"MultiModalDataSource(scrapers={aktif}, headless={self.headless}, "
            f"cache={'ON' if self.db else 'OFF'})"
        )
