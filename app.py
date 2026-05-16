"""
app.py — ANTARA Project
========================
Entry point utama Streamlit. Halaman home / landing.

Cara menjalankan:
    streamlit run app.py
"""

import streamlit as st
import os
import base64
from datetime import date

# Engine imports — sesuaikan jika path berbeda
try:
    from engine.data_source import MultiModalDataSource
    from engine.optimizer import SmartRouteOptimizer
    from models import RouteCombo, SearchCriteria
    _HAS_ENGINE = True
except ImportError:
    _HAS_ENGINE = False

st.set_page_config(page_title="ANTARA", layout="wide")

# ── CSS ──────────────────────────────────────────────────────
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── BACKEND ──────────────────────────────────────────────────
if _HAS_ENGINE:
    @st.cache_resource
    def get_optimizer():
        ds = MultiModalDataSource(headless=True, timeout=30, enabled_modes=["train", "flight"])
        return SmartRouteOptimizer(data_source=ds)
    optimizer = get_optimizer()
else:
    optimizer = None

# ── SESSION STATE ────────────────────────────────────────────
for key, default in [
    ("search_clicked",      False),
    ("selected_transport",  ["Bus", "Train", "Flight"]),
    ("logged_in",           False),
    ("login_clicked",       False),
    ("searching",           False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar", "Denpasar",
    "Palembang", "Balikpapan",
]

# ── UTIL ─────────────────────────────────────────────────────
def safe_image(path, **kwargs):
    if os.path.exists(path):
        st.image(path, **kwargs)

def _run_search(origin, destination, date_str, passengers):
    if not _HAS_ENGINE:
        return None
    criteria = SearchCriteria(
        origin=origin, destination=destination,
        departure_date=date_str, passengers=passengers,
    )
    with st.spinner("Mencari tiket terbaik..."):
        result = optimizer.optimize(criteria)
    st.session_state["search_criteria"] = {
        "origin": origin, "destination": destination,
        "date": date_str, "passengers": passengers,
    }
    st.session_state["optimizer_result"] = result
    return result

# ── HEADER ───────────────────────────────────────────────────
h_left, h_right = st.columns([6, 1.8])

with h_left:
    safe_image("assets/logo_antara.png", width=140)

with h_right:
    if st.session_state.logged_in:
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    else:
        btn_l, btn_r = st.columns(2)
        with btn_l:
            if st.button("Login", use_container_width=True):
                if os.path.exists("pages/login.py"):
                    st.switch_page("pages/login.py")
        with btn_r:
            if st.button("Sign Up", use_container_width=True, type="secondary"):
                if os.path.exists("pages/signup.py"):
                    st.switch_page("pages/signup.py")

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────
_, c_hero, _ = st.columns([1, 2, 1])

with c_hero:
    st.markdown("""
    <div style="text-align:center; padding:12px 0 20px;">
        <p class="page-eyebrow" style="text-align:center;">ANTARA · Smart Route Finder</p>
        <h1 class="hero-title">Plan Your <span>Perfect Journey</span></h1>
        <p class="hero-subtitle">Find routes, compare transport, and travel smarter</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

# ── SEARCH BOX ───────────────────────────────────────────────
_, c_mid, _ = st.columns([1, 3, 1])

with c_mid:
    safe_image("assets/multi.png", use_container_width=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1: from_city = st.selectbox("From", CITIES, index=0, key="from_app")
        with col2: to_city   = st.selectbox("To",   CITIES, index=1, key="to_app")
        with col3: date_input = st.date_input("Date")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        if st.button("🔍  Search Routes", use_container_width=True):

            if from_city == to_city:
                st.warning("Kota asal dan tujuan tidak boleh sama.")

            else:

                # simpan input user
                st.session_state.origin = from_city
                st.session_state.destination = to_city
                st.session_state.departure_date = str(date_input)
                st.session_state.passengers = 1

                # pindah ke loading page
                st.switch_page("pages/loading.py")

st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

# ── POPULAR ROUTES ────────────────────────────────────────────
st.markdown('<p class="section-title">Popular Routes</p>', unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
POPULAR = [
    ("assets/train.png", "Train",  "#3b82f6", "Tugu Yogyakarta Station"),
    ("assets/bus.png",   "Bus",    "#22c55e", "Blok M Bus Terminal"),
    ("assets/plane.png", "Plane",  "#f97316", "Soekarno-Hatta Airport"),
]

for col, (img, title, color, subtitle) in zip([r1, r2, r3], POPULAR):
    with col:
        safe_image(img, use_container_width=True)
        st.markdown(f"""
        <p class="route-tile-type" style="color:{color}; margin-top:10px;">{title}</p>
        <p class="route-tile-title">{title}</p>
        <p class="route-tile-sub">{subtitle}</p>
        """, unsafe_allow_html=True)
