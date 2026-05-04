# -*- coding: utf-8 -*-
"""
scraper/train_scraper.py — ANTARA Project
==========================================
Scraper data kereta api: Traveloka (utama) + KAI (fallback)
Dilengkapi teknik anti-bot: human-like behavior, random delay, stealth mode.

Menggunakan Playwright (async) yang dibungkus agar compatible dengan
interface BaseScraper yang sync.

Cara install dependency tambahan:
    pip install playwright
    playwright install chromium

Test standalone:
    python -m scraper.train_scraper
"""

import asyncio
import json
import re
import random
import sqlite3
import sys
import io
from datetime import datetime, timedelta
from typing import Optional

from models import TransportSegment
from scraper.base_scraper import BaseScraper

# Fix encoding Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────────
CONFIG = {
    "headless":    False,
    "timeout":     30_000,
    "output_json": "hasil_kereta.json",
    "output_db":   "hasil_kereta.db",
}

STASIUN_TRAVELOKA = {
    "GMR": "Gambir",
    "PSE": "Pasar Senen",
    "BD":  "Bandung",
    "YK":  "Yogyakarta",
    "SGU": "Surabaya Gubeng",
    "SBI": "Surabaya Pasarturi",
    "SMT": "Semarang Tawang",
    "ML":  "Malang",
    "SLO": "Solo Balapan",
    "CN":  "Cirebon",
}

KOTA_KE_KODE = {
    "Jakarta":    "GMR",
    "Bandung":    "BD",
    "Yogyakarta": "YK",
    "Surabaya":   "SBI",
    "Semarang":   "SMT",
    "Malang":     "ML",
    "Solo":       "SLO",
    "Cirebon":    "CN",
}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER — ANTI BOT
# ══════════════════════════════════════════════════════════════════════════════

async def jeda(min_ms: int = 300, max_ms: int = 1200):
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)

async def gerak_mouse_acak(page, steps: int = 3):
    for _ in range(steps):
        await page.mouse.move(random.randint(100, 1200), random.randint(100, 600))
        await jeda(100, 300)

async def ketik_seperti_manusia(element, teks: str):
    await element.click()
    await jeda(200, 500)
    for i, huruf in enumerate(teks):
        if i < len(teks) - 1 and random.random() < 0.08:
            typo = random.choice("abcdefghijklmnopqrstuvwxyz")
            await element.type(typo, delay=random.randint(60, 150))
            await jeda(150, 400)
            await element.press("Backspace")
            await jeda(100, 250)
        await element.type(huruf, delay=random.randint(60, 180))
    await jeda(200, 600)

async def scroll_pelan(page, arah: str = "down", px: int = 300):
    step = 80 if arah == "down" else -80
    for _ in range(px // abs(step)):
        await page.mouse.wheel(0, step)
        await jeda(50, 150)

async def buat_browser_stealth(playwright):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    ]
    viewports = [
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1920, "height": 1080},
    ]
    browser = await playwright.chromium.launch(
        headless=CONFIG["headless"],
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox", "--disable-infobars",
            "--disable-dev-shm-usage", "--disable-extensions", "--start-maximized",
        ],
    )
    context = await browser.new_context(
        user_agent=random.choice(user_agents),
        viewport=random.choice(viewports),
        locale="id-ID",
        timezone_id="Asia/Jakarta",
        extra_http_headers={
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        },
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins',   { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['id-ID','id','en-US','en'] });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
        });
    """)
    return browser, context


# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER TRAVELOKA (UTAMA)
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_traveloka(page, params: dict) -> list:
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    tgl_obj = datetime.strptime(params["tanggal"], "%Y-%m-%d")
    url = (
        f"https://www.traveloka.com/id-id/kereta-api/search"
        f"?originId={params['asal']}&destinationId={params['tujuan']}"
        f"&departureDate={tgl_obj.strftime('%d-%m-%Y')}&numAdult=1&numChild=0&numInfant=0"
    )
    print("  [INFO] Membuka Traveloka ...")
    await page.goto("https://www.traveloka.com/id-id", timeout=CONFIG["timeout"])
    await jeda(1500, 3000)
    await gerak_mouse_acak(page, 3)
    await scroll_pelan(page, "down", 200)
    await jeda(1000, 2000)

    print("  [INFO] Navigasi ke halaman pencarian kereta ...")
    await page.goto(url, timeout=CONFIG["timeout"])
    await jeda(2000, 4000)
    await scroll_pelan(page, "down", 300)
    await jeda(1000, 2000)

    print("  [INFO] Menunggu hasil kereta muncul ...")
    muncul = False
    for sel in ["[data-testid='train-search-result']", "[class*='TrainCard']",
                "[class*='train-card']", "[class*='journey-card']"]:
        try:
            await page.wait_for_selector(sel, timeout=12_000)
            muncul = True
            print(f"  [OK] Hasil ditemukan: {sel}")
            break
        except PlaywrightTimeout:
            continue

    if not muncul:
        print("  [WARN] Selector tidak cocok, mencoba parse HTML ...")

    await jeda(500, 1000)
    await scroll_pelan(page, "down", 500)
    await jeda(800, 1500)
    return await _ekstrak_traveloka(page, params, datetime.now().isoformat())


async def _ekstrak_traveloka(page, params: dict, waktu_scrape: str) -> list:
    kartu_list = []
    for sel in ["[data-testid='train-search-result']", "[class*='TrainCard']",
                "[class*='train-card']", "[class*='journey-card']", "[class*='JourneyCard']"]:
        kartu_list = await page.query_selector_all(sel)
        if kartu_list:
            print(f"  [INFO] Selector kartu: {sel} ({len(kartu_list)} item)")
            break

    if not kartu_list:
        html = await page.content()
        return _fallback_regex(html, params, waktu_scrape, "traveloka")

    data = []
    for idx, kartu in enumerate(kartu_list):
        try:
            async def teks(sel):
                try:
                    el = await kartu.query_selector(sel)
                    return (await el.inner_text()).strip() if el else ""
                except Exception:
                    return ""

            nama     = await teks("[class*='trainName'],[class*='train-name'],h3,h4")
            kode     = await teks("[class*='trainCode'],[class*='train-code']")
            jam_bgkt = await teks("[class*='departureTime'],[class*='departure-time'],[class*='depart']")
            jam_tiba = await teks("[class*='arrivalTime'],[class*='arrival-time'],[class*='arrive']")
            durasi   = await teks("[class*='duration'],[class*='Duration'],[class*='travel-time']")

            if not kode and nama:
                m = re.search(r'\(([A-Z0-9]+)\)', nama)
                kode = m.group(1) if m else ""

            harga_list = []
            for el in await kartu.query_selector_all("[class*='price'],[class*='Price'],[class*='fare']"):
                try:
                    t = (await el.inner_text()).strip()
                    if t and "Rp" in t:
                        harga_list.append(t)
                except Exception:
                    pass

            kelas_list = []
            for el in await kartu.query_selector_all("[class*='class'],[class*='kelas'],[class*='seat']"):
                try:
                    t = (await el.inner_text()).strip()
                    if t and len(t) < 30:
                        kelas_list.append(t)
                except Exception:
                    pass

            kursi_list = []
            for el in await kartu.query_selector_all("[class*='seat'],[class*='available'],[class*='sisa']"):
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        kursi_list.append(t)
                except Exception:
                    pass

            if not nama and not jam_bgkt:
                continue

            item = {
                "urutan": idx + 1, "sumber": "traveloka",
                "nama_kereta":    nama.split("(")[0].strip() if "(" in nama else nama,
                "kode_kereta":    kode,
                "stasiun_asal":   params["asal"],
                "stasiun_tujuan": params["tujuan"],
                "tanggal":        params["tanggal"],
                "jam_berangkat":  jam_bgkt, "jam_tiba": jam_tiba, "durasi": durasi,
                "kelas":          list(dict.fromkeys(kelas_list)),
                "harga":          list(dict.fromkeys(harga_list)),
                "kursi_tersedia": kursi_list,
                "waktu_scrape":   waktu_scrape,
            }
            data.append(item)
            print(f"  [OK] [{idx+1}] {item['nama_kereta'] or '?'} - {jam_bgkt} -> {jam_tiba}")
        except Exception as e:
            print(f"  [WARN] Gagal ekstrak [{idx+1}]: {e}")

    return data


# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER KAI (FALLBACK)
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_kai(page, params: dict) -> list:
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    waktu_scrape = datetime.now().isoformat()

    print("  [INFO] Membuka kai.id ...")
    await page.goto("https://kai.id", timeout=CONFIG["timeout"])
    await jeda(1500, 3000)
    await gerak_mouse_acak(page, 2)
    await scroll_pelan(page, "down", 150)
    await jeda(1000, 2000)

    print("  [INFO] Mengisi form pencarian KAI ...")
    await _isi_form_kai(page, params)

    print("  [INFO] Menunggu hasil KAI ...")
    for sel in [".train-card", ".schedule-item", "[data-testid*='train']", ".result-card"]:
        try:
            await page.wait_for_selector(sel, timeout=15_000)
            print(f"  [OK] Hasil KAI: {sel}")
            break
        except PlaywrightTimeout:
            continue

    await jeda(500, 1000)
    await scroll_pelan(page, "down", 400)
    await jeda(500, 1000)

    kartu_list = await page.query_selector_all(
        ".train-card,.schedule-item,[data-testid*='train'],.result-card,.kereta-item"
    )
    if not kartu_list:
        html = await page.content()
        return _fallback_regex(html, params, waktu_scrape, "kai")

    data = []
    for idx, kartu in enumerate(kartu_list):
        try:
            async def teks_kai(sel):
                try:
                    el = await kartu.query_selector(sel)
                    return (await el.inner_text()).strip() if el else ""
                except Exception:
                    return ""

            nama   = await teks_kai(".train-name,.kereta-name,h3,h4,[data-testid*='name']")
            kode   = await teks_kai(".train-code,[data-testid*='code']")
            bgkt   = await teks_kai(".departure-time,.jam-berangkat,[data-testid*='departure']")
            tiba   = await teks_kai(".arrival-time,.jam-tiba,[data-testid*='arrival']")
            durasi = await teks_kai(".duration,.durasi,[data-testid*='duration']")

            harga_list = []
            for el in await kartu.query_selector_all(".price,.harga,[data-testid*='price'],.fare"):
                try:
                    t = (await el.inner_text()).strip()
                    if t: harga_list.append(t)
                except Exception:
                    pass

            kelas_list = []
            for el in await kartu.query_selector_all(".class,.kelas,[data-testid*='class']"):
                try:
                    t = (await el.inner_text()).strip()
                    if t: kelas_list.append(t)
                except Exception:
                    pass

            kursi_list = []
            for el in await kartu.query_selector_all(".seat,.kursi,.available,[data-testid*='seat']"):
                try:
                    t = (await el.inner_text()).strip()
                    if t: kursi_list.append(t)
                except Exception:
                    pass

            if not nama:
                continue

            data.append({
                "urutan": idx + 1, "sumber": "kai",
                "nama_kereta": nama.split("(")[0].strip(), "kode_kereta": kode,
                "stasiun_asal": params["asal"], "stasiun_tujuan": params["tujuan"],
                "tanggal": params["tanggal"],
                "jam_berangkat": bgkt, "jam_tiba": tiba, "durasi": durasi,
                "kelas": kelas_list, "harga": harga_list, "kursi_tersedia": kursi_list,
                "waktu_scrape": waktu_scrape,
            })
            print(f"  [OK] [{idx+1}] {nama} - {bgkt} -> {tiba}")
        except Exception as e:
            print(f"  [WARN] Gagal ekstrak KAI [{idx+1}]: {e}")

    return data


async def _isi_form_kai(page, params: dict):
    from playwright.async_api import TimeoutError as PlaywrightTimeout

    for sel in ["input[placeholder*='asal']", "input[placeholder*='Asal']",
                "[data-testid*='origin'] input", "#origin"]:
        try:
            if await page.locator(sel).count() > 0:
                el = page.locator(sel).first
                await ketik_seperti_manusia(el, params["asal"])
                await jeda(800, 1500)
                try:
                    await page.locator(f"li:has-text('{params['asal']}'),[role='option']:has-text('{params['asal']}')").first.click(timeout=3000)
                except PlaywrightTimeout:
                    await el.press("Enter")
                break
        except Exception:
            continue

    await jeda(500, 1000)

    for sel in ["input[placeholder*='tujuan']", "input[placeholder*='Tujuan']",
                "[data-testid*='destination'] input", "#destination"]:
        try:
            if await page.locator(sel).count() > 0:
                el = page.locator(sel).first
                await ketik_seperti_manusia(el, params["tujuan"])
                await jeda(800, 1500)
                try:
                    await page.locator(f"li:has-text('{params['tujuan']}'),[role='option']:has-text('{params['tujuan']}')").first.click(timeout=3000)
                except PlaywrightTimeout:
                    await el.press("Enter")
                break
        except Exception:
            continue

    await jeda(500, 1000)

    for sel in ["input[type='date']", "[data-testid*='date'] input", "input[placeholder*='tanggal']"]:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).first.fill(params["tanggal"])
                break
        except Exception:
            continue

    await jeda(600, 1200)
    await gerak_mouse_acak(page, 2)

    for sel in ["button:has-text('Cari')", "button:has-text('Search')", "button[type='submit']"]:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).first.click()
                break
        except Exception:
            continue


# ══════════════════════════════════════════════════════════════════════════════
#  FALLBACK REGEX
# ══════════════════════════════════════════════════════════════════════════════

def _fallback_regex(html: str, params: dict, waktu_scrape: str, sumber: str) -> list:
    print("  [WARN] Menggunakan fallback regex parser ...")
    jam_list   = re.findall(r'\b(\d{2}:\d{2})\b', html)
    harga_list = re.findall(r'Rp\s?[\d.,]+', html)
    nama_list  = list(dict.fromkeys(re.findall(
        r'(Argo\s?\w+|Gajayana|Bangunkarta|Taksaka|Bima|Lodaya|'
        r'Parahyangan|Sancaka|Jayabaya|Malabar|Sembrani|Gumarang|'
        r'Turangga|Brantas|Majapahit|Mataram)',
        html, re.IGNORECASE
    )))
    return [
        {
            "urutan": i + 1, "sumber": sumber + "_fallback",
            "nama_kereta": nama.strip(), "kode_kereta": "",
            "stasiun_asal": params["asal"], "stasiun_tujuan": params["tujuan"],
            "tanggal": params["tanggal"],
            "jam_berangkat": jam_list[i*2]   if len(jam_list)   > i*2   else "",
            "jam_tiba":      jam_list[i*2+1] if len(jam_list)   > i*2+1 else "",
            "durasi": "",
            "kelas": [], "harga": [harga_list[i]] if len(harga_list) > i else [],
            "kursi_tersedia": [], "waktu_scrape": waktu_scrape,
            "catatan": "data dari fallback regex parser",
        }
        for i, nama in enumerate(nama_list)
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  CONVERTER: dict → TransportSegment
# ══════════════════════════════════════════════════════════════════════════════

def _dict_to_segment(item: dict, idx: int, passengers: int) -> Optional[TransportSegment]:
    try:
        tanggal  = item.get("tanggal", datetime.today().strftime("%Y-%m-%d"))
        jam_bgkt = item.get("jam_berangkat", "")
        jam_tiba = item.get("jam_tiba", "")
        if not jam_bgkt or not jam_tiba:
            return None

        departure = datetime.strptime(f"{tanggal} {jam_bgkt}", "%Y-%m-%d %H:%M")
        arrival   = datetime.strptime(f"{tanggal} {jam_tiba}",  "%Y-%m-%d %H:%M")
        if arrival < departure:
            arrival += timedelta(days=1)

        duration_min = int((arrival - departure).total_seconds() / 60)

        harga_raw   = item.get("harga", [])
        harga_angka = float(re.sub(r"[^\d]", "", harga_raw[0] if harga_raw else "0") or "0") * passengers

        kelas_list = item.get("kelas", [])
        kursi_raw  = item.get("kursi_tersedia", [])
        available  = None
        if kursi_raw:
            m = re.search(r'\d+', kursi_raw[0])
            available = int(m.group()) if m else None

        return TransportSegment(
            id               = f"SEG-TRAIN-{idx:03d}",
            mode             = "train",
            provider         = item.get("nama_kereta", "KAI"),
            provider_code    = item.get("kode_kereta", "KA"),
            origin           = STASIUN_TRAVELOKA.get(item.get("stasiun_asal", ""), item.get("stasiun_asal", "")),
            destination      = STASIUN_TRAVELOKA.get(item.get("stasiun_tujuan", ""), item.get("stasiun_tujuan", "")),
            departure_time   = departure,
            arrival_time     = arrival,
            duration_minutes = duration_min,
            price            = harga_angka,
            seat_class       = kelas_list[0] if kelas_list else "Economy",
            available_seats  = available,
            rating           = None,
        )
    except Exception as e:
        print(f"  [WARN] Gagal konversi TransportSegment: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  OUTPUT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def simpan_json(data: list, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] Disimpan ke JSON  : {filepath}")

def simpan_sql(data: list, filepath: str):
    conn = sqlite3.connect(filepath)
    cur  = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS kereta (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sumber TEXT, urutan INTEGER,
        nama_kereta TEXT, kode_kereta TEXT, stasiun_asal TEXT, stasiun_tujuan TEXT,
        tanggal TEXT, jam_berangkat TEXT, jam_tiba TEXT, durasi TEXT,
        waktu_scrape TEXT, catatan TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS harga (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kereta_id INTEGER,
        kelas TEXT, harga TEXT, kursi TEXT,
        FOREIGN KEY (kereta_id) REFERENCES kereta(id))""")
    for item in data:
        cur.execute("""INSERT INTO kereta
            (sumber,urutan,nama_kereta,kode_kereta,stasiun_asal,stasiun_tujuan,
             tanggal,jam_berangkat,jam_tiba,durasi,waktu_scrape,catatan)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            item.get("sumber"), item.get("urutan"), item.get("nama_kereta"),
            item.get("kode_kereta"), item.get("stasiun_asal"), item.get("stasiun_tujuan"),
            item.get("tanggal"), item.get("jam_berangkat"), item.get("jam_tiba"),
            item.get("durasi"), item.get("waktu_scrape"), item.get("catatan",""),
        ))
        kereta_id = cur.lastrowid
        kls = item.get("kelas", []); hrg = item.get("harga", []); krs = item.get("kursi_tersedia", [])
        for i in range(max(len(kls), len(hrg), len(krs), 1)):
            cur.execute("INSERT INTO harga (kereta_id,kelas,harga,kursi) VALUES (?,?,?,?)", (
                kereta_id,
                kls[i] if i < len(kls) else "",
                hrg[i] if i < len(hrg) else "",
                krs[i] if i < len(krs) else "",
            ))
    conn.commit()
    conn.close()
    print(f"  [OK] Disimpan ke SQLite: {filepath}")


# ══════════════════════════════════════════════════════════════════════════════
#  ASYNC CORE
# ══════════════════════════════════════════════════════════════════════════════

async def _run_scraper(params: dict) -> list:
    from playwright.async_api import async_playwright
    hasil = []
    async with async_playwright() as p:
        browser, context = await buat_browser_stealth(p)
        page = await context.new_page()
        try:
            print("=" * 50)
            print("  [STEP 1] Mencoba scraping dari Traveloka ...")
            print("=" * 50)
            hasil = await scrape_traveloka(page, params)
            if not hasil:
                print("\n  [WARN] Traveloka kosong, fallback ke KAI ...")
                print("=" * 50)
                print("  [STEP 2] Fallback ke KAI ...")
                print("=" * 50)
                await jeda(1500, 3000)
                hasil = await scrape_kai(page, params)
                if not hasil:
                    print("\n  [FAIL] Kedua sumber tidak menghasilkan data.")
            else:
                print(f"\n  [OK] Traveloka berhasil! {len(hasil)} kereta ditemukan.")
        except Exception as e:
            print(f"\n  [ERROR] {e}")
            raise
        finally:
            await browser.close()
    return hasil


# ══════════════════════════════════════════════════════════════════════════════
#  CLASS TrainScraper — INTERFACE UNTUK OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════

class TrainScraper(BaseScraper):
    """
    Scraper kereta api yang compatible dengan SmartRouteOptimizer.

    Secara internal menggunakan Playwright (async) dibungkus asyncio.run()
    supaya interface get_segments() tetap sync sesuai kontrak BaseScraper.

    Cara pakai dari optimizer:
        scraper = TrainScraper(headless=True)
        segments = scraper.get_segments("Jakarta", "Surabaya", "2026-05-10", passengers=2)
    """

    MODE = "train"

    def __init__(self, headless: bool = True, timeout: int = 30):
        super().__init__(headless=headless, timeout=timeout)
        CONFIG["headless"] = headless
        CONFIG["timeout"]  = timeout * 1000

    def _scrape(self, origin: str, destination: str, date_str: str, passengers: int) -> list:
        """Jalankan Playwright async → konversi ke list[TransportSegment]."""
        asal_kode   = KOTA_KE_KODE.get(origin,      origin[:3].upper())
        tujuan_kode = KOTA_KE_KODE.get(destination, destination[:3].upper())

        raw_data = asyncio.run(_run_scraper({
            "asal": asal_kode, "tujuan": tujuan_kode, "tanggal": date_str,
        }))

        segments = []
        for idx, item in enumerate(raw_data):
            seg = _dict_to_segment(item, idx + 1, passengers)
            if seg:
                segments.append(seg)
        return segments


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE MODE — test langsung tanpa optimizer
# ══════════════════════════════════════════════════════════════════════════════

async def _main_standalone():
    print("\n+====================================================+")
    print("|   SCRAPER TIKET KERETA - Traveloka + KAI           |")
    print("+====================================================+")

    print("\nPilih mode input:")
    print("  [1] Input manual (terminal)")
    print("  [2] Hardcode testing (GMR -> BD, hari ini)")
    pilihan = input("\nPilihan (1/2): ").strip()

    if pilihan == "1":
        print("\nKode stasiun:")
        for kode, nama in STASIUN_TRAVELOKA.items():
            print(f"  {kode:6s} - {nama}")
        print()
        params = {
            "asal":    input("Kode stasiun ASAL   (contoh: GMR) : ").strip().upper(),
            "tujuan":  input("Kode stasiun TUJUAN (contoh: BD)  : ").strip().upper(),
            "tanggal": input("Tanggal (YYYY-MM-DD)               : ").strip(),
        }
    else:
        params = {"asal": "GMR", "tujuan": "BD", "tanggal": datetime.today().strftime("%Y-%m-%d")}

    print("\nPilih mode browser:")
    print("  [1] Headed - browser kelihatan (DISARANKAN)")
    print("  [2] Headless - tanpa tampilan")
    CONFIG["headless"] = (input("\nPilihan (1/2): ").strip() == "2")

    hasil = await _run_scraper(params)
    if not hasil:
        return

    simpan_json(hasil, CONFIG["output_json"])
    simpan_sql(hasil,  CONFIG["output_db"])
    print(f"\n  Total: {len(hasil)} kereta | Sumber: {set(d['sumber'] for d in hasil)}")
    print("\n  [DONE] Selesai!")


if __name__ == "__main__":
    asyncio.run(_main_standalone())
