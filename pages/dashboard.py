"""
pages/dashboard.py — ANTARA
=============================
Halaman utama: hero, search, popular routes, hasil pencarian.
"""

import streamlit as st
import time
import os
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="ANTARA — Dashboard", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── SESSION STATE ────────────────────────────────────────────
for key, default in [
    ("search_clicked", False),
    ("searching", False),
    ("selected_transport", ["Bus", "Train", "Flight"]),
]:
    if key not in st.session_state:
        st.session_state[key] = default

CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar", "Denpasar",
    "Palembang", "Balikpapan",
]

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="home")

# ── HERO ─────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 32px 0 20px;">
    <p class="page-eyebrow">ANTARA · Smart Route Finder</p>
    <h1 class="hero-title">Plan Your <span>Perfect Journey</span></h1>
    <p class="hero-subtitle">Find routes, compare transport, and travel smarter across Indonesia</p>
</div>
""", unsafe_allow_html=True)

# ── SEARCH BOX ───────────────────────────────────────────────
_, c_mid, _ = st.columns([1, 3.5, 1])

with c_mid:
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            from_city = st.selectbox("From", CITIES, index=0, key="from_dash")
        with col2:
            to_city = st.selectbox("To", CITIES, index=1, key="to_dash")
        with col3:
            travel_date = st.date_input("Date", key="date_dash")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        if st.button("🔍  Search Routes", use_container_width=True, key="search_dash"):
            if from_city == to_city:
                st.warning("Kota asal dan tujuan tidak boleh sama.")
            else:
                st.session_state.searching = True
                st.session_state.search_clicked = False
                st.rerun()

# ── LOADING (inline) ──────────────────────────────────────────
if st.session_state.searching:
    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

    _, c_load, _ = st.columns([1, 2, 1])
    with c_load:
        if os.path.exists("assets/logo_antara.png"):
            st.image("assets/logo_antara.png", width=100)

        st.markdown("""
        <div class="loading-wrap">
            <p class="loading-title">Mencari Rute Terbaik...</p>
            <p class="loading-sub">Sedang membandingkan semua opsi transportasi untukmu</p>
        </div>
        """, unsafe_allow_html=True)

        progress = st.progress(0)
        status_text = st.empty()
        messages = [
            "Searching flights...",
            "Searching trains...",
            "Searching buses...",
            "Comparing prices...",
        ]
        for i in range(100):
            progress.progress(i + 1)
            status_text.markdown(
                f"<p style='text-align:center; color:#94a3b8; font-size:14px;'>{messages[(i // 25) % 4]}</p>",
                unsafe_allow_html=True,
            )
            time.sleep(0.018)

    st.session_state.searching = False
    st.session_state.search_clicked = True
    st.rerun()

# ── POPULAR ROUTES ────────────────────────────────────────────
st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

st.markdown('<p class="section-title">Popular Routes</p>', unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)

POPULAR = [
    ("assets/train.png", "Train",  "#3b82f6", "Tugu Yogyakarta Station"),
    ("assets/bus.png",   "Bus",    "#22c55e", "Blok M Bus Terminal"),
    ("assets/plane.png", "Plane",  "#f97316", "Soekarno-Hatta Airport"),
]

for col, (img, title, color, subtitle) in zip([r1, r2, r3], POPULAR):
    with col:
        st.markdown(f"""
        <div class="route-tile">
        """, unsafe_allow_html=True)

        if os.path.exists(img):
            st.image(img, use_container_width=True)

        st.markdown(f"""
            <p class="route-tile-type" style="color:{color};">{title}</p>
            <p class="route-tile-title">{title}</p>
            <p class="route-tile-sub">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)

# ── RECOMMENDED ROUTES ────────────────────────────────────────
if not st.session_state.search_clicked:
    st.stop()

st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

# Header baris: judul + mode toggle
top_left, top_right = st.columns([2, 3])

with top_left:
    st.markdown(f"""
    <p class="section-title" style="margin-bottom:4px;">Recommended Routes</p>
    <p style="font-size:16px; font-weight:700; color:#1e2a52; margin:0;">{from_city} → {to_city}</p>
    <p style="font-size:13px; color:#94a3b8; margin:2px 0 0;">{travel_date}</p>
    """, unsafe_allow_html=True)

with top_right:
    st.markdown('<p style="font-size:13px; font-weight:600; color:#374151; margin-bottom:8px;">Filter Mode Transportasi</p>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)

    def _toggle(mode):
        sel = st.session_state.selected_transport
        if mode in sel:
            sel.remove(mode)
        else:
            sel.append(mode)

    def _mode_btn(label, mode, col):
        active = mode in st.session_state.selected_transport
        wrap = "mode-btn-active" if active else "mode-btn-inactive"
        with col:
            st.markdown(f'<div class="{wrap}">', unsafe_allow_html=True)
            if st.button(label, key=f"mbtn_{mode}", use_container_width=True):
                _toggle(mode)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    _mode_btn("✈️ Flight", "Flight", m1)
    _mode_btn("🚆 Train",  "Train",  m2)
    _mode_btn("🚌 Bus",    "Bus",    m3)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# Filter + Hasil
c_filter, c_results = st.columns([1, 2.6])

# ── FILTER PANEL ──────────────────────────────────────────────
with c_filter:
    st.markdown("""
    <div class="filter-panel">
        <p class="filter-panel-title">Refine Your Search</p>
        <p class="filter-section-label">Airlines</p>
    </div>
    """, unsafe_allow_html=True)

    st.checkbox("All Airlines",      value=True, key="f_all")
    st.checkbox("Garuda Indonesia",  key="f_garuda")
    st.checkbox("Lion Air",          key="f_lion")
    st.checkbox("Batik Air",         key="f_batik")
    st.checkbox("Citilink",          key="f_citilink")

    st.markdown('<p class="filter-section-label" style="margin-top:16px;">Price Range</p>', unsafe_allow_html=True)

    price_max = 5_000_000
    price_range = st.slider(
        "Price", 0, price_max, (0, price_max),
        format="Rp %d",
        label_visibility="collapsed",
        key="f_price"
    )

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.button("Reset Filter", use_container_width=True, type="secondary", key="f_reset")

# ── HASIL ─────────────────────────────────────────────────────
with c_results:

    TRANSPORT_DATA = [
        {"type": "Bus",    "name": "Haryanto",        "time": "19:00 - 07:00", "duration": "12h",    "price": "Rp 250.000",   "price_raw": 250_000,   "rating": "4.5"},
        {"type": "Train",  "name": "Gajah Mungkur",   "time": "18:00 - 04:00", "duration": "10h",    "price": "Rp 350.000",   "price_raw": 350_000,   "rating": "4.7"},
        {"type": "Flight", "name": "Garuda Indonesia", "time": "08:00 - 10:15", "duration": "2h 15m", "price": "Rp 1.450.000", "price_raw": 1_450_000, "rating": "4.9"},
        {"type": "Flight", "name": "Lion Air",         "time": "09:00 - 11:30", "duration": "2h 30m", "price": "Rp 950.000",   "price_raw": 950_000,   "rating": "4.3"},
    ]

    filtered = [
        i for i in TRANSPORT_DATA
        if i["type"] in st.session_state.selected_transport
        and price_range[0] <= i["price_raw"] <= price_range[1]
    ]

    if filtered:
        cheapest = min(filtered, key=lambda x: x["price_raw"])
        fastest  = min(filtered, key=lambda x: x["duration"])

        hc1, hc2 = st.columns(2)
        with hc1:
            st.markdown(f"""
            <div class="highlight-card cheap">
                <p class="highlight-label">💸 Cheapest</p>
                <p class="highlight-value">{cheapest['price']}</p>
                <p class="highlight-desc">{cheapest['name']}</p>
            </div>
            """, unsafe_allow_html=True)
        with hc2:
            st.markdown(f"""
            <div class="highlight-card fast">
                <p class="highlight-label">⚡ Fastest</p>
                <p class="highlight-value">{fastest['duration']}</p>
                <p class="highlight-desc">{fastest['name']}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    COLOR_MAP = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}

    if not filtered:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <p class="empty-state-title">Tidak ada hasil</p>
            <p class="empty-state-sub">Coba ubah filter atau mode transportasi</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for item in filtered:
            color = COLOR_MAP.get(item["type"], "#26a69a")

            card_col, btn_col = st.columns([5, 1])

            with card_col:
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <p class="result-card-badge" style="color:{color};">{item['type']}</p>
                        <p class="result-card-name">{item['name']}</p>
                        <p class="result-card-meta">{item['time']} &nbsp;·&nbsp; {item['duration']}</p>
                        <p class="result-card-rating">⭐ {item['rating']}</p>
                    </div>
                    <div class="result-card-price">{item['price']}</div>
                </div>
                """, unsafe_allow_html=True)

            with btn_col:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button("Select", key=f"sel_{item['name']}", use_container_width=True):
                    st.session_state.selected_route  = item
                    st.session_state.selected_from   = from_city
                    st.session_state.selected_to     = to_city
                    st.session_state.selected_date   = str(travel_date)
                    if os.path.exists("pages/result.py"):
                        st.switch_page("pages/result.py")
