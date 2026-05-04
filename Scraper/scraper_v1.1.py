import asyncio
import json
import random
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

CONFIG = {
    "headless": False,
    "timeout": 90000,
    "output_json": "hasil_kereta_traveloka.json",
}

async def human_delay(min_sec=1.5, max_sec=4.0):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def gentle_human_behavior(page):
    await page.mouse.move(random.randint(100, 800), random.randint(100, 500), steps=10)
    await human_delay(1.0, 2.5)
    for _ in range(random.randint(2, 3)):
        await page.mouse.wheel(0, random.randint(100, 300))
        await human_delay(0.8, 1.8)
    await human_delay(1.5, 3.0)

async def scrape_traveloka_v10():
    print("\n" + "="*85)
    print("STASIUN KERETA API\n BD = Bandung\n CN = Cirebon\n GMR = Gambir\n PSE = Pasar Senen\n ML = Malang\n SMC = Semarang Poncol\n SMT = Semarang Tawang\n SBI = Surabaya Pasar Turi\n YK = Yogyakarta")
    print("="*85)

    asal      = input("Kode stasiun ASAL     : ").strip().upper()
    tujuan    = input("Kode stasiun TUJUAN   : ").strip().upper()
    tanggal   = input("Tanggal (YYYY-MM-DD)  : ").strip()
    num_adult = input("Jumlah dewasa         : ").strip() or "1"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=CONFIG["headless"], args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="id-ID",
            timezone_id="Asia/Jakarta",
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        page = await context.new_page()

        try:
            dt_obj = datetime.strptime(tanggal, "%Y-%m-%d")
            dt_str = f"{dt_obj.day}-{dt_obj.month}-{dt_obj.year}.null"
            url = f"https://www.traveloka.com/id-id/kereta-api/search?st={asal}.{tujuan}&dt={dt_str}&ps={num_adult}.0&pd=KAI"

            print(f"\n🔗 URL: {url}")
            await page.goto(url, timeout=CONFIG["timeout"], wait_until="networkidle")
            await gentle_human_behavior(page)

            print("⏳ Menunggu hasil kereta...")
            await page.wait_for_selector("text=Pilih", timeout=40000)

            cards = await page.locator("div:has-text('Pilih')").all()
            print(f"   Raw cards ditemukan: {len(cards)} (sebelum filter)")

            hasil_baru = []
            for i, card in enumerate(cards):
                try:
                    full_text = await card.inner_text()

                    # FIX 1: Skip header/toolbar — mengandung kata UI bukan data kereta
                    noise_keywords = ["URUTKAN", "Waktu\nWaktu", "Kelas\nKelas", "Kereta\nKereta"]
                    if any(kw in full_text for kw in noise_keywords):
                        continue

                    # Parsing
                    nama_match = re.search(r'([A-Za-z\s]+?\s*\(\d+[A-Z]*\))', full_text)
                    nama = nama_match.group(1).strip() if nama_match else "Unknown"

                    kelas_match = re.search(r'(Eksekutif|Ekonomi|Bisnis)\s*\(([A-Z]+)\)', full_text)
                    kelas = f"{kelas_match.group(1)} ({kelas_match.group(2)})" if kelas_match else ""

                    times = re.findall(r'\b\d{2}:\d{2}\b', full_text)
                    jam_bgkt = times[0] if len(times) > 0 else ""
                    jam_tiba = times[1] if len(times) > 1 else ""

                    harga_match = re.search(r'Rp\s?[\d.,]+', full_text)
                    harga = harga_match.group(0) if harga_match else ""

                    item = {
                        "urutan": -1,           # Di-assign ulang setelah dedup
                        "sumber": "traveloka",
                        "nama_kereta": nama,
                        "kelas": kelas,
                        "jam_berangkat": jam_bgkt,
                        "jam_tiba": jam_tiba,
                        "harga": harga,
                        "stasiun_asal": asal,
                        "stasiun_tujuan": tujuan,
                        "tanggal": tanggal,
                        "num_adult": num_adult,
                        "waktu_scrape": datetime.now().isoformat()
                    }
                    hasil_baru.append(item)

                except Exception as e:
                    print(f"   [SKIP] Card {i+1} gagal diekstrak: {e}")
                    continue

            # FIX 2: Deduplikasi berdasarkan kombinasi unik, skip "Unknown" tanpa data
            seen = set()
            hasil_dedup = []
            for item in hasil_baru:
                key = (item["nama_kereta"], item["kelas"], item["jam_berangkat"],
                       item["jam_tiba"], item["harga"])
                # Skip entry kosong sama sekali
                if not any([item["nama_kereta"] != "Unknown", item["kelas"], item["harga"]]):
                    continue
                if key not in seen:
                    seen.add(key)
                    hasil_dedup.append(item)

            # Re-assign urutan setelah dedup
            for idx, item in enumerate(hasil_dedup):
                item["urutan"] = idx + 1

            # Print hasil bersih
            print(f"✅ Ditemukan {len(hasil_dedup)} kereta unik (dari {len(hasil_baru)} raw)")
            for item in hasil_dedup:
                print(f"   [{item['urutan']}] {item['nama_kereta']} | {item['kelas']} | {item['jam_berangkat']} → {item['jam_tiba']} | {item['harga']}")

            # Auto append JSON
            existing = []
            if os.path.exists(CONFIG["output_json"]):
                with open(CONFIG["output_json"], "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        existing = json.loads(content)

            final = existing + hasil_dedup
            with open(CONFIG["output_json"], "w", encoding="utf-8") as f:
                json.dump(final, f, ensure_ascii=False, indent=2)

            print(f"\n✅ BERHASIL! Total data: {len(final)} disimpan ke {CONFIG['output_json']}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            await page.screenshot(path="traveloka_error.png")
            print("Screenshot disimpan → traveloka_error.png")
        finally:
            input("\nTekan ENTER untuk tutup browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_traveloka_v10())