"""
scraper/bus_scraper.py — ANTARA Project
Scraper untuk data bus dari Tiket.com menggunakan Playwright async.
Pola persis sama dengan TrainScraper & PlaneScraper:
_scrape()       → sinkron wrapper via asyncio.run()
_scrape_async() → inti scraping Playwright
_parse_card()   → ekstrak satu card → dict mentah
_to_segment()   → dict → TransportSegment

Kota → ID Tiket.com (diambil dari URL search tiket.com):
Jakarta   → 63d0b5bd2cbd5656536ba09f
Bandung   → 63d0b5be2cbd5656536ba167
Surabaya  → 63d0b5bb2cbd5656536b9f28
Denpasar  → 63d0b5be2cbd5656536ba1ac
Yogyakarta→ 63d0b5bb2cbd5656536b9ec4
Semarang  → 63d0b5bb2cbd5656536b9ecd
Solo      → 63d0b5bb2cbd5656536b9ecd (Shared ID with Semarang in some contexts, verify if needed)
Malang    → 63d0b5bb2cbd5656536b9ee2
Garut     → 63d0b5b02cbd5656536b957c
Bogor     → 63d0b5c32cbd5656536ba585
"""
import asyncio
import re
import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper

# ─── Mapping Kota → ID Tiket.com ───────────────────────────────────────────────
# Sumber: Parameter 'origin' dan 'destination' pada URL search tiket.com
CITY_IDS = {
    "JAKARTA": "63d0b5bd2cbd5656536ba09f",
    "BANDUNG": "63d0b5be2cbd5656536ba167",
    "SURABAYA": "63d0b5bb2cbd5656536b9f28",
    "DENPASAR": "63d0b5be2cbd5656536ba1ac",
    "BALI": "63d0b5be2cbd5656536ba1ac",  # Alias Denpasar
    "YOGYAKARTA": "63d0b5bb2cbd5656536b9ec4",
    "JOGJA": "63d0b5bb2cbd5656536b9ec4",
    "SEMARANG": "63d0b5bb2cbd5656536b9ecd",
    "SOLO": "63d0b5bb2cbd5656536b9ecd",
    "MALANG": "63d0b5bb2cbd5656536b9ee2",
    "GARUT": "63d0b5b02cbd5656536b957c",
    "BOGOR": "63d0b5c32cbd5656536ba585",
    "BEKASI": "63d0b5ad2cbd5656536b928d",
    "DEPOK": "63d0b5ad2cbd5656536b928d",
    "CIREBON": "63d0b5bd2cbd5656536ba0a5",
    "TEGAL": "63d0b5c22cbd5656536ba4f3",
    "PEKALONGAN": "63d0b5c02cbd5656536ba3a1",
    "PURWOKERTO": "63d0b5c12cbd5656536ba44a",
    "CILACAP": "63d0b5b22cbd5656536b972e",
    "KEDIRI": "63d0b5b92cbd5656536b9d8c",
    "BLITAR": "63d0b5b12cbd5656536b965a",
    "PROBOLINGGO": "63d0b5c12cbd5656536ba463",
    "BANYUWANGI": "63d0b5b02cbd5656536b95c3",
    "JEMBER": "63d0b5b92cbd5656536b9d9e",
}

# Noise keywords untuk filter card yang bukan data (banner, filter UI, popup text)
BUS_NOISE_KEYWORDS = [
    "Filter & Urutkan", "Agen Populer", "Titik Naik", "sesuai keinginanmu",
    "Klaim refund", "0% Refund", "Diskon hingga", "Terlaris", "buruan pesan",
    "Pilih mau naik dan turun di mana", "Cari Titik Naik", "Cari Titik Turun"
]

class BusScraper(BaseScraper):
    """Mengambil data bus dari Tiket.com via Playwright async."""
    MODE = "bus"

    # Template URL Tiket.com Bus
    TIKET_URL = (
        "https://www.tiket.com/id-id/bus-travel/search?"
        "origin={origin}&destination={dest}&"
        "tripType=oneway&journeyType=depart&"
        "departureDate={date}&returnDate={date}&adult={pax}"
    )

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
        max_results: Optional[int] = None,
    ) -> List[TransportSegment]:
        """Wrapper sinkron — dipanggil oleh BaseScraper.get_segments()."""
        return asyncio.run(
            self._scrape_async(origin, destination, date_str, passengers,
                               max_results=max_results)
        )

    # ─────────────────────────────────────────────────────────────────────────
    #   ASYNC CORE
    # ─────────────────────────────────────────────────────────────────────────

    async def _scrape_async(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
        max_results: Optional[int] = None,
    ) -> List[TransportSegment]:
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

        # Konversi nama kota ke ID (case-insensitive)
        origin_id = CITY_IDS.get(origin.upper())
        dest_id   = CITY_IDS.get(destination.upper())

        if not origin_id or not dest_id:
            self.logger.warning(f"[BusScraper] ID tidak ditemukan untuk {origin} ({origin.upper()}) atau {destination} ({destination.upper()}).")
            self.logger.info(f"[BusScraper] Kota tersedia: {list(CITY_IDS.keys())}")
            return []

        url = self.TIKET_URL.format(
            origin=origin_id,
            dest=dest_id,
            date=date_str,
            pax=passengers,
        )

        self.logger.info(f"[BusScraper] URL: {url}")
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
                self.logger.info("[BusScraper] Navigasi ke halaman search...")
                await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

                # Delay awal untuk rendering JS & stabilisasi
                await asyncio.sleep(random.uniform(1.0, 2.0))

                # 🎯 STEP 1: Handle Popup Tutorial (Fitur Spesifik Tiket.com)
                await self._close_tutorial_popup(page)

                # 🎯 STEP 2: Scroll untuk trigger lazy-load hasil bus
                self.logger.info("[BusScraper] Scrolling untuk memuat daftar bus...")
                await self._gentle_scroll(page, rounds=3)
                await asyncio.sleep(random.uniform(1.5, 2.5))

                # 🎯 STEP 3: Tunggu hasil muncul
                result_found = await self._wait_for_results(page)
                if not result_found:
                    self.logger.info("[BusScraper] Tidak ada hasil bus ditemukan.")
                    return []

                # 🎯 STEP 4: Ambil Cards
                # Selector berdasarkan struktur PDF: ada 'IDR' DAN ('Shuttle' ATAU 'Eksekutif' ATAU 'Ekonomi')
                # Menggunakan locator chaining untuk presisi
                cards = await page.locator(
                    "div:has-text('IDR'):has-text('Shuttle'), "
                    "div:has-text('IDR'):has-text('Eksekutif'), "
                    "div:has-text('IDR'):has-text('Ekonomi'), "
                    "div:has-text('IDR'):has-text('VIP')"
                ).all()

                # Fallback jika selector spesifik kosong (mungkin kelas lain atau format beda)
                if not cards:
                    self.logger.warning("[BusScraper] Selector spesifik kosong, pakai fallback umum...")
                    cards = await page.locator("div:has-text('IDR')").all()

                self.logger.info(f"[BusScraper] Raw cards ditemukan: {len(cards)}")

                raw_items = []
                for i, card in enumerate(cards):
                    try:
                        text = await card.inner_text()
                        item = self._parse_card(text)
                        if item:
                            raw_items.append(item)
                    except Exception as e:
                        self.logger.debug(f"[BusScraper] Card {i+1} error: {e}")
                        continue

                # 🎯 STEP 5: Deduplikasi & Konversi ke Segment + early stop
                seen = set()
                for item in raw_items:
                    if max_results and len(segments) >= max_results:
                        self.logger.info(
                            f"[BusScraper] Quick-stop: {len(segments)} rute cukup."
                        )
                        break
                    # Key unik: Operator + Jam Berangkat + Harga
                    key = (
                        item["operator"],
                        item["jam_berangkat"],
                        item["harga_raw"]
                    )
                    if key not in seen and item["harga_raw"] > 0:
                        seen.add(key)
                        seg = self._to_segment(item, origin, destination, date_str)
                        if seg:
                            segments.append(seg)

                self.logger.info(f"[BusScraper] {len(segments)} bus unik diproses.")

            except Exception as e:
                self.logger.error(f"[BusScraper] Fatal error: {e}")
                try:
                    await page.screenshot(path="bus_scraper_error.png")
                    self.logger.info("[BusScraper] Screenshot → bus_scraper_error.png")
                except:
                    pass
            finally:
                await browser.close()

        return segments

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER: CLOSE TUTORIAL POPUP
    # ─────────────────────────────────────────────────────────────────────────

    async def _close_tutorial_popup(self, page, timeout=10000):
        """Menutup popup 'Filter & Urutkan' / 'Lewati' yang sering muncul."""
        try:
            self.logger.info("[BusScraper] Cek popup tutorial...")
            # Coba klik tombol "Lewati" jika ada
            skip_btn = page.locator("button:has-text('Lewati')").first
            if await skip_btn.count() > 0:
                await skip_btn.click()
                await asyncio.sleep(1.0)
                self.logger.info("[BusScraper] Popup ditutup via 'Lewati'.")
            
            # Fallback: klik overlay jika modal masih ada (kadang 'Lewati' tidak menutup sepenuhnya)
            overlay = page.locator(".modal-overlay, [class*='overlay'], div[class*='Modal']").first
            if await overlay.count() > 0:
                # Klik di tengah overlay (koordinat relatif)
                box = await overlay.bounding_box()
                if box:
                    await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    await asyncio.sleep(0.5)
                    self.logger.info("[BusScraper] Overlay diklik.")
                
        except Exception as e:
            self.logger.debug(f"[BusScraper] Tidak ada popup atau error handle popup: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER: WAIT FOR RESULTS
    # ─────────────────────────────────────────────────────────────────────────

    async def _wait_for_results(self, page) -> bool:
        """Tunggu indikator hasil bus muncul."""
        selectors = [
            "text=IDR",
            "text=Shuttle",
            "text=Eksekutif",
            "text=Pilih mau naik",  # Teks spesifik dari PDF
        ]
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=15000)
                self.logger.info(f"[BusScraper] Hasil terdeteksi via: {sel}")
                return True
            except:
                continue

        # Semua selektor timeout — cek secara eksplisit apakah halaman kosong/error
        try:
            body_text = await page.inner_text("body")
            body_lower = body_text.lower()

            # Indikator "tidak ada hasil" dari Tiket.com
            NO_RESULT_PHRASES = [
                "tidak ditemukan",
                "no results",
                "tidak tersedia",
                "maaf, tidak ada",
                "pencarian tidak menghasilkan",
                "coba ubah tanggal",
                "rute tidak ditemukan",
            ]
            if any(phrase in body_lower for phrase in NO_RESULT_PHRASES):
                self.logger.info("[BusScraper] Halaman menunjukkan tidak ada hasil bus.")
                return False

            # Indikator error / redirect (halaman bukan hasil pencarian)
            ERROR_PHRASES = [
                "404", "page not found", "halaman tidak ditemukan",
                "terjadi kesalahan", "something went wrong",
            ]
            if any(phrase in body_lower for phrase in ERROR_PHRASES):
                self.logger.warning("[BusScraper] Halaman error/404 terdeteksi, abort scraping.")
                return False

            # Cek minimal: apakah ada teks harga IDR sama sekali di body?
            # Jika tidak ada IDR sama sekali, kemungkinan besar halaman kosong
            if "idr" not in body_lower and "rp" not in body_lower:
                self.logger.info("[BusScraper] Tidak ada teks harga di halaman, kemungkinan tidak ada hasil.")
                return False

        except Exception as e:
            self.logger.debug(f"[BusScraper] Gagal baca body untuk cek hasil: {e}")

        self.logger.warning("[BusScraper] Timeout menunggu hasil, tapi ada konten di halaman — lanjut scrape...")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER: SCROLL
    # ─────────────────────────────────────────────────────────────────────────

    async def _gentle_scroll(self, page, rounds: int = 5):
        """Scroll perlahan untuk memuat lazy content."""
        for _ in range(rounds):
            await page.mouse.wheel(0, random.randint(300, 500))
            await asyncio.sleep(random.uniform(0.6, 1.2))

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER: PARSE CARD
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_card(self, text: str) -> Optional[dict]:
        """
        Parse teks card bus → dict.
        Contoh Teks (dari PDF):
        Daytrans
        4.5/5
        Shuttle 1+1
        02:00 • Pasteur 3j 05:00 • Grogol
        IDR108.160
        Diskon hingga 20%
        IDR 101.660
        Pilih mau naik dan turun di mana
        """
        # 1. Filter teks terlalu pendek (pasti bukan card hasil)
        if len(text.strip()) < 40:
            return None

        # 2. Harga (Wajib ada) — validasi struktural utama
        #    Harus ada harga IDR/Rp sebelum cek noise, karena badge promo
        #    bisa saja muncul bersama data valid di card yang sama.
        price_matches = re.findall(r'(?:IDR|Rp)\s?([\d.,]+)', text, re.IGNORECASE)
        if not price_matches:
            return None

        # 3. Waktu (Wajib ada) — minimal jam berangkat & tiba
        times = re.findall(r'\b(\d{2}:\d{2})\b', text)
        if len(times) < 2:
            return None

        # 4. Filter Noise — hanya skip jika teks TIDAK punya data valid sama sekali
        #    (harga & waktu sudah diverifikasi di atas, jadi kita hanya skip
        #     card yang SELURUH isinya adalah elemen UI, bukan card yang
        #     kebetulan mengandung kata promo)
        UI_ONLY_KEYWORDS = [
            "Filter & Urutkan", "Agen Populer", "Titik Naik",
            "Cari Titik Naik", "Cari Titik Turun",
            "sesuai keinginanmu", "Klaim refund",
        ]
        # Hitung berapa keyword UI yang muncul — jika mayoritas teks adalah UI, skip
        noise_count = sum(1 for kw in UI_ONLY_KEYWORDS if kw.lower() in text.lower())
        if noise_count >= 2:
            # Kemungkinan besar ini elemen filter/UI, bukan card bus
            return None

        # 5. Ekstrak data dari teks yang sudah tervalidasi
        price_str = price_matches[0]
        harga_raw = int(re.sub(r'[^\d]', '', price_str))

        # Ambil harga diskon jika ada (harga kedua lebih kecil dari pertama)
        if len(price_matches) >= 2:
            harga_diskon = int(re.sub(r'[^\d]', '', price_matches[1]))
            # Gunakan harga diskon jika lebih kecil (artinya ini harga setelah diskon)
            if 0 < harga_diskon < harga_raw:
                harga_raw = harga_diskon

        jam_berangkat = times[0]
        jam_tiba = times[1]

        # 6. Operator (Cari nama di awal teks sebelum kelas/harga)
        operator = "Unknown"
        # Pola: Huruf besar di awal baris, sebelum angka rating atau Shuttle/Eksekutif
        # Contoh: "Daytrans\n4.5/5\nShuttle"
        op_match = re.search(r'^([A-Z][a-zA-Z\s\.]{3,30}?)\s*(?:\n|$)', text, re.MULTILINE)
        if op_match:
            candidate = op_match.group(1).strip()
            # Validasi sederhana: jangan ambil kata kunci UI
            if not any(bad in candidate.lower() for bad in ["filter", "urut", "agen", "populer"]):
                operator = candidate

        # Fallback jika operator masih Unknown, cari pola lain
        if operator == "Unknown":
            # Cari nama sebelum kata 'Shuttle' atau 'Eksekutif'
            op_fallback = re.search(r'([A-Z][a-zA-Z\s]+?)\s+(?:Shuttle|Eksekutif|Ekonomi|VIP)', text)
            if op_fallback:
                candidate = op_fallback.group(1).strip()
                if not any(bad in candidate.lower() for bad in ["filter", "urut", "agen"]):
                    operator = candidate

        # 7. Kelas Bus
        kelas = "Reguler"
        if "Shuttle" in text:
            kelas = "Shuttle"
        elif "Eksekutif" in text:
            kelas = "Executive"
        elif "Ekonomi" in text:
            kelas = "Economy"
        elif "VIP" in text:
            kelas = "VIP"
        elif "Sleeper" in text:
            kelas = "Sleeper"

        # 8. Rating
        rating_match = re.search(r'(\d\.\d)/5', text)
        rating = float(rating_match.group(1)) if rating_match else None

        # 9. Durasi — ekstrak dari teks (misal "24j 55m", "3j", "1j 30m")
        durasi_menit = 0
        dm = re.search(r'(\d+)j(?:\s*(\d+)m)?', text)
        if dm:
            durasi_menit = int(dm.group(1)) * 60 + (int(dm.group(2)) if dm.group(2) else 0)

        return {
            "operator": operator,
            "kelas": kelas,
            "jam_berangkat": jam_berangkat,
            "jam_tiba": jam_tiba,
            "harga_raw": harga_raw,
            "rating": rating,
            "durasi_menit": durasi_menit,
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER: CONVERT TO SEGMENT
    # ─────────────────────────────────────────────────────────────────────────

    def _to_segment(
        self,
        item: dict,
        origin: str,
        destination: str,
        date_str: str,
    ) -> Optional[TransportSegment]:
        try:
            # Parse datetime
            dep_time = self._parse_time(date_str, item["jam_berangkat"])

            # Jika ada durasi dari teks, hitung arr_time dari dep_time + durasi
            # (lebih akurat, menangani perjalanan >24 jam seperti Jakarta→Denpasar)
            if item.get("durasi_menit", 0) > 0:
                arr_time = dep_time + timedelta(minutes=item["durasi_menit"])
                duration = item["durasi_menit"]
            else:
                arr_time = self._parse_time(date_str, item["jam_tiba"])
                if arr_time < dep_time:
                    arr_time += timedelta(days=1)
                duration = int((arr_time - dep_time).total_seconds() / 60)

            return TransportSegment(
                id=f"SEG-BUS-{uuid.uuid4().hex[:8].upper()}",
                mode="bus",
                provider=item["operator"],
                provider_code="BUS",  # Kode umum untuk bus
                origin=origin,
                destination=destination,
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=duration,
                price=float(item["harga_raw"]),
                seat_class=item["kelas"],
                available_seats=None,  # Tiket.com tidak selalu expose sisa seat di list
                rating=item.get("rating"),
            )
        except Exception as e:
            self.logger.debug(f"[BusScraper] Gagal konversi item: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    #  STATIC HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_time(date_str: str, time_str: str) -> datetime:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


# ─── Quick Test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = BusScraper(headless=False)  # Set True untuk mode tanpa UI
    results = scraper.get_segments("Jakarta", "Bandung", "2026-05-20", passengers=1)
    print(f"\n✅ Hasil: {len(results)} bus ditemukan")
    for r in results[:3]:
        print(f"  🚌 {r.provider} | {r.departure_time.time()} -> {r.arrival_time.time()} | Rp {r.price:,.0f}")