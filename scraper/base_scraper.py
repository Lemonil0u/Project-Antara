"""
scraper/base_scraper.py — ANTARA Project
==========================================
Abstract base class untuk semua scraper.

WAJIB DIBACA sebelum implementasi plane_scraper, train_scraper, bus_scraper.

Aturan:
  1. Setiap scraper HARUS mewarisi BaseScraper.
  2. Method get_segments() WAJIB diimplementasi — ini kontrak dengan optimizer.
  3. Method _scrape() adalah inti scraping, bebas diimplementasi sesuai target site.
  4. Gunakan self.logger untuk logging, jangan pakai print().
  5. Tangani exception di dalam kelas, jangan biarkan meledak ke caller.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from models import TransportSegment


class BaseScraper(ABC):
    """
    Abstract base class untuk semua scraper ANTARA.

    Usage:
        class PlaneScraper(BaseScraper):
            MODE = "flight"

            def _scrape(self, origin, destination, date_str, passengers):
                # ... implementasi selenium ...
                return [TransportSegment(...), ...]
    """

    # Subclass WAJIB set ini: "flight" | "train" | "bus"
    MODE: str = ""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Args:
            headless : Jalankan browser tanpa UI (True untuk production).
            timeout  : Timeout per request dalam detik.
        """
        self.headless = headless
        self.timeout  = timeout
        self.logger   = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(
            level  = logging.INFO,
            format = "[%(asctime)s] %(name)s — %(message)s",
            datefmt= "%H:%M:%S",
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC — Interface yang dipakai SmartRouteOptimizer
    # ─────────────────────────────────────────────────────────────────────────

    def get_segments(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int = 1,
        modes: Optional[list] = None,
    ) -> list[TransportSegment]:
        """
        Ambil daftar TransportSegment untuk rute dan tanggal tertentu.

        Interface ini IDENTIK dengan DummyDataGenerator.get_segments() —
        jadi optimizer tidak perlu diubah saat scraper sudah jadi.

        Args:
            origin      : Kota asal, e.g. "Jakarta"
            destination : Kota tujuan, e.g. "Surabaya"
            date_str    : Format "YYYY-MM-DD"
            passengers  : Jumlah penumpang
            modes       : Filter moda; None = ambil semua yang relevan

        Returns:
            List[TransportSegment], bisa kosong jika tidak ada hasil.
        """
        # Kalau moda ini bukan tanggung jawab scraper ini, kembalikan []
        if modes and self.MODE and self.MODE not in modes:
            return []

        self.logger.info(f"Scraping {self.MODE}: {origin} → {destination} ({date_str})")
        try:
            segments = self._scrape(origin, destination, date_str, passengers)
            self.logger.info(f"  ✓ {len(segments)} segmen ditemukan")
            return segments
        except Exception as e:
            self.logger.error(f"  ✗ Scraping gagal: {e}")
            return []   # Kembalikan list kosong, jangan crash

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
    ) -> list[TransportSegment]:
        """
        Inti scraping — implementasi per moda transportasi.

        Wajib return List[TransportSegment].
        Boleh raise exception; akan ditangkap oleh get_segments().
        """
        ...

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER — Bisa dipakai di subclass
    # ─────────────────────────────────────────────────────────────────────────

    def _make_driver(self):
        """
        Buat instance Selenium WebDriver.
        Gunakan ini di _scrape() setiap scraper.

        TODO: Install chromedriver via webdriver-manager.
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        opts = Options()
        if self.headless:
            opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        # User agent agar tidak terdeteksi sebagai bot
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts,
        )
        driver.set_page_load_timeout(self.timeout)
        return driver

    def _city_to_code(self, city: str, mode: str) -> str:
        """
        Konversi nama kota ke kode bandara/stasiun.
        Extend tabel ini sesuai kebutuhan.
        """
        airport_codes = {
            "Jakarta":    "CGK",
            "Surabaya":   "SUB",
            "Bali":       "DPS",
            "Yogyakarta": "JOG",
            "Semarang":   "SRG",
            "Medan":      "KNO",
            "Makassar":   "UPG",
            "Bandung":    "BDO",
            "Lombok":     "LOP",
            "Manado":     "MDC",
            "Batam":      "BTH",
            "Padang":     "PDG",
            "Palembang":  "PLM",
            "Malang":     "MLG",
        }
        train_codes = {
            "Jakarta":    "GMR",   # Gambir
            "Surabaya":   "SBI",   # Surabaya Gubeng
            "Yogyakarta": "YK",
            "Semarang":   "SMT",
            "Bandung":    "BD",
            "Malang":     "ML",
            "Solo":       "SLO",
        }
        if mode == "flight":
            return airport_codes.get(city, city[:3].upper())
        elif mode == "train":
            return train_codes.get(city, city[:3].upper())
        return city
