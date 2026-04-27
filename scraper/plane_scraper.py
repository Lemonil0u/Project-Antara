"""
scraper/plane_scraper.py — ANTARA Project
===========================================
Scraper untuk data penerbangan dari Traveloka / Tiket.com

TODO (Nesya / Nurul):
  1. Implementasi method _scrape() di bawah
  2. Target site: Traveloka (utama), Tiket.com (fallback)
  3. Gunakan self._make_driver() untuk membuat Selenium WebDriver
  4. Gunakan self._city_to_code(city, "flight") untuk dapat kode bandara
  5. Parse HTML → TransportSegment (lihat contoh di docstring _scrape)
  6. Test dengan: python scraper/plane_scraper.py

Referensi URL Traveloka:
  https://www.traveloka.com/en-id/flight/search?
    originAirport=CGK&destinationAirport=SUB
    &departureDate=2026-05-10&numberOfPassenger=1
"""

import re
import time
from datetime import datetime
from typing import Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper


class PlaneScraper(BaseScraper):
    """Mengambil data penerbangan dari Traveloka."""

    MODE = "flight"

    TRAVELOKA_URL = (
        "https://www.traveloka.com/en-id/flight/search?"
        "originAirport={origin}&destinationAirport={dest}"
        "&departureDate={date}&numberOfPassenger={pax}"
    )

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> list[TransportSegment]:
        """
        Scrape data penerbangan dari Traveloka.

        TODO (Nesya / Nurul): Implementasi ini.

        Panduan langkah-langkah:
          1. Buka URL Traveloka dengan Selenium
          2. Tunggu elemen hasil pencarian muncul (gunakan WebDriverWait)
          3. Loop semua card penerbangan yang tampil
          4. Extract: maskapai, jam berangkat, jam tiba, harga, kelas
          5. Konversi ke TransportSegment dan tambahkan ke list

        Contoh hasil yang diharapkan:
            return [
                TransportSegment(
                    id               = "SEG-PLANE-001",
                    mode             = "flight",
                    provider         = "Garuda Indonesia",
                    provider_code    = "GA",
                    origin           = origin,
                    destination      = destination,
                    departure_time   = datetime(2026, 5, 10, 8, 0),
                    arrival_time     = datetime(2026, 5, 10, 9, 15),
                    duration_minutes = 75,
                    price            = 850000,
                    seat_class       = "Economy",
                    available_seats  = 12,
                    rating           = 4.5,
                ),
                # ... tambah lebih banyak ...
            ]
        """
        # ── PLACEHOLDER — hapus raise ini saat mulai implementasi ─────────────
        raise NotImplementedError(
            "PlaneScraper._scrape() belum diimplementasi.\n"
            "Lihat docstring di atas untuk panduan implementasi."
        )

        # ── Template awal yang bisa dipakai ──────────────────────────────────
        # origin_code = self._city_to_code(origin, "flight")
        # dest_code   = self._city_to_code(destination, "flight")
        # url = self.TRAVELOKA_URL.format(
        #     origin=origin_code, dest=dest_code,
        #     date=date_str, pax=passengers
        # )
        #
        # driver = self._make_driver()
        # try:
        #     driver.get(url)
        #     time.sleep(5)  # tunggu JS render
        #     # TODO: parse elemen di sini
        #     segments = []
        #     return segments
        # finally:
        #     driver.quit()


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = PlaneScraper(headless=True)
    results = scraper.get_segments("Jakarta", "Surabaya", "2026-05-10", passengers=1)
    print(f"Hasil: {len(results)} penerbangan ditemukan")
    for r in results:
        print(f"  {r}")
