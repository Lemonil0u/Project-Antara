"""
engine/local_data.py — ANTARA Project
=====================================
Generator first-mile / last-mile (STUB).

Konteks:
  Untuk menghasilkan rute "door-to-door" yang benar-benar lengkap, kita perlu
  segmen lokal: rumah → stasiun keberangkatan, dan stasiun tujuan → hotel.

  Saat ini scraping rute lokal nyata (Gojek/Grab/TransJakarta) BELUM
  diimplementasi — modul ini menghasilkan estimasi placeholder agar arsitektur
  sudah tertanam dan tinggal diisi data nyata nanti.

Cara pakai:
    from engine.local_data import LocalSegmentGenerator
    gen = LocalSegmentGenerator(seed=42)
    first = gen.generate_first_mile("Jakarta")
    last  = gen.generate_last_mile("Surabaya")
"""

import random
from typing import Optional

from models import LocalSegment


class LocalSegmentGenerator:
    """
    Placeholder generator untuk first-mile dan last-mile.

    Menghasilkan estimasi sederhana berbasis kota. Bukan data nyata —
    ganti dengan scraper Gojek/Grab nanti.
    """

    # Estimasi harga & durasi rata-rata transport lokal per kota besar (IDR, menit)
    # Format: kota → (harga_min, harga_max, durasi_min, durasi_max)
    LOCAL_ESTIMATES = {
        "Jakarta":    (25_000, 80_000, 20, 60),
        "Bandung":    (15_000, 50_000, 15, 40),
        "Surabaya":   (20_000, 60_000, 15, 45),
        "Yogyakarta": (15_000, 45_000, 10, 35),
        "Semarang":   (15_000, 40_000, 15, 35),
        "Solo":       (12_000, 35_000, 10, 30),
        "Malang":     (12_000, 35_000, 10, 30),
        "Bali":       (30_000, 90_000, 25, 60),
        "Medan":      (20_000, 55_000, 20, 50),
        "Makassar":   (18_000, 50_000, 20, 45),
    }

    DEFAULT_ESTIMATE = (15_000, 50_000, 15, 40)

    PROVIDERS = ["Gojek", "Grab", "Maxim", "TransJakarta", "Damri Bandara"]

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"LOCAL-{self._counter:04d}"

    def _generate(self, city: str, is_last_mile: bool = False) -> LocalSegment:
        """Hasilkan satu LocalSegment placeholder untuk kota tertentu."""
        price_min, price_max, dur_min, dur_max = self.LOCAL_ESTIMATES.get(
            city, self.DEFAULT_ESTIMATE,
        )
        provider = self._rng.choice(self.PROVIDERS)
        price    = self._rng.randint(price_min, price_max)
        duration = self._rng.randint(dur_min, dur_max)
        # Bulatkan harga ke ribuan terdekat
        price = round(price / 1000) * 1000

        # Walk untuk Damri/TransJakarta cenderung lebih murah & lebih lama
        if provider in ("TransJakarta", "Damri Bandara"):
            mode = "transit"
        elif provider == "Maxim":
            mode = "ride_hail"
        else:
            mode = "ride_hail"

        if is_last_mile:
            origin_label, dest_label = f"Stasiun/Bandara {city}", f"Tujuan akhir di {city}"
        else:
            origin_label, dest_label = f"Titik jemput di {city}", f"Stasiun/Bandara {city}"

        return LocalSegment(
            id=self._next_id(),
            mode=mode,
            provider=provider,
            origin=origin_label,
            destination=dest_label,
            duration_minutes=duration,
            price=float(price),
        )

    def generate_first_mile(self, origin_city: str) -> LocalSegment:
        """Estimasi rumah → stasiun/bandara di origin_city."""
        return self._generate(origin_city, is_last_mile=False)

    def generate_last_mile(self, destination_city: str) -> LocalSegment:
        """Estimasi stasiun/bandara → hotel di destination_city."""
        return self._generate(destination_city, is_last_mile=True)


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gen = LocalSegmentGenerator(seed=42)
    print("First-mile Jakarta:", gen.generate_first_mile("Jakarta"))
    print("Last-mile Surabaya:", gen.generate_last_mile("Surabaya"))
