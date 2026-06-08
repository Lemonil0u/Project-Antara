"""
pages/loading.py — ANTARA
==========================
Halaman loading saat scraping berjalan di background thread.

MERGE: UI dari temanmu (progress bar, animated messages)
       + database/cache dari fixku (DatabaseManager, save_search_result)
"""

import os
import threading
import time

import streamlit as st

from database import DatabaseManager
from engine.data_source import MultiModalDataSource
from engine.optimizer import SmartRouteOptimizer

from config import SCRAPER_TIMEOUT, SCRAPER_HEADLESS, SCRAPER_ENABLED_MODES, CACHE_TTL_MINUTES, QUICK_SEARCH_MAX_PER_MODE

from models import SearchCriteria

st.set_page_config(page_title="Searching... — ANTARA", layout="centered")

if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── OPTIMIZER dengan database + price cache ───────────────────────────────────
# MERGE: tambah db= agar cache aktif, hemat scraping ulang rute yang sama
@st.cache_resource
def get_db():
    return DatabaseManager()


@st.cache_resource
def get_optimizer():
    db = get_db()
    ds = MultiModalDataSource(
        headless=SCRAPER_HEADLESS,
        timeout=SCRAPER_TIMEOUT,
        enabled_modes=SCRAPER_ENABLED_MODES,
        db=db,
        cache_ttl_minutes=CACHE_TTL_MINUTES,
    )
    return SmartRouteOptimizer(data_source=ds)


db        = get_db()
optimizer = get_optimizer()

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown('<div style="height:80px"></div>', unsafe_allow_html=True)

_, c, _ = st.columns([1, 2, 1])

with c:
    if os.path.exists("assets/logo_antara.png"):
        st.image("assets/logo_antara.png", width=100)

    st.markdown(
        """
        <h2 style='text-align:center; color:#14b8a6; font-weight:700; margin-bottom:0;'>
            Mencari Rute Terbaik...
        </h2>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <p style='text-align:center; color:#64748b; font-size:15px; margin-top:8px;'>
            Sedang membandingkan semua opsi transportasi untukmu
        </p>
        """,
        unsafe_allow_html=True,
    )

    progress = st.progress(0)
    status   = st.empty()

    # Pastikan data pencarian ada, kalau tidak balik ke landing
    if "origin" not in st.session_state:
        st.switch_page("app.py")

    origin         = st.session_state.get("origin")
    destination    = st.session_state.get("destination")
    departure_date = st.session_state.get("departure_date")
    passengers     = st.session_state.get("passengers", 1)

    result_holder = {"result": None}

    def run_search():
        # full_search=True berarti user klik Refresh → scrape lebih banyak (no limit)
        _is_full = st.session_state.get("full_search", False)
        _max_per = None if _is_full else QUICK_SEARCH_MAX_PER_MODE
        criteria = SearchCriteria(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
            max_results_per_mode=_max_per,
        )
        result_holder["result"] = optimizer.optimize(criteria)

    # Jalankan scraper di thread terpisah agar progress bar bisa update
    thread = threading.Thread(target=run_search)
    thread.start()

    messages = [
        "Searching flights",
        "Searching trains",
        "Searching buses",
        "Comparing ticket prices",
        "Finding best route",
    ]

    progress_value = 0.0
    message_index  = 0
    dot_count      = 1

    while thread.is_alive():
        # Progress naik smooth, max 96 sebelum scraper selesai
        increment = max(0.08, (100 - progress_value) / 180)
        progress_value = min(progress_value + increment, 96)
        progress.progress(int(progress_value))

        dots = "." * dot_count
        status.markdown(
            f"""
            <p style='text-align:center; color:#94a3b8; font-size:14px; margin-top:10px;'>
                {messages[message_index]}{dots}
            </p>
            """,
            unsafe_allow_html=True,
        )
        dot_count += 1
        if dot_count > 3:
            dot_count = 1
            message_index = (message_index + 1) % len(messages)

        time.sleep(0.12)

    thread.join()

    progress.progress(100)
    status.markdown(
        """
        <p style='text-align:center; color:#10b981; font-size:14px; margin-top:10px;'>
            Rute ditemukan!
        </p>
        """,
        unsafe_allow_html=True,
    )

    result = result_holder["result"]

    # ── Simpan hasil ke database (best-effort) ────────────────────────────────
    # MERGE: save search history ke SQLite, jangan crash UI kalau DB error
    if result is not None:
        st.session_state["optimizer_result"] = result
        # FIX: simpan juga search_criteria agar visualization bisa cek "same route"
        st.session_state["search_criteria"] = {
            "origin":      origin,
            "destination": destination,
            "date":        departure_date,
            "passengers":  passengers,
        }
        # FIX: aktifkan flag search_clicked supaya dashboard menampilkan hasil
        # (sebelumnya dashboard berhenti di "if not search_clicked: st.stop()")
        st.session_state["search_clicked"] = True

        try:
            cheapest_summary = {}
            if result.cheapest:
                cheapest_summary = {
                    "route":    result.cheapest.route_label,
                    "price":    result.cheapest.total_price_str,
                    "duration": result.cheapest.total_duration_str,
                    "mode":     result.cheapest.mode_label,
                }
            db.save_search_result(
                origin=origin,
                destination=destination,
                date=departure_date,
                passengers=passengers,
                best_route_combo=cheapest_summary,
                total_options=result.total_options,
            )
        except Exception as e:
            # DB error tidak boleh ganggu UI
            print(f"[WARN] Gagal simpan ke DB: {e}")

    time.sleep(1)

    # Setelah scraping selesai, pergi ke dashboard (bukan app.py)
    # supaya hasil pencarian langsung tampil
    st.switch_page("pages/dashboard.py")