"""
scraper/plane_scraper.py — ANTARA Project
==========================================
Scraper tiket pesawat dari tiket.com menggunakan Playwright (async).

Pola persis sama dengan TrainScraper:
  - _scrape()       → sinkron wrapper via asyncio.run()
  - _scrape_async() → inti scraping Playwright
  - _parse_card()   → ekstrak satu card → dict mentah
  - _to_segment()   → dict → TransportSegment

Kota → Kode IATA (CITY-code tiket.com pakai akhiran 'C'):
  Jakarta   → JKTC   Surabaya  → SUBC   Bali/Denpasar → DPSC
  Yogyakarta→ YOGC   Semarang  → SRGC   Bandung        → BDOC
  Makassar  → UPGC   Malang    → MLGC   Medan          → KNOC
"""

import asyncio
import re
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper


# ── Mapping kota → kode CITY tiket.com ───────────────────────────────────────
CITY_CODES = {
    "Jakarta":    "JKTC",
    "Surabaya":   "SUBC",
    "Bali":       "DPSC",
    "Denpasar":   "DPSC",
    "Yogyakarta": "YOGC",
    "Semarang":   "SRGC",
    "Bandung":    "BDOC",
    "Makassar":   "UPGC",
    "Malang":     "MLGC",
    "Medan":      "KNOC",
    "Manado":     "MDCC",
    "Balikpapan": "BPNC",
    "Lombok":     "LOPC",
    "Solo":       "SOCC",
    "Palembang":  "PLMC",
}

# ── Daftar maskapai untuk parsing ─────────────────────────────────────────────
MASKAPAI_LIST = [
    "Garuda Indonesia",
    "Lion Air",
    "Citilink",
    "Batik Air Indonesia",
    "Batik Air",
    "AirAsia Indonesia",
    "AirAsia",
    "Sriwijaya Air",
    "Wings Air",
    "Super Air Jet",
    "TransNusa",
    "NAM Air",
    "Pelita Air",
]

# Kode IATA bandara valid (untuk ekstrak dari teks card)
VALID_IATA = {
    "CGK", "HLP", "DPS", "SUB", "UPG", "MDC", "BPN",
    "LOP", "SOC", "SRG", "YOG", "JOG", "BDO", "PLM",
    "PKU", "KUL", "SIN", "MLG", "KNO", "BTH",
}

# Noise keywords yang ada di card bukan penerbangan (header, banner, footer)
NOISE_KEYWORDS = [
    "Filter", "Urutkan", "Maskapai", "Waktu Penerbangan",
    "Login untuk", "Daftar", "Pusat Bantuan",
    "WhatsApp", "cs@tiket", "2011-2026",
    "Penerbangan Populer",
]


class PlaneScraper(BaseScraper):
    """Mengambil data penerbangan dari tiket.com menggunakan Playwright."""

    MODE = "flight"

    TIKET_URL = (
        "https://www.tiket.com/id-id/flights/search"
        "?d={origin}&a={dest}"
        "&date={date}"
        "&adult={pax}&child=0&infant=0"
        "&class=economy"
        "&dType=CITY&aType=CITY"
        "&dLabel={origin}&aLabel={dest}"
        "&type=depart"
    )

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> List[TransportSegment]:
        """Sinkron wrapper — dipanggil oleh BaseScraper.get_segments()."""
        return asyncio.run(
            self._scrape_async(origin, destination, date_str, passengers)
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  ASYNC CORE
    # ─────────────────────────────────────────────────────────────────────────

    async def _scrape_async(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> List[TransportSegment]:
        from playwright.async_api import async_playwright

        origin_code = CITY_CODES.get(origin, origin[:3].upper() + "C")
        dest_code   = CITY_CODES.get(destination, destination[:3].upper() + "C")

        url = self.TIKET_URL.format(
            origin=origin_code,
            dest=dest_code,
            date=date_str,
            pax=passengers,
        )

        self.logger.info(f"[PlaneScraper] URL: {url}")
        segments: List[TransportSegment] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
                locale="id-ID",
                timezone_id="Asia/Jakarta",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")
                await self._human_behavior(page)

                self.logger.info("[PlaneScraper] Menunggu card penerbangan...")
                result_found = await self._wait_for_results(page)

                if not result_found:
                    self.logger.info("[PlaneScraper] Tidak ada penerbangan ditemukan.")
                    return segments

                # Scroll agar semua card lazy-load termuat
                await self._gentle_scroll(page, rounds=8)
                await asyncio.sleep(random.uniform(2.0, 3.0))

                # Ambil semua card menggunakan class yang sudah diverifikasi dari DOM
                cards = await page.locator(
                    "[class*='FlightCard_card'], [class*='FlightSectionRenderer_flight_item']"
                ).all()

                # Fallback jika class berubah
                if not cards:
                    self.logger.warning("[PlaneScraper] Class selector kosong, pakai fallback...")
                    cards = await page.locator(
                        "div:has-text('IDR'):has-text('Langsung'), "
                        "div:has-text('IDR'):has-text('transit')"
                    ).all()

                self.logger.info(f"[PlaneScraper] Raw cards: {len(cards)}")

                raw_items = []
                for i, card in enumerate(cards):
                    try:
                        item = await self._parse_card_async(card)
                        if item:
                            raw_items.append(item)
                    except Exception as e:
                        self.logger.warning(f"[PlaneScraper] Card {i+1} skip: {e}")
                        continue

                # Deduplikasi
                seen = set()
                for item in raw_items:
                    key = (
                        item["maskapai"],
                        item["jam_berangkat"],
                        item["jam_tiba"],
                        item["durasi_menit"],
                        item["harga_raw"],
                    )
                    if item["harga_raw"] <= 0:
                        continue
                    if key not in seen:
                        seen.add(key)
                        seg = self._to_segment(item, origin, destination, date_str)
                        if seg:
                            segments.append(seg)

                self.logger.info(f"[PlaneScraper] {len(segments)} penerbangan unik ditemukan.")

            except Exception as e:
                self.logger.error(f"[PlaneScraper] Scraping gagal: {e}")
                try:
                    await page.screenshot(path="plane_scraper_error.png")
                    self.logger.info("[PlaneScraper] Screenshot → plane_scraper_error.png")
                except Exception:
                    pass

            finally:
                await browser.close()

        return segments

    # ─────────────────────────────────────────────────────────────────────────
    #  WAIT FOR RESULTS
    # ─────────────────────────────────────────────────────────────────────────

    async def _wait_for_results(self, page) -> bool:
        """Tunggu hingga card penerbangan muncul di DOM."""
        try:
            await page.wait_for_selector(
                "[class*='FlightCard_card'], [class*='FlightSectionRenderer_flight_item']",
                timeout=45000,
            )
            self.logger.info("[PlaneScraper] FlightCard terdeteksi.")
            return True
        except Exception:
            self.logger.warning("[PlaneScraper] Class selector timeout, coba fallback text=IDR...")

        try:
            await page.wait_for_selector("text=IDR", timeout=20000)
            self.logger.info("[PlaneScraper] Text 'IDR' ditemukan.")
            return True
        except Exception:
            self.logger.warning("[PlaneScraper] Fallback juga timeout.")

        # Cek apakah ada pesan tidak ada hasil
        body = await page.inner_text("body")
        if any(kw in body for kw in ["Tidak ada penerbangan", "No flights", "tidak ditemukan"]):
            return False

        # Kasih waktu extra, mungkin lambat
        self.logger.warning("[PlaneScraper] Lanjut scrape dengan fallback keras...")
        await asyncio.sleep(5)
        return True

    # ─────────────────────────────────────────────────────────────────────────
    #  SCROLL
    # ─────────────────────────────────────────────────────────────────────────

    async def _gentle_scroll(self, page, rounds: int = 8):
        """Scroll bertahap untuk trigger lazy-load."""
        self.logger.info("[PlaneScraper] Scrolling untuk memuat semua card...")
        for i in range(rounds):
            await page.mouse.wheel(0, random.randint(400, 700))
            await asyncio.sleep(random.uniform(0.8, 1.4))
            # Klik "Tampilkan lebih" jika ada
            btn = page.locator(
                "button:has-text('Tampilkan lebih'), button:has-text('Lihat lebih')"
            )
            if await btn.count() > 0:
                self.logger.info(f"[PlaneScraper] Klik 'Tampilkan lebih' (round {i+1})")
                await btn.first.click()
                await asyncio.sleep(random.uniform(2.0, 3.0))

    # ─────────────────────────────────────────────────────────────────────────
    #  PARSE CARD
    # ─────────────────────────────────────────────────────────────────────────

    async def _parse_card_async(self, card) -> Optional[dict]:
        """Ekstrak data dari satu card elemen Playwright."""
        try:
            teks = await card.inner_text()
        except Exception:
            return None

        return self._parse_card(teks)

    def _parse_card(self, teks: str) -> Optional[dict]:
        """Parse teks card → dict mentah. Dipanggil juga dari test."""

        # Buang card yang bukan data penerbangan
        if any(n.lower() in teks.lower() for n in NOISE_KEYWORDS):
            return None

        # Wajib ada IDR dan minimal satu jam
        times = re.findall(r'\b\d{2}:\d{2}\b', teks)
        if not times or "IDR" not in teks:
            return None

        # ── Maskapai ──────────────────────────────────────────────────────────
        maskapai = "Unknown"
        for mk in MASKAPAI_LIST:
            if mk.lower() in teks.lower():
                maskapai = mk
                break

        # Fallback: maskapai gabungan (e.g. "Batik Air + Lion Air")
        if maskapai == "Unknown":
            gabungan = re.search(
                r'([A-Za-z\s]+(?:Air|Jet|Nusa|Link)[A-Za-z\s]*'
                r'(?:\+[A-Za-z\s]+(?:Air|Jet|Nusa|Link)[A-Za-z\s]*)?)',
                teks,
            )
            if gabungan:
                maskapai = gabungan.group(1).strip()

        # ── Jam berangkat & tiba ──────────────────────────────────────────────
        jam_berangkat = times[0] if len(times) > 0 else ""
        jam_tiba      = times[1] if len(times) > 1 else ""

        # ── Kode bandara ──────────────────────────────────────────────────────
        iata_found = [c for c in re.findall(r'\b([A-Z]{3})\b', teks) if c in VALID_IATA]
        bandara_dari = iata_found[0] if len(iata_found) > 0 else ""
        bandara_ke   = iata_found[1] if len(iata_found) > 1 else ""

        # ── Durasi → menit ────────────────────────────────────────────────────
        durasi_str  = ""
        durasi_menit = 0
        dm = re.search(r'(\d+)j(?:\s*(\d+)m)?', teks)
        if dm:
            jam  = int(dm.group(1))
            mnt  = int(dm.group(2)) if dm.group(2) else 0
            durasi_menit = jam * 60 + mnt
            durasi_str   = f"{jam}j {mnt}m" if mnt else f"{jam}j"

        # ── Transit ───────────────────────────────────────────────────────────
        if re.search(r'langsung', teks, re.IGNORECASE):
            transit = "Langsung"
        else:
            tm = re.search(r'(\d+)\s*transit', teks, re.IGNORECASE)
            transit = f"{tm.group(1)} Transit" if tm else ""

        # ── Harga terkecil (after cashback) ──────────────────────────────────
        idr_matches = re.findall(r'IDR\s?[\d.,]+', teks)
        def to_int(s):
            return int(re.sub(r'[^\d]', '', s))
        harga_raw = 0
        if idr_matches:
            harga_raw = min(to_int(m) for m in idr_matches)

        # ── Bagasi ────────────────────────────────────────────────────────────
        bagasi_m = re.search(r'(\d+\s*[kK][gG])', teks)
        bagasi   = bagasi_m.group(1) if bagasi_m else ""

        return {
            "maskapai":      maskapai,
            "jam_berangkat": jam_berangkat,
            "jam_tiba":      jam_tiba,
            "bandara_dari":  bandara_dari,
            "bandara_ke":    bandara_ke,
            "durasi_str":    durasi_str,
            "durasi_menit":  durasi_menit,
            "transit":       transit,
            "bagasi":        bagasi,
            "harga_raw":     harga_raw,
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  KONVERSI KE TransportSegment
    # ─────────────────────────────────────────────────────────────────────────

    def _to_segment(
        self,
        item: dict,
        origin: str,
        destination: str,
        date_str: str,
    ) -> Optional[TransportSegment]:
        try:
            departure_time = self._parse_time(date_str, item["jam_berangkat"])

            # Jika ada durasi dari teks, hitung arr_time dari dep_time + durasi
            # (lebih akurat, menangani penerbangan lewat tengah malam)
            if item.get("durasi_menit", 0) > 0:
                arrival_time     = departure_time + timedelta(minutes=item["durasi_menit"])
                duration_minutes = item["durasi_menit"]
            else:
                arrival_time = self._parse_time(date_str, item["jam_tiba"])
                if arrival_time < departure_time:
                    arrival_time += timedelta(days=1)
                duration_minutes = int(
                    (arrival_time - departure_time).total_seconds() / 60
                )

            return TransportSegment(
                id               = f"SEG-PLANE-{uuid.uuid4().hex[:8].upper()}",
                mode             = "flight",
                provider         = item["maskapai"],
                provider_code    = self._maskapai_code(item["maskapai"]),
                origin           = origin,
                destination      = destination,
                departure_time   = departure_time,
                arrival_time     = arrival_time,
                duration_minutes = duration_minutes,
                price            = float(item["harga_raw"]),
                seat_class       = "Economy",
                available_seats  = None,
                rating           = None,
            )
        except Exception as e:
            self.logger.warning(f"[PlaneScraper] Gagal konversi ke segment: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_time(date_str: str, time_str: str) -> datetime:
        """'2026-05-08' + '07:30' → datetime(2026, 5, 8, 7, 30)"""
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    @staticmethod
    def _maskapai_code(maskapai: str) -> Optional[str]:
        """Kode IATA maskapai dari nama."""
        kode_map = {
            "Garuda Indonesia":    "GA",
            "Lion Air":            "JT",
            "Citilink":            "QG",
            "Batik Air Indonesia": "ID",
            "Batik Air":           "ID",
            "AirAsia Indonesia":   "QZ",
            "AirAsia":             "AK",
            "Sriwijaya Air":       "SJ",
            "Wings Air":           "IW",
            "Super Air Jet":       "IU",
            "TransNusa":           "8B",
            "NAM Air":             "IN",
            "Pelita Air":          "IP",
        }
        return kode_map.get(maskapai)

    @staticmethod
    async def _human_behavior(page) -> None:
        """Simulasi perilaku manusia agar tidak terdeteksi bot."""
        await page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 500),
            steps=10,
        )
        await asyncio.sleep(random.uniform(1.0, 2.5))
        for _ in range(random.randint(2, 3)):
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.8, 1.8))
        await asyncio.sleep(random.uniform(1.5, 3.0))


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s — %(message)s")

    scraper = PlaneScraper(headless=False, timeout=90)
    results = scraper.get_segments("Jakarta", "Bali", "2026-05-15", passengers=1)
    print(f"\nHasil: {len(results)} penerbangan ditemukan")
    for r in results:
        print(f"  {r}")