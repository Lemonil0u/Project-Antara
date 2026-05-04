"""
engine/data_source.py — ANTARA Project
========================================
MultiModalDataSource: adapter layer yang menggabungkan semua scraper nyata
(TrainScraper, PlaneScraper, BusScraper) menjadi satu data source tunggal
dengan interface yang sama seperti DummyDataGenerator.

Cara pakai di optimizer / app.py:
    from engine.data_source import MultiModalDataSource
    optimizer = SmartRouteOptimizer(data_source=MultiModalDataSource())

Arsitektur:
  - Tiap scraper hanya dipanggil jika mode-nya termasuk dalam `modes` filter.
  - Hasil dari semua scraper digabung, diurutkan berdasarkan departure_time.
  - Jika scraper gagal (misal browser error), hasilnya kosong [] dan tidak crash.
  - Scraper yang belum tersedia (PlaneScraper/BusScraper) di-skip otomatis.
"""

import logging
from typing import List, Optional

from models import TransportSegment

logger = logging.getLogger(__name__)


# ── Set kota yang punya layanan kereta (sama dengan TRAIN_CITIES di optimizer) ─
TRAIN_CITIES = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Cirebon", "Purwokerto",
}


class MultiModalDataSource:
    """
    Data source nyata yang menggabungkan semua scraper.

    Interface identik dengan DummyDataGenerator — optimizer tidak perlu diubah.

    Args:
        headless        : Jalankan browser tanpa tampilan (True = production mode).
        timeout         : Timeout per request dalam detik.
        enabled_modes   : Daftar moda yang diaktifkan. Default semua.
                          Berguna saat pengembangan agar hanya kereta yang jalan.

    Contoh:
        # Hanya kereta (development)
        ds = MultiModalDataSource(enabled_modes=["train"])

        # Semua moda (production)
        ds = MultiModalDataSource()
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        enabled_modes: Optional[List[str]] = None,
    ):
        self.headless       = headless
        self.timeout        = timeout
        self.enabled_modes  = enabled_modes or ["train", "flight", "bus"]

        # Inisialisasi scraper yang tersedia
        self._scrapers = {}
        self._init_scrapers()

    # ─────────────────────────────────────────────────────────────────────────
    #  INISIALISASI SCRAPER
    # ─────────────────────────────────────────────────────────────────────────

    def _init_scrapers(self):
        """
        Load scraper yang tersedia. Jika scraper belum diimplementasi
        atau gagal import, di-skip tanpa crash.
        """
        if "train" in self.enabled_modes:
            try:
                from scraper.train_scraper import TrainScraper
                self._scrapers["train"] = TrainScraper(
                    headless=self.headless,
                    timeout=self.timeout,
                )
                logger.info("[DataSource] TrainScraper aktif.")
            except ImportError as e:
                logger.warning(f"[DataSource] TrainScraper tidak tersedia: {e}")

        if "flight" in self.enabled_modes:
            try:
                from scraper.plane_scraper import PlaneScraper
                self._scrapers["flight"] = PlaneScraper(
                    headless=self.headless,
                    timeout=self.timeout,
                )
                logger.info("[DataSource] PlaneScraper aktif.")
            except (ImportError, NotImplementedError) as e:
                logger.warning(f"[DataSource] PlaneScraper tidak tersedia: {e}")

        if "bus" in self.enabled_modes:
            try:
                from scraper.bus_scraper import BusScraper
                self._scrapers["bus"] = BusScraper(
                    headless=self.headless,
                    timeout=self.timeout,
                )
                logger.info("[DataSource] BusScraper aktif.")
            except (ImportError, NotImplementedError) as e:
                logger.warning(f"[DataSource] BusScraper tidak tersedia: {e}")

        if not self._scrapers:
            logger.error(
                "[DataSource] Tidak ada scraper yang berhasil diinisialisasi! "
                "Pastikan dependency (playwright, dll) sudah terinstall."
            )

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

        Identik dengan DummyDataGenerator.get_segments() — optimizer tidak perlu
        diubah sama sekali.

        Args:
            origin      : Kota asal, e.g. "Jakarta"
            destination : Kota tujuan, e.g. "Surabaya"
            date_str    : Format "YYYY-MM-DD"
            passengers  : Jumlah penumpang
            modes       : Filter moda; None = pakai semua scraper yang aktif

        Returns:
            List[TransportSegment] gabungan dari semua scraper, urut departure_time.
        """
        requested_modes = modes or list(self._scrapers.keys())
        all_segments: List[TransportSegment] = []

        for mode, scraper in self._scrapers.items():
            # Skip jika mode ini tidak diminta
            if mode not in requested_modes:
                continue

            # Skip rute yang tidak masuk akal untuk moda ini
            if not self._route_feasible(mode, origin, destination):
                logger.info(
                    f"[DataSource] Skip {mode}: rute {origin}→{destination} "
                    f"tidak tersedia untuk moda ini."
                )
                continue

            logger.info(f"[DataSource] Memanggil {mode} scraper: {origin}→{destination} ({date_str})")
            segs = scraper.get_segments(
                origin=origin,
                destination=destination,
                date_str=date_str,
                passengers=passengers,
                modes=[mode],
            )
            logger.info(f"[DataSource] {mode} scraper: {len(segs)} segmen ditemukan.")
            all_segments.extend(segs)

        # Urutkan berdasarkan waktu keberangkatan
        all_segments.sort(key=lambda s: s.departure_time)
        return all_segments

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE
    # ─────────────────────────────────────────────────────────────────────────

    def _route_feasible(self, mode: str, origin: str, destination: str) -> bool:
        """
        Validasi dasar apakah rute ini masuk akal untuk moda tertentu.
        Mencegah scraper kereta dipanggil untuk rute Jakarta-Bali, misalnya.
        """
        if mode == "train":
            return origin in TRAIN_CITIES and destination in TRAIN_CITIES

        if mode == "flight":
            # PlaneScraper punya validasinya sendiri, tapi filter awal di sini
            # mencegah pemanggilan yang pasti gagal
            return True  # Biarkan PlaneScraper yang memfilter

        if mode == "bus":
            jawa = {
                "Jakarta", "Bandung", "Semarang", "Yogyakarta",
                "Solo", "Surabaya", "Malang",
            }
            if origin in jawa and destination in jawa:
                return True
            cross_pulau = {("Surabaya", "Bali"), ("Bali", "Surabaya")}
            return (origin, destination) in cross_pulau

        return True

    def __repr__(self) -> str:
        aktif = list(self._scrapers.keys())
        return f"MultiModalDataSource(scrapers={aktif}, headless={self.headless})"