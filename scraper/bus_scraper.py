"""
scraper/bus_scraper.py — ANTARA Project
=========================================
Scraper untuk data bus dari RedBus / Traveloka (Bus section)

TODO (Nesya / Nurul):
  1. Implementasi method _scrape() di bawah
  2. Target site: RedBus Indonesia (utama), Traveloka Bus (fallback)
  3. Gunakan self._make_driver() untuk Selenium
  4. Test dengan: python scraper/bus_scraper.py

Referensi URL RedBus:
  https://www.redbus.id/bus-tickets/{origin-slug}-to-{destination-slug}
  Contoh: https://www.redbus.id/bus-tickets/jakarta-to-surabaya
"""

import time
from datetime import datetime

from models import TransportSegment
from scraper.base_scraper import BaseScraper

# Mapping nama kota → slug URL RedBus
REDBUS_SLUGS = {
    "Jakarta":    "jakarta",
    "Surabaya":   "surabaya",
    "Yogyakarta": "yogyakarta",
    "Semarang":   "semarang",
    "Bandung":    "bandung",
    "Solo":       "solo",
    "Malang":     "malang",
    "Bali":       "bali",
}


class BusScraper(BaseScraper):
    """Mengambil data bus dari RedBus Indonesia."""

    MODE = "bus"

    REDBUS_URL = "https://www.redbus.id/bus-tickets/{origin}-to-{dest}"

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> list[TransportSegment]:
        """
        Scrape data bus dari RedBus.

        TODO (Nesya / Nurul): Implementasi ini.

        Panduan langkah-langkah:
          1. Konversi nama kota ke slug RedBus (pakai REDBUS_SLUGS)
          2. Buka URL RedBus
          3. Set filter tanggal
          4. Tunggu daftar bus muncul
          5. Loop setiap card bus
          6. Extract: operator, jam berangkat, jam tiba, harga, rating, tipe bus
          7. Konversi ke TransportSegment

        Contoh hasil:
            return [
                TransportSegment(
                    id               = "SEG-BUS-001",
                    mode             = "bus",
                    provider         = "PO Rosalia Indah",
                    provider_code    = "RI",
                    origin           = origin,
                    destination      = destination,
                    departure_time   = datetime(2026, 5, 10, 19, 0),
                    arrival_time     = datetime(2026, 5, 11, 9, 0),
                    duration_minutes = 840,
                    price            = 180000,
                    seat_class       = "Executive",
                    available_seats  = 8,
                    rating           = 4.2,
                ),
            ]
        """
        raise NotImplementedError(
            "BusScraper._scrape() belum diimplementasi.\n"
            "Lihat docstring di atas untuk panduan implementasi."
        )

        # ── Template ──────────────────────────────────────────────────────────
        # origin_slug = REDBUS_SLUGS.get(origin, origin.lower())
        # dest_slug   = REDBUS_SLUGS.get(destination, destination.lower())
        # url = self.REDBUS_URL.format(origin=origin_slug, dest=dest_slug)
        #
        # driver = self._make_driver()
        # try:
        #     driver.get(url)
        #     time.sleep(4)
        #     # TODO: set tanggal dan parse hasil
        #     segments = []
        #     return segments
        # finally:
        #     driver.quit()


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = BusScraper(headless=True)
    results = scraper.get_segments("Jakarta", "Surabaya", "2026-05-10", passengers=1)
    print(f"Hasil: {len(results)} bus ditemukan")
    for r in results:
        print(f"  {r}")
