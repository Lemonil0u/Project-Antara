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
from config import SCRAPER_TIMEOUT, SCRAPER_HEADLESS, SCRAPER_ENABLED_MODES, CACHE_TTL_MINUTES
from models import SearchCriteria

st.set_page_config(page_title="Searching... — ANTARA", layout="centered")

if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Optimizer & DB (cached resource) ─────────────────────────────────────────
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

# ── Guard: harus ada search params ───────────────────────────────────────────
if "origin" not in st.session_state:
    st.switch_page("app.py")

origin         = st.session_state["origin"]
destination    = st.session_state["destination"]
departure_date = st.session_state["departure_date"]
passengers     = st.session_state.get("passengers", 1)

criteria = SearchCriteria(
    origin=origin,
    destination=destination,
    departure_date=departure_date,
    passengers=passengers,
)

# ── Inisialisasi streaming state (hanya sekali per search) ───────────────────
MODES = [m for m in ["train", "flight", "bus"] if m in SCRAPER_ENABLED_MODES]

if not st.session_state.get("stream_started"):
    st.session_state["stream_segments"] = {m: [] for m in MODES}
    st.session_state["stream_done"]     = {m: False for m in MODES}
    st.session_state["stream_error"]    = {m: None for m in MODES}
    st.session_state["stream_started"]  = True

    # ── Spawn satu thread per moda ────────────────────────────────────────
    ds: MultiModalDataSource = optimizer.data_source

    def _scrape_mode(mode: str):
        """Worker untuk satu moda — hasil langsung masuk session_state."""
        try:
            segs = ds.get_segments(
                origin=origin,
                destination=destination,
                date_str=departure_date,
                passengers=passengers,
                modes=[mode],
            )
            st.session_state["stream_segments"][mode] = segs or []
        except Exception as e:
            st.session_state["stream_error"][mode] = str(e)
            st.session_state["stream_segments"][mode] = []
        finally:
            st.session_state["stream_done"][mode] = True

    for mode in MODES:
        t = threading.Thread(target=_scrape_mode, args=(mode,), daemon=True)
        t.start()

# ── Helper: kumpulkan semua segmen yang sudah ada ────────────────────────────
def _collected_segments():
    all_segs = []
    for segs in st.session_state["stream_segments"].values():
        all_segs.extend(segs)
    return all_segs

def _all_done():
    return all(st.session_state["stream_done"].values())

def _done_modes():
    return [m for m, done in st.session_state["stream_done"].items() if done]

def _pending_modes():
    return [m for m, done in st.session_state["stream_done"].items() if not done]

# ── UI Render ─────────────────────────────────────────────────────────────────
st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)

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
        f"""
        <p style='text-align:center; color:#64748b; font-size:15px; margin-top:8px;'>
            {origin} → {destination} · {departure_date}
        </p>
        """,
        unsafe_allow_html=True,
    )

# ── Progress bar berdasarkan moda yang selesai ───────────────────────────────
done_count    = len(_done_modes())
total_count   = len(MODES)
progress_pct  = int((done_count / total_count) * 85) if total_count > 0 else 0
if _all_done():
    progress_pct = 100

progress_bar  = st.progress(progress_pct)

# ── Status pills: per-moda ────────────────────────────────────────────────────
MODE_EMOJI = {"train": "🚂", "flight": "✈️", "bus": "🚌"}
MODE_LABEL = {"train": "Kereta", "flight": "Pesawat", "bus": "Bus"}

status_cols = st.columns(len(MODES))
for i, mode in enumerate(MODES):
    done  = st.session_state["stream_done"][mode]
    err   = st.session_state["stream_error"].get(mode)
    segs  = st.session_state["stream_segments"][mode]
    emoji = MODE_EMOJI.get(mode, "🔍")
    label = MODE_LABEL.get(mode, mode.title())

    if done and err:
        pill = f"⚠️ {label} — error"
        color = "#f59e0b"
    elif done:
        pill = f"✅ {label} — {len(segs)} opsi"
        color = "#10b981"
    else:
        pill = f"⏳ {label}..."
        color = "#94a3b8"

    with status_cols[i]:
        st.markdown(
            f"<p style='text-align:center; color:{color}; font-size:13px; "
            f"font-weight:600; margin:4px 0;'>{pill}</p>",
            unsafe_allow_html=True,
        )

# ── Partial results — render kartu sementara ─────────────────────────────────
partial_segs = _collected_segments()

if partial_segs:
    n_combos    = len(partial_segs)
    pending_str = (
        f" · masih memuat {', '.join(MODE_LABEL.get(m, m) for m in _pending_modes())}"
        if _pending_modes() else ""
    )
    st.markdown(
        f"""
        <p style='color:#64748b; font-size:13px; margin: 16px 0 8px;'>
            {n_combos} opsi ditemukan sejauh ini{pending_str}
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Build partial result untuk preview (max 5 kartu)
    try:
        partial_result = optimizer.build_combos_from_segments(partial_segs, criteria)
        preview_combos = partial_result.all_combos[:5]

        for combo in preview_combos:
            mode_icon = "✈️" if combo.mode_label == "flight" else (
                "🚂" if combo.mode_label == "train" else "🚌"
            )
            is_best = combo.is_cheapest or combo.is_fastest
            border  = "border-left: 4px solid #14b8a6;" if is_best else "border-left: 4px solid #334155;"
            badge   = ""
            if combo.is_cheapest:
                badge += "<span style='background:#14b8a6;color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;margin-right:4px;'>Termurah</span>"
            if combo.is_fastest:
                badge += "<span style='background:#6366f1;color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;'>Tercepat</span>"

            st.markdown(
                f"""
                <div style='background:#1e293b; border-radius:10px; padding:12px 16px;
                            margin-bottom:8px; {border} opacity:0.85;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span style='color:#e2e8f0; font-weight:600; font-size:15px;'>
                            {mode_icon} {combo.route_label}
                        </span>
                        <span style='color:#14b8a6; font-weight:700; font-size:16px;'>
                            {combo.total_price_str}
                        </span>
                    </div>
                    <div style='color:#94a3b8; font-size:13px; margin-top:4px;'>
                        ⏱ {combo.total_duration_str} &nbsp;·&nbsp; {combo.mode_label.title()}
                        {"&nbsp;·&nbsp;" + badge if badge else ""}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception:
        pass  # Partial combos gagal build — tidak masalah, tunggu selesai semua

elif not _all_done():
    st.markdown(
        "<p style='color:#64748b; font-size:13px; margin-top:16px;'>Sedang mencari...</p>",
        unsafe_allow_html=True,
    )

# ── Selesai: simpan ke DB & pindah ke dashboard ───────────────────────────────
if _all_done():
    progress_bar.progress(100)

    all_segs = _collected_segments()
    final_result = optimizer.build_combos_from_segments(all_segs, criteria)

    st.session_state["optimizer_result"] = final_result
    st.session_state["search_criteria"]  = {
        "origin":      origin,
        "destination": destination,
        "date":        departure_date,
        "passengers":  passengers,
    }
    st.session_state["search_clicked"]  = True

    # Reset streaming state untuk search berikutnya
    st.session_state.pop("stream_started", None)
    st.session_state.pop("stream_segments", None)
    st.session_state.pop("stream_done", None)
    st.session_state.pop("stream_error", None)

    # Simpan ke DB (best-effort)
    try:
        cheapest_summary = {}
        if final_result.cheapest:
            cheapest_summary = {
                "route":    final_result.cheapest.route_label,
                "price":    final_result.cheapest.total_price_str,
                "duration": final_result.cheapest.total_duration_str,
                "mode":     final_result.cheapest.mode_label,
            }
        db.save_search_result(
            origin=origin,
            destination=destination,
            date=departure_date,
            passengers=passengers,
            best_route_combo=cheapest_summary,
            total_options=final_result.total_options,
        )
    except Exception as e:
        print(f"[WARN] Gagal simpan ke DB: {e}")

    time.sleep(0.5)
    st.switch_page("pages/dashboard.py")

else:
    # Polling: rerun setiap 0.5 detik selama masih ada moda yang belum selesai
    time.sleep(0.5)
    st.rerun()