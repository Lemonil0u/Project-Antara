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
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from models import TransportSegment

logger = logging.getLogger(__name__)


# ── Kota yang punya layanan kereta ──────────────────────────────────────────
TRAIN_CITIES = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Cirebon", "Purwokerto",
}

# ── Kota yang punya bandara komersial ───────────────────────────────────────
FLIGHT_CITIES = {
    "Jakarta", "Surabaya", "Bali", "Medan", "Makassar",
    "Yogyakarta", "Semarang", "Bandung", "Batam", "Lombok",
    "Manado", "Padang", "Palembang", "Bandar Lampung", "Malang", "Denpasar",
}

# ── Kota Jawa untuk bus (default) + cross-pulau khusus ──────────────────────
BUS_JAWA = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang",
}
BUS_CROSS_PULAU = {("Surabaya", "Bali"), ("Bali", "Surabaya")}


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

        Identik dengan DummyDataGenerator.get_segments() — optimizer tidak
        perlu diubah saat dipindah dari dummy ke nyata.
        """
        requested_modes = modes or list(self._scrapers.keys())
        all_segments: List[TransportSegment] = []

        for mode, scraper in self._scrapers.items():
            if mode not in requested_modes:
                continue
            if not self._route_feasible(mode, origin, destination):
                logger.info(
                    f"[DataSource] Skip {mode}: rute {origin}→{destination} "
                    f"tidak tersedia untuk moda ini."
                )
                continue

            # ── Cek cache dulu ───────────────────────────────────────────────
            cached = self._get_from_cache(origin, destination, date_str, mode)
            if cached is not None:
                logger.info(f"[DataSource] {mode}: {len(cached)} segmen dari cache.")
                all_segments.extend(cached)
                continue

            # ── Cache miss → scrape ──────────────────────────────────────────
            logger.info(f"[DataSource] {mode} scrape: {origin}→{destination} ({date_str})")
            try:
                segs = scraper.get_segments(
                    origin=origin, destination=destination,
                    date_str=date_str, passengers=passengers,
                    modes=[mode],
                )
            except NotImplementedError:
                logger.info(f"[DataSource] {mode}: scraper belum diimplementasi, skip.")
                continue
            except Exception as e:
                logger.error(f"[DataSource] {mode}: scrape error: {e}")
                continue

            logger.info(f"[DataSource] {mode}: {len(segs)} segmen ditemukan.")
            all_segments.extend(segs)

            # Simpan ke cache jika ada hasil
            if segs and self.db is not None:
                self._save_to_cache(origin, destination, date_str, mode, segs)

        all_segments.sort(key=lambda s: s.departure_time)
        return all_segments

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
        """Validasi dasar apakah moda ini bisa beroperasi antara dua kota."""
        if mode == "train":
            return origin in TRAIN_CITIES and destination in TRAIN_CITIES
        if mode == "flight":
            return origin in FLIGHT_CITIES and destination in FLIGHT_CITIES
        if mode == "bus":
            if origin in BUS_JAWA and destination in BUS_JAWA:
                return True
            return (origin, destination) in BUS_CROSS_PULAU
        return True

    def __repr__(self) -> str:
        aktif = list(self._scrapers.keys())
        return (
            f"MultiModalDataSource(scrapers={aktif}, headless={self.headless}, "
            f"cache={'ON' if self.db else 'OFF'})"
        )
