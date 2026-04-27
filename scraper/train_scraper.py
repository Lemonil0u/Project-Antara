"""
scraper/train_scraper.py — ANTARA Project
===========================================
Scraper untuk data kereta api dari KAI Access / Tiket.com

TODO (Nesya / Nurul):
  1. Implementasi method _scrape() di bawah
  2. Target site: KAI Access (utama), Tiket.com (fallback)
  3. Gunakan self._make_driver() untuk Selenium
  4. Gunakan self._city_to_code(city, "train") untuk kode stasiun
  5. Test dengan: python scraper/train_scraper.py

Referensi URL KAI:
  https://booking.kai.id/
  Perlu interaksi form: pilih origin, destination, tanggal, lalu submit.
"""

import time
from datetime import datetime
from typing import Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper


class TrainScraper(BaseScraper):
    """Mengambil data kereta api dari KAI Access."""

    MODE = "train"

    KAI_URL = "https://booking.kai.id/"

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> list[TransportSegment]:
        """
        Scrape data kereta api dari KAI.

        TODO (Nesya / Nurul): Implementasi ini.

        Panduan langkah-langkah:
          1. Buka halaman KAI dengan Selenium
          2. Isi form: stasiun asal, stasiun tujuan, tanggal, jumlah penumpang
          3. Klik tombol "Cari"
          4. Tunggu hasil muncul
          5. Loop card kereta yang tampil
          6. Extract: nama kereta, kelas, jam berangkat, jam tiba, harga
          7. Konversi ke TransportSegment

        Note:
          - KAI pakai kode stasiun (GMR, SBI, YK, dll.)
          - Gunakan self._city_to_code(city, "train")
          - Hati-hati dengan CAPTCHA — mungkin perlu delay random

        Contoh hasil:
            return [
                TransportSegment(
                    id               = "SEG-TRAIN-001",
                    mode             = "train",
                    provider         = "KAI Argo Bromo Anggrek",
                    provider_code    = "KA",
                    origin           = origin,
                    destination      = destination,
                    departure_time   = datetime(2026, 5, 10, 9, 0),
                    arrival_time     = datetime(2026, 5, 10, 17, 0),
                    duration_minutes = 480,
                    price            = 350000,
                    seat_class       = "Executive",
                    available_seats  = 4,
                    rating           = 4.6,
                ),
            ]
        """
        raise NotImplementedError(
            "TrainScraper._scrape() belum diimplementasi.\n"
            "Lihat docstring di atas untuk panduan implementasi."
        )

        # ── Template ──────────────────────────────────────────────────────────
        # origin_code = self._city_to_code(origin, "train")
        # dest_code   = self._city_to_code(destination, "train")
        #
        # driver = self._make_driver()
        # try:
        #     driver.get(self.KAI_URL)
        #     time.sleep(3)
        #     # TODO: isi form, klik submit, parse hasil
        #     segments = []
        #     return segments
        # finally:
        #     driver.quit()


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = TrainScraper(headless=True)
    results = scraper.get_segments("Jakarta", "Surabaya", "2026-05-10", passengers=1)
    print(f"Hasil: {len(results)} kereta ditemukan")
    for r in results:
        print(f"  {r}")
