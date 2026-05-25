"""
pages/visualization.py — ANTARA
=================================
Halaman analitik dan perbandingan transportasi.
"""

import threading
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from database import DatabaseManager
from engine.data_source import MultiModalDataSource
from engine.optimizer import SmartRouteOptimizer
from models import SearchCriteria
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme
from config import SCRAPER_TIMEOUT, SCRAPER_HEADLESS, CACHE_TTL_MINUTES

st.set_page_config(page_title="Visualization — ANTARA", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── OPTIMIZER dengan price cache ─────────────────────────────
@st.cache_resource
def get_db():
    return DatabaseManager()

@st.cache_resource
def get_optimizer():
    db = get_db()
    ds = MultiModalDataSource(
        headless=SCRAPER_HEADLESS, timeout=SCRAPER_TIMEOUT,
        enabled_modes=["train", "flight"],
        db=db, cache_ttl_minutes=CACHE_TTL_MINUTES,
    )
    return SmartRouteOptimizer(data_source=ds)

db        = get_db()
optimizer = get_optimizer()

apply_theme()

# ── STATE ────────────────────────────────────────────────────
for key, default in [
    ("visual_search_clicked", False),
    ("visual_searching",      False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

CITIES = [
    "Jakarta", "Bandung", "Surabaya", "Yogyakarta", "Semarang",
    "Denpasar", "Medan", "Makassar", "Palembang", "Balikpapan",
]

COLOR_MAP = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="visualization")

# ── PAGE HEADER ──────────────────────────────────────────────
st.markdown("""
<p class="page-eyebrow">ANTARA · Analytics</p>
<h1 class="page-title">Transportation Visualization</h1>
<p class="page-subtitle">Compare prices, duration, and ratings across transport modes</p>
""", unsafe_allow_html=True)

# ── SEARCH BOX ───────────────────────────────────────────────
with st.container(border=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        from_city = st.selectbox("From", CITIES, index=0, key="vis_from")
    with col2:
        to_city = st.selectbox("To", CITIES, index=2, key="vis_to")
    with col3:
        travel_date = st.date_input("Date", key="vis_date")

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    if st.button("🔍  Generate Visualization", use_container_width=True, key="vis_search"):
        if from_city == to_city:
            st.warning("Kota asal dan tujuan tidak boleh sama.")
        else:
            # Cek apakah data pencarian terakhir cocok dengan pilihan sekarang
            last_criteria = st.session_state.get("search_criteria", {})
            existing_result = st.session_state.get("optimizer_result")

            same_route = (
                existing_result is not None
                and last_criteria.get("origin", "").lower() == from_city.lower()
                and last_criteria.get("destination", "").lower() == to_city.lower()
                and last_criteria.get("date", "") == str(travel_date)
            )

            if same_route:
                # Pakai data yang sudah ada — tidak perlu scrape ulang
                result = existing_result
                vis_data = []
                for combo in result.all_combos:
                    mode = combo.modes_used[0] if combo.modes_used else "train"
                    t_type = {"flight": "Flight", "train": "Train", "bus": "Bus"}.get(mode, "Train")
                    first_seg = combo.segments[0]
                    vis_data.append({
                        "type":     t_type,
                        "name":     first_seg.provider,
                        "duration": round(combo.total_duration_minutes / 60, 1),
                        "price":    combo.total_price,
                        "rating":   combo.average_rating if combo.average_rating else 4.0,
                    })
                st.session_state.visualization_results = vis_data
                st.session_state.vis_from_city    = from_city
                st.session_state.vis_to_city      = to_city
                st.session_state.vis_travel_date  = str(travel_date)
                st.session_state.visual_searching = False
                st.session_state.visual_search_clicked = True
                st.rerun()
            else:
                # Rute berbeda — perlu scrape baru
                st.session_state.visual_searching = True
                st.session_state.visual_search_clicked = False
                st.rerun()

# ── LOADING + REAL SCRAPING ──────────────────────────────────
if st.session_state.visual_searching:
    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

    _, c_load, _ = st.columns([1, 2, 1])
    with c_load:
        if os.path.exists("assets/logo_antara.png"):
            st.image("assets/logo_antara.png", width=100)

        st.markdown("""
        <div class="loading-wrap">
            <p class="loading-title">Generating Visualization...</p>
            <p class="loading-sub">Mengumpulkan dan menganalisis data transportasi</p>
        </div>
        """, unsafe_allow_html=True)

        progress    = st.progress(0)
        status_text = st.empty()
        messages    = [
            "Collecting transportation data...",
            "Comparing ticket prices...",
            "Analyzing duration...",
            "Generating charts...",
        ]

        result_holder = {"result": None}

        def _run_vis_search():
            criteria = SearchCriteria(
                origin=from_city,
                destination=to_city,
                departure_date=str(travel_date),
                passengers=1,
            )
            result_holder["result"] = optimizer.optimize(criteria)

        thread = threading.Thread(target=_run_vis_search)
        thread.start()

        progress_value = 0.0
        message_index  = 0
        dot_count      = 1

        while thread.is_alive():
            increment = max(0.08, (100 - progress_value) / 180)
            progress_value = min(progress_value + increment, 96)
            progress.progress(int(progress_value))
            dots = "." * dot_count
            status_text.markdown(
                f"<p style='text-align:center; color:#94a3b8; font-size:14px;'>{messages[message_index]}{dots}</p>",
                unsafe_allow_html=True,
            )
            dot_count += 1
            if dot_count > 3:
                dot_count = 1
                message_index = (message_index + 1) % len(messages)
            time.sleep(0.12)

        thread.join()
        progress.progress(100)

        result = result_holder["result"]

        # Konversi OptimizerResult → format yang dipakai chart
        vis_data = []
        if result and result.total_options > 0:
            for combo in result.all_combos:
                mode = combo.modes_used[0] if combo.modes_used else "train"
                t_type = {"flight": "Flight", "train": "Train", "bus": "Bus"}.get(mode, "Train")
                first_seg = combo.segments[0]
                vis_data.append({
                    "type":     t_type,
                    "name":     first_seg.provider,
                    "duration": round(combo.total_duration_minutes / 60, 1),
                    "price":    combo.total_price,
                    "rating":   combo.average_rating if combo.average_rating else 4.0,
                })

        # Simpan ke session_state
        st.session_state.visualization_results      = vis_data
        st.session_state.vis_from_city              = from_city
        st.session_state.vis_to_city                = to_city
        st.session_state.vis_travel_date            = str(travel_date)
        st.session_state.visual_searching  = False
        st.session_state.visual_search_clicked = True
        st.rerun()

# ── VISUALIZATION RESULT ──────────────────────────────────────
if not st.session_state.visual_search_clicked:
    st.stop()

transport_data = st.session_state.get("visualization_results", [])
df = pd.DataFrame(transport_data)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# Ambil kota dari session_state (bukan dari widget, karena page sudah rerun)
_from_city   = st.session_state.get("vis_from_city", from_city)
_to_city     = st.session_state.get("vis_to_city", to_city)
_travel_date = st.session_state.get("vis_travel_date", str(travel_date))

if not transport_data:
    st.warning("Tidak ada data ditemukan untuk rute ini. Coba rute lain.")
    st.stop()

st.markdown(f"""
<h2 style="color:#26a69a; font-family:'Plus Jakarta Sans',sans-serif; font-weight:800; margin-bottom:2px;">{_from_city} → {_to_city}</h2>
<p class="page-subtitle">Transportation comparison analytics · {_travel_date}</p>
""", unsafe_allow_html=True)

# ── SUMMARY CARDS ─────────────────────────────────────────────
cheapest = df.loc[df["price"].idxmin()]
fastest  = df.loc[df["duration"].idxmin()]
highest  = df.loc[df["rating"].idxmax()]

sc1, sc2, sc3 = st.columns(3)

def _summary_card(col, icon, label, name, value, suffix=""):
    with col:
        with st.container(border=True):
            st.markdown(f"""
            <p style="font-size:11px; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; color:#6b7280; margin-bottom:8px;">{icon} {label}</p>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:14px; font-weight:600; color:#374151; margin-bottom:2px;">{name}</p>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:28px; font-weight:800; color:#26a69a; margin:0;">{value}{suffix}</p>
            """, unsafe_allow_html=True)

_summary_card(sc1, "💸", "Cheapest",    cheapest["name"], f"Rp {int(cheapest['price']):,}".replace(",", "."))
_summary_card(sc2, "⚡", "Fastest",     fastest["name"],  f"{fastest['duration']}h")
_summary_card(sc3, "⭐", "Best Rating", highest["name"],  highest["rating"])

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── CHARTS ────────────────────────────────────────────────────
chart1, chart2 = st.columns(2)

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_family="DM Sans",
    legend_title_text="Mode",
    xaxis_title="",
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

with chart1:
    with st.container(border=True):
        st.markdown('<p style="font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:8px;">Price Comparison</p>', unsafe_allow_html=True)
        fig = px.bar(
            df, x="name", y="price",
            color="type",
            color_discrete_map=COLOR_MAP,
            text_auto=True,
            height=340,
        )
        fig.update_layout(**CHART_LAYOUT, yaxis_title="Price (IDR)")
        fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

with chart2:
    with st.container(border=True):
        st.markdown('<p style="font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:8px;">Duration Comparison</p>', unsafe_allow_html=True)
        fig2 = px.bar(
            df, x="name", y="duration",
            color="type",
            color_discrete_map=COLOR_MAP,
            text_auto=True,
            height=340,
        )
        fig2.update_layout(**CHART_LAYOUT, yaxis_title="Duration (hours)")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

# Rating chart — full width
with st.container(border=True):
    st.markdown('<p style="font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:8px;">Rating Comparison</p>', unsafe_allow_html=True)
    fig3 = px.bar(
        df, x="name", y="rating",
        color="type",
        color_discrete_map=COLOR_MAP,
        text_auto=True,
        height=280,
    )
    fig3.update_layout(**CHART_LAYOUT, yaxis_title="Rating", yaxis_range=[0, 5.5])
    st.plotly_chart(fig3, use_container_width=True)

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

# ── TABLE ─────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown('<p style="font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:12px;">Route Comparison Table</p>', unsafe_allow_html=True)

    show_df = df.copy()
    show_df["price"] = show_df["price"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))
    show_df["duration"] = show_df["duration"].apply(lambda x: f"{x}h")
    show_df.columns = ["Mode", "Provider", "Duration", "Price", "Rating"]

    st.dataframe(show_df, use_container_width=True, hide_index=True)