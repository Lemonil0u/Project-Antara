"""
scraper/bus_scraper.py — ANTARA Project
=======================================
Scraper untuk data bus dari RedBus / Traveloka Bus.

STATUS: STUB. Belum diimplementasi. Data source akan otomatis skip scraper
ini dan tidak crash.

TODO (Nesya / Nurul):
  1. Implementasi _scrape() / _scrape_async() mengikuti pola TrainScraper.
  2. Target site: RedBus Indonesia (utama), Traveloka Bus (fallback).
  3. Pakai Playwright async (BUKAN Selenium).
  4. Test: python scraper/bus_scraper.py

Referensi URL RedBus:
  https://www.redbus.id/bus-tickets/{origin-slug}-to-{destination-slug}
  Contoh: https://www.redbus.id/bus-tickets/jakarta-to-surabaya
"""

from typing import List

from models import TransportSegment
from scraper.base_scraper import BaseScraper


# Mapping nama kota → slug URL RedBus (extend sesuai kebutuhan)
REDBUS_SLUGS = {
    "Jakarta": "jakarta",
    "Surabaya": "surabaya",
    "Yogyakarta": "yogyakarta",
    "Semarang": "semarang",
    "Bandung": "bandung",
    "Solo": "solo",
    "Malang": "malang",
    "Bali": "bali",
}


class BusScraper(BaseScraper):
    """Mengambil data bus. STUB — belum diimplementasi."""

    MODE = "bus"

    REDBUS_URL = "https://www.redbus.id/bus-tickets/{origin}-to-{dest}"

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> List[TransportSegment]:
        """
        TODO: implementasi scraping bus.

        Pola implementasi (lihat TrainScraper):
          1. Konversi nama kota ke slug RedBus pakai REDBUS_SLUGS.
          2. Bangun URL.
          3. async with async_playwright() ...
          4. Set filter tanggal (kemungkinan via input/datepicker).
          5. Tunggu daftar bus muncul.
          6. Parse: operator, jam berangkat/tiba, harga, rating, tipe bus.
          7. Return List[TransportSegment].

        Contoh hasil:
            [TransportSegment(
                id="SEG-BUS-XYZ",
                mode="bus",
                provider="PO Rosalia Indah",
                provider_code="RI",
                origin="Jakarta", destination="Surabaya",
                departure_time=datetime(2026,5,15,19,0),
                arrival_time=datetime(2026,5,16,9,0),
                duration_minutes=840,
                price=180000, seat_class="Executive",
                available_seats=8, rating=4.2,
            ), ...]
        """
        raise NotImplementedError(
            "BusScraper._scrape() belum diimplementasi. "
            "Lihat docstring untuk panduan implementasi Playwright."
        )


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = BusScraper(headless=True)
    results = scraper.get_segments("Jakarta", "Surabaya", "2026-05-15", passengers=1)
    print(f"Hasil: {len(results)} bus ditemukan")
