"""
scraper/base_scraper.py — ANTARA Project
========================================
Abstract base class untuk semua scraper.

Kontrak:
  1. Setiap scraper HARUS mewarisi BaseScraper.
  2. Method _scrape() WAJIB diimplementasi — boleh sinkron atau wrapper async.
  3. Attribut kelas MODE WAJIB diisi: "flight" | "train" | "bus".
  4. Gunakan self.logger untuk logging (bukan print).
  5. Jangan biarkan exception meledak ke caller — sudah ditangkap di get_segments().

Catatan: project sudah pindah dari Selenium ke Playwright. Helper Selenium
yang lama sudah dihapus. Subclass bertanggung jawab membuka browser-nya
sendiri (lihat TrainScraper untuk contoh pola async Playwright).
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from models import TransportSegment

try:
    from config import SCRAPER_TIMEOUT as _DEFAULT_TIMEOUT, SCRAPER_HEADLESS as _DEFAULT_HEADLESS
except ImportError:
    _DEFAULT_TIMEOUT, _DEFAULT_HEADLESS = 30, True

# ── Setup logger sekali di module level ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


class BaseScraper(ABC):
    """
    Abstract base class untuk semua scraper ANTARA.

    Contoh implementasi minimal:
        class MyScraper(BaseScraper):
            MODE = "train"
            def _scrape(self, origin, destination, date_str, passengers):
                return [TransportSegment(...), ...]
    """

    # Subclass WAJIB set ini: "flight" | "train" | "bus"
    MODE: str = ""

    # Stasiun/bandara/terminal codes (subclass boleh extend)
    AIRPORT_CODES = {
        "Jakarta": "CGK", "Surabaya": "SUB", "Bali": "DPS",
        "Yogyakarta": "JOG", "Semarang": "SRG", "Medan": "KNO",
        "Makassar": "UPG", "Bandung": "BDO", "Lombok": "LOP",
        "Manado": "MDC", "Batam": "BTH", "Padang": "PDG",
        "Palembang": "PLM", "Malang": "MLG",
    }

    STATION_CODES = {
        "Jakarta": "GMR", "Surabaya": "SBI", "Yogyakarta": "YK",
        "Semarang": "SMT", "Bandung": "BD", "Malang": "ML",
        "Solo": "SLO", "Cirebon": "CN", "Purwokerto": "PWT",
    }

    def __init__(self, headless: bool = _DEFAULT_HEADLESS, timeout: int = _DEFAULT_TIMEOUT):
        """
        Args:
            headless : Jalankan browser tanpa UI (True untuk production).
            timeout  : Timeout per request dalam detik.
        """
        self.headless = headless
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC — Interface yang dipakai SmartRouteOptimizer
    # ─────────────────────────────────────────────────────────────────────────

    def get_segments(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int = 1,
        modes: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[TransportSegment]:
        """
        Ambil daftar TransportSegment untuk rute & tanggal tertentu.

        max_results: batas maksimal segmen yang dikembalikan per moda.
                     None = tidak ada limit (ambil semua di halaman).

        Interface ini identik dengan DummyDataGenerator.get_segments() dan
        MultiModalDataSource.get_segments() — optimizer tidak perlu tahu
        siapa yang melayani panggilannya.

        Returns:
            List[TransportSegment]. Bisa kosong jika tidak ada hasil atau
            jika scraping gagal (exception dicatat dan ditelan).
        """
        # Skip jika moda ini bukan tanggung jawab scraper ini
        if modes and self.MODE and self.MODE not in modes:
            return []

        self.logger.info(f"Scraping {self.MODE}: {origin} → {destination} ({date_str})"
                         + (f" [max {max_results}]" if max_results else ""))
        try:
            segments = self._scrape(origin, destination, date_str, passengers,
                                    max_results=max_results)
            self.logger.info(f"  ✓ {len(segments)} segmen ditemukan")
            return segments
        except NotImplementedError:
            # Re-raise NotImplementedError agar data_source bisa skip scraper ini
            raise
        except Exception as e:
            self.logger.error(f"  ✗ Scraping gagal: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    #  ABSTRACT — Wajib diimplementasi di subclass
    # ─────────────────────────────────────────────────────────────────────────

    @abstractmethod
    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
        max_results: Optional[int] = None,
    ) -> List[TransportSegment]:
        """
        Inti scraping — implementasi per moda transportasi.
        max_results: stop setelah menemukan N segmen unik (None = semua).
        Boleh raise NotImplementedError jika belum diimplementasi.
        """
        ...

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER — Bisa dipakai di subclass
    # ─────────────────────────────────────────────────────────────────────────

    def _city_to_code(self, city: str, mode: str) -> str:
        """Konversi nama kota ke kode bandara / stasiun."""
        if mode == "flight":
            return self.AIRPORT_CODES.get(city, city[:3].upper())
        if mode == "train":
            return self.STATION_CODES.get(city, city[:3].upper())
        return city
