# -*- coding: utf-8 -*-
"""
scraper_v2.py - Scraper tiket kereta: Traveloka (utama) + KAI (fallback)
Dilengkapi teknik anti-bot: human-like behavior, random delay, stealth mode

Cara install:
    pip install playwright
    playwright install chromium

Cara pakai:
    python scraper_v2.py
"""

import asyncio
import json
import sqlite3
import re
import random
import sys
import io
import time
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Fix encoding Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────────
CONFIG = {
    "headless":    False,         # False = headed (lebih aman dari bot detection)
    "timeout":     30_000,        # ms
    "output_json": "hasil_kereta.json",
    "output_db":   "hasil_kereta.db",
}

# Nama stasiun lengkap untuk Traveloka (pakai nama kota/stasiun, bukan kode)
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


# ─────────────────────────────────────────────
#  HUMAN BEHAVIOR — ANTI BOT
# ─────────────────────────────────────────────
async def jeda(min_ms: int = 300, max_ms: int = 1200):
    """Jeda acak layaknya manusia berpikir sebelum aksi."""
    delay = random.randint(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def gerak_mouse_acak(page, steps: int = 3):
    """Gerakkan mouse ke posisi acak beberapa kali sebelum klik."""
    for _ in range(steps):
        x = random.randint(100, 1200)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        await jeda(100, 300)


async def ketik_seperti_manusia(element, teks: str):
    """
    Ketik teks karakter per karakter dengan delay acak,
    sesekali salah ketik lalu hapus (simulasi human typo).
    """
    await element.click()
    await jeda(200, 500)

    for i, huruf in enumerate(teks):
        # 8% chance typo pada karakter bukan terakhir
        if i < len(teks) - 1 and random.random() < 0.08:
            typo = random.choice("abcdefghijklmnopqrstuvwxyz")
            await element.type(typo, delay=random.randint(60, 150))
            await jeda(150, 400)
            await element.press("Backspace")
            await jeda(100, 250)

        await element.type(huruf, delay=random.randint(60, 180))

    await jeda(200, 600)


async def scroll_pelan(page, arah: str = "down", px: int = 300):
    """Scroll halaman perlahan seperti manusia membaca."""
    step = 80 if arah == "down" else -80
    total = px // abs(step)
    for _ in range(total):
        await page.mouse.wheel(0, step)
        await jeda(50, 150)


async def buat_browser_stealth(playwright):
    """
    Buat browser dengan konfigurasi stealth:
    - User-agent Chrome asli
    - Viewport layar laptop umum
    - Locale & timezone Indonesia
    - Sembunyikan tanda-tanda otomasi
    """
    # Pilih acak dari beberapa user agent Chrome terbaru
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    ]
    viewports = [
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080},
    ]

    browser = await playwright.chromium.launch(
        headless=CONFIG["headless"],
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--start-maximized",
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

    # Injeksi script stealth — sembunyikan navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
        });
    """)

    return browser, context


# ─────────────────────────────────────────────
#  INPUT HELPER
# ─────────────────────────────────────────────
def input_dari_user() -> dict:
    print("\n" + "=" * 50)
    print("  Scraper Tiket Kereta - Input Pencarian")
    print("=" * 50)
    print("\nKode stasiun:")
    for kode, nama in STASIUN_TRAVELOKA.items():
        print(f"  {kode:6s} - {nama}")
    print()
    asal   = input("Kode stasiun ASAL   (contoh: GMR) : ").strip().upper()
    tujuan = input("Kode stasiun TUJUAN (contoh: BD)  : ").strip().upper()
    tgl    = input("Tanggal (YYYY-MM-DD)               : ").strip()
    return {"asal": asal, "tujuan": tujuan, "tanggal": tgl}


def input_hardcode() -> dict:
    return {
        "asal":    "GMR",
        "tujuan":  "BD",
        "tanggal": datetime.today().strftime("%Y-%m-%d"),
    }


# ─────────────────────────────────────────────
#  SCRAPER TRAVELOKA (UTAMA)
# ─────────────────────────────────────────────
async def scrape_traveloka(page, params: dict) -> list[dict]:
    """Scrape jadwal kereta dari Traveloka."""
    hasil   = []
    asal_nama   = STASIUN_TRAVELOKA.get(params["asal"],   params["asal"])
    tujuan_nama = STASIUN_TRAVELOKA.get(params["tujuan"], params["tujuan"])
    tgl_obj     = datetime.strptime(params["tanggal"], "%Y-%m-%d")

    # Format URL langsung ke halaman hasil kereta Traveloka
    # dd-MM-yyyy
    tgl_url = tgl_obj.strftime("%d-%m-%Y")
    url = (
        f"https://www.traveloka.com/id-id/kereta-api/search"
        f"?originId={params['asal']}"
        f"&destinationId={params['tujuan']}"
        f"&departureDate={tgl_url}"
        f"&numAdult=1&numChild=0&numInfant=0"
    )

    print(f"  [INFO] Membuka Traveloka ...")
    await page.goto("https://www.traveloka.com/id-id", timeout=CONFIG["timeout"])
    await jeda(1500, 3000)
    await gerak_mouse_acak(page, 3)
    await scroll_pelan(page, "down", 200)
    await jeda(1000, 2000)

    print(f"  [INFO] Navigasi ke halaman pencarian kereta ...")
    await page.goto(url, timeout=CONFIG["timeout"])
    await jeda(2000, 4000)
    await scroll_pelan(page, "down", 300)
    await jeda(1000, 2000)

    # Tunggu hasil muncul
    print(f"  [INFO] Menunggu hasil kereta muncul ...")
    result_selectors = [
        "[data-testid='train-search-result']",
        "[class*='TrainCard']",
        "[class*='train-card']",
        "[class*='SearchResult']",
        "[class*='journey-card']",
        "div[class*='Card']:has(div[class*='time'])",
    ]

    muncul = False
    for sel in result_selectors:
        try:
            await page.wait_for_selector(sel, timeout=12_000)
            muncul = True
            print(f"  [OK] Hasil ditemukan dengan selector: {sel}")
            break
        except PlaywrightTimeout:
            continue

    if not muncul:
        print("  [WARN] Selector otomatis tidak cocok, mencoba parse HTML ...")

    await jeda(500, 1000)
    await scroll_pelan(page, "down", 500)
    await jeda(800, 1500)

    # Ekstrak data
    waktu_scrape = datetime.now().isoformat()
    hasil = await _ekstrak_traveloka(page, params, waktu_scrape)

    return hasil


async def _ekstrak_traveloka(page, params: dict, waktu_scrape: str) -> list[dict]:
    """Ekstrak kartu-kartu kereta dari halaman hasil Traveloka."""
    data = []

    # Coba berbagai selector kartu
    kartu_selectors = [
        "[data-testid='train-search-result']",
        "[class*='TrainCard']",
        "[class*='train-card']",
        "[class*='journey-card']",
        "[class*='JourneyCard']",
    ]

    kartu_list = []
    for sel in kartu_selectors:
        kartu_list = await page.query_selector_all(sel)
        if kartu_list:
            print(f"  [INFO] Menggunakan selector kartu: {sel} ({len(kartu_list)} item)")
            break

    if not kartu_list:
        print("  [WARN] Tidak ada kartu ditemukan, mencoba fallback regex ...")
        html = await page.content()
        return _fallback_regex(html, params, waktu_scrape, sumber="traveloka")

    for idx, kartu in enumerate(kartu_list):
        try:
            async def teks(sel):
                try:
                    el = await kartu.query_selector(sel)
                    return (await el.inner_text()).strip() if el else ""
                except Exception:
                    return ""

            nama = await teks("[class*='trainName'],[class*='train-name'],[class*='TrainName'],h3,h4")
            kode = await teks("[class*='trainCode'],[class*='train-code'],[class*='TrainCode']")

            if not kode and nama:
                m = re.search(r'\(([A-Z0-9]+)\)', nama)
                kode = m.group(1) if m else ""

            jam_bgkt = await teks("[class*='departureTime'],[class*='departure-time'],[class*='depart']")
            jam_tiba = await teks("[class*='arrivalTime'],[class*='arrival-time'],[class*='arrive']")
            durasi   = await teks("[class*='duration'],[class*='Duration'],[class*='travel-time']")

            harga_els = await kartu.query_selector_all("[class*='price'],[class*='Price'],[class*='fare'],[class*='harga']")
            harga_list = []
            for el in harga_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t and "Rp" in t:
                        harga_list.append(t)
                except Exception:
                    pass

            kelas_els = await kartu.query_selector_all("[class*='class'],[class*='Class'],[class*='kelas'],[class*='seat']")
            kelas_list = []
            for el in kelas_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t and len(t) < 30:
                        kelas_list.append(t)
                except Exception:
                    pass

            kursi_els = await kartu.query_selector_all("[class*='seat'],[class*='available'],[class*='kursi'],[class*='sisa']")
            kursi_list = []
            for el in kursi_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        kursi_list.append(t)
                except Exception:
                    pass

            if not nama and not jam_bgkt:
                continue

            item = {
                "urutan":         idx + 1,
                "sumber":         "traveloka",
                "nama_kereta":    nama.split("(")[0].strip() if "(" in nama else nama,
                "kode_kereta":    kode,
                "stasiun_asal":   params["asal"],
                "stasiun_tujuan": params["tujuan"],
                "tanggal":        params["tanggal"],
                "jam_berangkat":  jam_bgkt,
                "jam_tiba":       jam_tiba,
                "durasi":         durasi,
                "kelas":          list(dict.fromkeys(kelas_list)),   # deduplicate
                "harga":          list(dict.fromkeys(harga_list)),
                "kursi_tersedia": kursi_list,
                "waktu_scrape":   waktu_scrape,
            }
            data.append(item)
            print(f"  [OK] [{idx+1}] {item['nama_kereta'] or '?'} - {item['jam_berangkat']} -> {item['jam_tiba']}")

        except Exception as e:
            print(f"  [WARN] Gagal ekstrak kartu [{idx+1}]: {e}")

    return data


# ─────────────────────────────────────────────
#  SCRAPER KAI (FALLBACK)
# ─────────────────────────────────────────────
async def scrape_kai(page, params: dict) -> list[dict]:
    """Scrape jadwal kereta dari kai.id sebagai fallback."""
    waktu_scrape = datetime.now().isoformat()

    print(f"  [INFO] Membuka kai.id ...")
    await page.goto("https://kai.id", timeout=CONFIG["timeout"])
    await jeda(1500, 3000)
    await gerak_mouse_acak(page, 2)
    await scroll_pelan(page, "down", 150)
    await jeda(1000, 2000)

    # Isi form
    print(f"  [INFO] Mengisi form pencarian KAI ...")
    await _isi_form_kai(page, params)

    # Tunggu hasil
    print(f"  [INFO] Menunggu hasil KAI ...")
    result_selectors = [
        ".train-card", ".schedule-item",
        "[data-testid*='train']", ".result-card",
    ]
    for sel in result_selectors:
        try:
            await page.wait_for_selector(sel, timeout=15_000)
            print(f"  [OK] Hasil KAI ditemukan: {sel}")
            break
        except PlaywrightTimeout:
            continue

    await jeda(500, 1000)
    await scroll_pelan(page, "down", 400)
    await jeda(500, 1000)

    # Ekstrak
    kartu_list = await page.query_selector_all(
        ".train-card,.schedule-item,[data-testid*='train'],.result-card,.kereta-item"
    )

    if not kartu_list:
        html = await page.content()
        return _fallback_regex(html, params, waktu_scrape, sumber="kai")

    data = []
    for idx, kartu in enumerate(kartu_list):
        try:
            async def teks_kai(sel):
                try:
                    el = await kartu.query_selector(sel)
                    return (await el.inner_text()).strip() if el else ""
                except Exception:
                    return ""

            nama  = await teks_kai(".train-name,.kereta-name,h3,h4,[data-testid*='name']")
            kode  = await teks_kai(".train-code,.kereta-kode,[data-testid*='code']")
            bgkt  = await teks_kai(".departure-time,.jam-berangkat,[data-testid*='departure']")
            tiba  = await teks_kai(".arrival-time,.jam-tiba,[data-testid*='arrival']")
            durasi = await teks_kai(".duration,.durasi,[data-testid*='duration']")

            harga_els = await kartu.query_selector_all(".price,.harga,[data-testid*='price'],.fare")
            harga_list = []
            for el in harga_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        harga_list.append(t)
                except Exception:
                    pass

            kelas_els  = await kartu.query_selector_all(".class,.kelas,[data-testid*='class']")
            kelas_list = []
            for el in kelas_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        kelas_list.append(t)
                except Exception:
                    pass

            kursi_els  = await kartu.query_selector_all(".seat,.kursi,.available,[data-testid*='seat']")
            kursi_list = []
            for el in kursi_els:
                try:
                    t = (await el.inner_text()).strip()
                    if t:
                        kursi_list.append(t)
                except Exception:
                    pass

            if not nama:
                continue

            data.append({
                "urutan":         idx + 1,
                "sumber":         "kai",
                "nama_kereta":    nama.split("(")[0].strip(),
                "kode_kereta":    kode,
                "stasiun_asal":   params["asal"],
                "stasiun_tujuan": params["tujuan"],
                "tanggal":        params["tanggal"],
                "jam_berangkat":  bgkt,
                "jam_tiba":       tiba,
                "durasi":         durasi,
                "kelas":          kelas_list,
                "harga":          harga_list,
                "kursi_tersedia": kursi_list,
                "waktu_scrape":   waktu_scrape,
            })
            print(f"  [OK] [{idx+1}] {nama} - {bgkt} -> {tiba}")

        except Exception as e:
            print(f"  [WARN] Gagal ekstrak KAI [{idx+1}]: {e}")

    return data


async def _isi_form_kai(page, params: dict):
    """Isi form pencarian KAI dengan perilaku human-like."""
    asal_sel = [
        "input[placeholder*='asal']","input[placeholder*='Asal']",
        "[data-testid*='origin'] input","#origin",
    ]
    for sel in asal_sel:
        try:
            el = page.locator(sel).first
            if await page.locator(sel).count() > 0:
                await ketik_seperti_manusia(el, params["asal"])
                await jeda(800, 1500)
                try:
                    dd = page.locator(f"li:has-text('{params['asal']}'),[role='option']:has-text('{params['asal']}')").first
                    await dd.click(timeout=3000)
                except PlaywrightTimeout:
                    await el.press("Enter")
                break
        except Exception:
            continue

    await jeda(500, 1000)

    tujuan_sel = [
        "input[placeholder*='tujuan']","input[placeholder*='Tujuan']",
        "[data-testid*='destination'] input","#destination",
    ]
    for sel in tujuan_sel:
        try:
            if await page.locator(sel).count() > 0:
                el = page.locator(sel).first
                await ketik_seperti_manusia(el, params["tujuan"])
                await jeda(800, 1500)
                try:
                    dd = page.locator(f"li:has-text('{params['tujuan']}'),[role='option']:has-text('{params['tujuan']}')").first
                    await dd.click(timeout=3000)
                except PlaywrightTimeout:
                    await el.press("Enter")
                break
        except Exception:
            continue

    await jeda(500, 1000)

    tgl_sel = ["input[type='date']","[data-testid*='date'] input","input[placeholder*='tanggal']"]
    for sel in tgl_sel:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).first.fill(params["tanggal"])
                break
        except Exception:
            continue

    await jeda(600, 1200)
    await gerak_mouse_acak(page, 2)

    cari_sel = ["button:has-text('Cari')","button:has-text('Search')","button[type='submit']"]
    for sel in cari_sel:
        try:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).first.click()
                break
        except Exception:
            continue


# ─────────────────────────────────────────────
#  FALLBACK REGEX PARSER
# ─────────────────────────────────────────────
def _fallback_regex(html: str, params: dict, waktu_scrape: str, sumber: str) -> list[dict]:
    """Parser regex sederhana jika selector CSS tidak cocok."""
    print(f"  [WARN] Menggunakan fallback regex parser ...")
    jam_list    = re.findall(r'\b(\d{2}:\d{2})\b', html)
    harga_list  = re.findall(r'Rp\s?[\d.,]+', html)
    nama_list   = list(dict.fromkeys(re.findall(
        r'(Argo\s?\w+|Gajayana|Bangunkarta|Taksaka|Bima|Lodaya|'
        r'Parahyangan|Sancaka|Jayabaya|Malabar|Sembrani|Gumarang|'
        r'Turangga|Brantas|Majapahit|Mataram)',
        html, re.IGNORECASE
    )))

    data = []
    for i, nama in enumerate(nama_list):
        data.append({
            "urutan":         i + 1,
            "sumber":         sumber + "_fallback",
            "nama_kereta":    nama.strip(),
            "kode_kereta":    "",
            "stasiun_asal":   params["asal"],
            "stasiun_tujuan": params["tujuan"],
            "tanggal":        params["tanggal"],
            "jam_berangkat":  jam_list[i*2]     if len(jam_list)   > i*2   else "",
            "jam_tiba":       jam_list[i*2+1]   if len(jam_list)   > i*2+1 else "",
            "durasi":         "",
            "kelas":          [],
            "harga":          [harga_list[i]]   if len(harga_list) > i     else [],
            "kursi_tersedia": [],
            "waktu_scrape":   waktu_scrape,
            "catatan":        "data dari fallback regex parser",
        })
    return data


# ─────────────────────────────────────────────
#  OUTPUT: JSON
# ─────────────────────────────────────────────
def simpan_json(data: list[dict], filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] Disimpan ke JSON  : {filepath}")


# ─────────────────────────────────────────────
#  OUTPUT: SQLITE
# ─────────────────────────────────────────────
def simpan_sql(data: list[dict], filepath: str):
    conn = sqlite3.connect(filepath)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS kereta (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sumber          TEXT,
            urutan          INTEGER,
            nama_kereta     TEXT,
            kode_kereta     TEXT,
            stasiun_asal    TEXT,
            stasiun_tujuan  TEXT,
            tanggal         TEXT,
            jam_berangkat   TEXT,
            jam_tiba        TEXT,
            durasi          TEXT,
            waktu_scrape    TEXT,
            catatan         TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS harga (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            kereta_id  INTEGER,
            kelas      TEXT,
            harga      TEXT,
            kursi      TEXT,
            FOREIGN KEY (kereta_id) REFERENCES kereta(id)
        )
    """)

    for item in data:
        cur.execute("""
            INSERT INTO kereta
                (sumber, urutan, nama_kereta, kode_kereta, stasiun_asal,
                 stasiun_tujuan, tanggal, jam_berangkat, jam_tiba,
                 durasi, waktu_scrape, catatan)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            item.get("sumber"),        item.get("urutan"),
            item.get("nama_kereta"),   item.get("kode_kereta"),
            item.get("stasiun_asal"),  item.get("stasiun_tujuan"),
            item.get("tanggal"),       item.get("jam_berangkat"),
            item.get("jam_tiba"),      item.get("durasi"),
            item.get("waktu_scrape"),  item.get("catatan", ""),
        ))
        kereta_id  = cur.lastrowid
        kelas_list = item.get("kelas", [])
        harga_list = item.get("harga", [])
        kursi_list = item.get("kursi_tersedia", [])
        jumlah     = max(len(kelas_list), len(harga_list), len(kursi_list), 1)

        for i in range(jumlah):
            cur.execute("""
                INSERT INTO harga (kereta_id, kelas, harga, kursi)
                VALUES (?,?,?,?)
            """, (
                kereta_id,
                kelas_list[i] if i < len(kelas_list) else "",
                harga_list[i] if i < len(harga_list) else "",
                kursi_list[i] if i < len(kursi_list) else "",
            ))

    conn.commit()
    conn.close()
    print(f"  [OK] Disimpan ke SQLite: {filepath}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
async def main():
    print("\n+====================================================+")
    print("|   SCRAPER TIKET KERETA - Traveloka + KAI           |")
    print("+====================================================+")

    # Mode input
    print("\nPilih mode input:")
    print("  [1] Input manual (terminal)")
    print("  [2] Hardcode testing (GMR -> BD, hari ini)")
    pilihan = input("\nPilihan (1/2): ").strip()
    params  = input_dari_user() if pilihan == "1" else input_hardcode()

    # Mode browser
    print("\nPilih mode browser:")
    print("  [1] Headed - browser kelihatan (DISARANKAN, lebih aman)")
    print("  [2] Headless - tanpa tampilan (lebih cepat, risiko diblok)")
    mode = input("\nPilihan (1/2): ").strip()
    CONFIG["headless"] = (mode == "2")

    print(f"\n  Parameter : {params['asal']} -> {params['tujuan']}  |  {params['tanggal']}")
    print(f"  Browser   : {'Headless' if CONFIG['headless'] else 'Headed (terlihat)'}")
    print(f"  Strategi  : Traveloka dulu, KAI jika gagal\n")

    hasil = []

    async with async_playwright() as p:
        browser, context = await buat_browser_stealth(p)
        page = await context.new_page()

        try:
            # ── Coba Traveloka dulu ──────────────────────────────
            print("=" * 50)
            print("  [STEP 1] Mencoba scraping dari Traveloka ...")
            print("=" * 50)
            hasil = await scrape_traveloka(page, params)

            if hasil:
                print(f"\n  [OK] Traveloka berhasil! {len(hasil)} kereta ditemukan.")
            else:
                # ── Fallback ke KAI ──────────────────────────────
                print(f"\n  [WARN] Traveloka tidak menghasilkan data.")
                print("=" * 50)
                print("  [STEP 2] Fallback ke KAI ...")
                print("=" * 50)
                await jeda(1500, 3000)
                hasil = await scrape_kai(page, params)

                if hasil:
                    print(f"\n  [OK] KAI berhasil! {len(hasil)} kereta ditemukan.")
                else:
                    print(f"\n  [FAIL] Kedua sumber tidak menghasilkan data.")
                    print("  Saran: Jalankan ulang dengan mode Headed dan inspeksi manual.")

        except Exception as e:
            print(f"\n  [ERROR] {e}")
            raise
        finally:
            input(f"\n  [Browser terbuka -- tekan ENTER untuk tutup] ")
            await browser.close()

    if not hasil:
        return

    # Simpan output
    print()
    simpan_json(hasil, CONFIG["output_json"])
    simpan_sql(hasil,  CONFIG["output_db"])

    # Preview
    print(f"\n  Total data tersimpan: {len(hasil)} kereta")
    print(f"  Sumber: {set(d['sumber'] for d in hasil)}")
    print("\n  [DONE] Selesai!")


if __name__ == "__main__":
    asyncio.run(main())