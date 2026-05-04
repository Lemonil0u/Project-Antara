import asyncio
import re
import random
import uuid
from datetime import datetime
from typing import List, Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper

STATION_CODES = {
    "Jakarta":    "GMR",
    "Bandung":    "BD",
    "Yogyakarta": "YK",
    "Semarang":   "SMT",
    "Surabaya":   "SBI",
    "Malang":     "ML",
    "Solo":       "SLO",
    "Cirebon":    "CN",
    "Purwokerto": "PWT",
}

NOISE_KEYWORDS = ["URUTKAN", "Waktu\nWaktu", "Kelas\nKelas", "Kereta\nKereta"]


class TrainScraper(BaseScraper):
    MODE = "train"

    def _scrape(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> List[TransportSegment]:
        """
        Sinkron wrapper — memanggil _scrape_async() via asyncio.run().
        """
        return asyncio.run(self._scrape_async(origin, destination, date_str, passengers))

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

        origin_code = STATION_CODES.get(origin, origin[:3].upper())
        dest_code   = STATION_CODES.get(destination, destination[:3].upper())

        # Format tanggal untuk URL Traveloka: D-M-YYYY.null
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        dt_str = f"{dt_obj.day}-{dt_obj.month}-{dt_obj.year}.null"

        url = (
            f"https://www.traveloka.com/id-id/kereta-api/search"
            f"?st={origin_code}.{dest_code}"
            f"&dt={dt_str}"
            f"&ps={passengers}.0"
            f"&pd=KAI"
        )

        self.logger.info(f"[TrainScraper] URL: {url}")

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
            # Sembunyikan tanda bot
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            page = await context.new_page()

            try:
                await page.goto(url, timeout=60000, wait_until="load")
                await self._human_behavior(page)

                self.logger.info("[TrainScraper] Menunggu hasil kereta...")

                result_found = await self._wait_for_results(page)

                if not result_found:
                    self.logger.info("[TrainScraper] Tidak ada hasil kereta ditemukan di halaman.")
                    return segments

                cards = await self._get_train_cards(page)
                self.logger.info(f"[TrainScraper] Raw cards: {len(cards)}")

                raw_items = []
                for i, card in enumerate(cards):
                    try:
                        full_text = await card.inner_text()

                        # Skip toolbar/header Traveloka
                        if any(kw in full_text for kw in NOISE_KEYWORDS):
                            continue

                        # Skip card yang terlalu pendek (pasti bukan card kereta lengkap)
                        # Card kereta minimal punya: nama, jam, harga → minimal ~30 karakter
                        if len(full_text.strip()) < 30:
                            continue

                        item = self._parse_card(full_text, origin, destination, date_str, passengers)
                        if item:
                            raw_items.append(item)

                    except Exception as e:
                        self.logger.warning(f"[TrainScraper] Card {i+1} gagal diparse: {e}")
                        continue

                # Deduplikasi
                seen = set()
                for item in raw_items:
                    key = (
                        item["nama_kereta"], item["kelas"],
                        item["jam_berangkat"], item["jam_tiba"], item["harga_raw"]
                    )
                    if key not in seen and item["harga_raw"] > 0:
                        seen.add(key)
                        seg = self._to_segment(item, origin, destination, date_str)
                        if seg:
                            segments.append(seg)

                self.logger.info(f"[TrainScraper] {len(segments)} kereta unik ditemukan.")

            except Exception as e:
                self.logger.error(f"[TrainScraper] Scraping gagal: {e}")
                try:
                    await page.screenshot(path="train_scraper_error.png")
                    self.logger.info("[TrainScraper] Screenshot disimpan → train_scraper_error.png")
                except Exception:
                    pass

            finally:
                await browser.close()

        return segments

    async def _wait_for_results(self, page) -> bool:
        try:
            await page.locator("text=Pilih").first.wait_for(state="visible", timeout=45000)
            self.logger.info("[TrainScraper] Tombol 'Pilih' ditemukan → ada hasil.")
            return True
        except Exception:
            self.logger.warning("[TrainScraper] Timeout nunggu 'Pilih', coba cek 'tidak ditemukan'...")

        try:
            no_result = page.locator("text=tidak ditemukan").or_(
                page.locator("text=Tidak ada kereta")
            ).or_(
                page.locator("text=Tidak ada hasil")
            )
            await no_result.first.wait_for(state="visible", timeout=10000)
            self.logger.info("[TrainScraper] Halaman konfirmasi tidak ada kereta.")
            return False
        except Exception:
            self.logger.warning("[TrainScraper] Tidak ketemu teks 'tidak ditemukan' juga.")

        self.logger.warning("[TrainScraper] Fallback keras: lanjut scrape meski selector tidak ketemu.")
        await asyncio.sleep(3)  # kasih waktu extra buat render
        return True

    async def _get_train_cards(self, page) -> list:
        try:
            pilih_buttons = await page.locator("text=Pilih").all()
            if len(pilih_buttons) > 2:  # minimal ada beberapa hasil
                cards = []
                for btn in pilih_buttons:
                    try:
                        for _ in range(5):
                            parent = btn.locator("xpath=..")
                            parent_text = await parent.inner_text()
                            if "Rp" in parent_text and ":" in parent_text:
                                cards.append(parent)
                                break
                            btn = parent
                    except Exception:
                        continue

                if cards:
                    self.logger.info(f"[TrainScraper] Strategi 1 berhasil: {len(cards)} cards.")
                    return cards
        except Exception as e:
            self.logger.warning(f"[TrainScraper] Strategi 1 gagal: {e}")

        try:
            all_divs = await page.locator("div").all()
            cards = []
            for div in all_divs:
                try:
                    text = await div.inner_text()
                    has_price = "Rp" in text
                    has_time  = bool(re.search(r'\b\d{2}:\d{2}\b', text))
                    has_pilih = "Pilih" in text
                    reasonable_length = 50 < len(text.strip()) < 2000

                    if has_price and has_time and has_pilih and reasonable_length:
                        cards.append(div)
                except Exception:
                    continue

            if cards:
                self.logger.info(f"[TrainScraper] Strategi 2 berhasil: {len(cards)} cards.")
                return cards
        except Exception as e:
            self.logger.warning(f"[TrainScraper] Strategi 2 gagal: {e}")

        self.logger.warning("[TrainScraper] Fallback ke strategi 3 (cara lama).")
        return await page.locator("div:has-text('Pilih')").all()

    def _parse_card(
        self,
        text: str,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int,
    ) -> Optional[dict]:

        # Nama kereta, e.g. "Argo Bromo Anggrek (1)"
        nama_match = re.search(r'([A-Za-z\s]+?\s*\(\d+[A-Z]*\))', text)
        nama = nama_match.group(1).strip() if nama_match else "Unknown"

        # Kelas, e.g. "Eksekutif (EKS)"
        kelas_match = re.search(r'(Eksekutif|Ekonomi|Bisnis)\s*\(([A-Z]+)\)', text)
        kelas = f"{kelas_match.group(1)} ({kelas_match.group(2)})" if kelas_match else ""
        seat_class = kelas_match.group(1) if kelas_match else None

        # Jam berangkat & tiba
        times = re.findall(r'\b\d{2}:\d{2}\b', text)
        jam_bgkt = times[0] if len(times) > 0 else ""
        jam_tiba = times[1] if len(times) > 1 else ""

        # Harga
        harga_match = re.search(r'Rp\s?[\d.,]+', text)
        harga_str = harga_match.group(0) if harga_match else "Rp 0"
        harga_raw = self._parse_price(harga_str)

        # Skip jika tidak ada data yang berarti
        if nama == "Unknown" and not kelas and harga_raw == 0:
            return None

        return {
            "nama_kereta"  : nama,
            "kelas"        : kelas,
            "seat_class"   : seat_class,
            "jam_berangkat": jam_bgkt,
            "jam_tiba"     : jam_tiba,
            "harga_str"    : harga_str,
            "harga_raw"    : harga_raw,
        }

    def _to_segment(
        self,
        item: dict,
        origin: str,
        destination: str,
        date_str: str,
    ) -> Optional[TransportSegment]:
        try:
            departure_time = self._parse_time(date_str, item["jam_berangkat"])
            arrival_time   = self._parse_time(date_str, item["jam_tiba"])

            if arrival_time < departure_time:
                from datetime import timedelta
                arrival_time += timedelta(days=1)

            duration_minutes = int((arrival_time - departure_time).total_seconds() / 60)

            return TransportSegment(
                id               = f"SEG-TRAIN-{uuid.uuid4().hex[:8].upper()}",
                mode             = "train",
                provider         = item["nama_kereta"],
                provider_code    = "KA",
                origin           = origin,
                destination      = destination,
                departure_time   = departure_time,
                arrival_time     = arrival_time,
                duration_minutes = duration_minutes,
                price            = float(item["harga_raw"]),
                seat_class       = item.get("seat_class"),
                available_seats  = None,   # Traveloka tidak tampilkan jumlah kursi
                rating           = None,
            )
        except Exception as e:
            self.logger.warning(f"[TrainScraper] Gagal konversi ke segment: {e}")
            return None

    @staticmethod
    def _parse_price(price_str: str) -> int:
        """'Rp 250.000' → 250000"""
        digits = re.sub(r'[^\d]', '', price_str)
        return int(digits) if digits else 0

    @staticmethod
    def _parse_time(date_str: str, time_str: str) -> datetime:
        """Gabungkan date_str 'YYYY-MM-DD' + time_str 'HH:MM' → datetime."""
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    @staticmethod
    async def _human_behavior(page) -> None:
        """Simulasi perilaku manusia agar tidak terdeteksi bot."""
        import random
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