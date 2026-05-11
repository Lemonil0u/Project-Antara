"""
app.py — ANTARA Project
========================
Entry point utama Streamlit. Semua halaman ada di sini.

Cara menjalankan:
    streamlit run app.py
"""

import streamlit as st
import os
import base64
import json

from datetime import date, datetime

from engine.data_source import MultiModalDataSource
from engine.optimizer import SmartRouteOptimizer
from models import RouteCombo, SearchCriteria

st.set_page_config(page_title="ANTARA", layout="wide")

# =======================
# BACKEND INIT
# =======================

@st.cache_resource
def get_optimizer():
    data_source = MultiModalDataSource(
        headless=True,
        timeout=30,
        enabled_modes=["train", "flight"],  # FIXED: unlock flight mode (plane scraper ready)
    )
    return SmartRouteOptimizer(data_source=data_source)

optimizer = get_optimizer()

# =======================
# STATE
# =======================
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

if "selected_transport" not in st.session_state:
    st.session_state.selected_transport = ["Bus", "Train", "Flight"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "login_clicked" not in st.session_state:
    st.session_state.login_clicked = False

if "searching" not in st.session_state:
    st.session_state.searching = False

cities = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar",
    "Denpasar", "Palembang", "Balikpapan"
]

# =======================
# UTIL
# =======================
def img_to_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def safe_image(path, **kwargs):
    """Load image with graceful fallback if file missing."""
    if os.path.exists(path):
        st.image(path, **kwargs)
    else:
        st.warning(f"⚠️ Image not found: {path}")

# =======================
# BACKEND SEARCH
# =======================

def _run_search(origin: str, destination: str, date_str: str, passengers: int):

    criteria = SearchCriteria(
        origin=origin,
        destination=destination,
        departure_date=date_str,
        passengers=passengers,
    )

    with st.spinner("Mencari tiket terbaik..."):
        result = optimizer.optimize(criteria)

    st.session_state["search_criteria"] = {
        "origin": origin,
        "destination": destination,
        "date": date_str,
        "passengers": passengers,
    }

    st.session_state["optimizer_result"] = result

    return result

# =======================
# LOAD CSS
# =======================
css_path = "style.css"
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("⚠️ style.css not found — using default Streamlit styling")

# =======================
# HEADER
# =======================
left, right = st.columns([6,1.8])

with left:
    safe_image("assets/logo_antara.png", width=140)

with right:

    if st.session_state.logged_in:

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    else:

        col_login, col_signup = st.columns(2)

        with col_login:

            if st.button("Login", use_container_width=True):

                st.session_state.login_clicked = True

                st.markdown("""
                <style>
                div[data-testid="stButton"] > button:first-child {
                    background-color:#26a69a;
                    color:white;
                    border:none;
                }
                </style>
                """, unsafe_allow_html=True)

                # FIXED: check if pages/login.py exists before switch
                if os.path.exists("pages/login.py"):
                    st.switch_page("pages/login.py")
                else:
                    st.info("Login page not yet implemented")

        with col_signup:
            if st.button("Sign-up", use_container_width=True):

                st.session_state.login_clicked = True

                st.markdown("""
                <style>
                div[data-testid="stButton"] > button:first-child {
                    background-color:#26a69a;
                    color:white;
                    border:none;
                }
                </style>
                """, unsafe_allow_html=True)

                # FIXED: check if pages/signup.py exists
                if os.path.exists("pages/signup.py"):
                    st.switch_page("pages/signup.py")
                else:
                    st.info("Sign-up page not yet implemented")

st.markdown("<br>", unsafe_allow_html=True)

# =======================
# HERO
# =======================
c1, c2, c3 = st.columns([1,2,1])

with c2:
    st.markdown(
        "<h1 style='text-align:center; color:#26a69a;'>Plan Your Perfect Journey</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center; color:gray;'>Find routes, compare transport, and travel smarter</p>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# =======================
# SEARCH BOX
# =======================
c1, c2, c3 = st.columns([1,3,1])

with c2:

    safe_image("assets/multi.png", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        from_city = st.selectbox(
            "From",
            cities,
            index=0,
            key="from_app"
        )

    with col2:
        to_city = st.selectbox(
            "To",
            cities,
            index=1,
            key="to_app"
        )

    with col3:
        date_input = st.date_input("Date")

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns([2,1])

    with col_btn1:

        if st.button("🔍 Search", use_container_width=True):

            if from_city == to_city:
                st.warning("Kota asal dan tujuan tidak boleh sama")

            else:

                st.session_state.searching = True

                result = _run_search(
                    from_city,
                    to_city,
                    str(date_input),
                    1
                )

                # simpan hasil scraping
                st.session_state.search_result = result

                st.session_state.search_clicked = True

                # FIXED: check if pages/loading.py exists
                if os.path.exists("pages/loading.py"):
                    st.switch_page("pages/loading.py")
                else:
                    # If loading page doesn't exist, show results inline
                    pass

    with col_btn2:
        st.button("🚢 Transportasi", use_container_width=True)

# =======================
# POPULAR ROUTES
# =======================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("<h3>Popular Routes</h3>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)

def route_card(img, title, subtitle):
    safe_image(img, use_container_width=True)
    st.markdown(f"**{title}**")
    st.markdown(f"<small style='color:gray'>{subtitle}</small>", unsafe_allow_html=True)

with r1:
    route_card("assets/train.png", "Train", "Tugu Yogyakarta Station")

with r2:
    route_card("assets/bus.png", "Bus", "Blok M Bus Stop")

with r3:
    route_card("assets/plane.png", "Plane", "Soekarno-Hatta Airport")

# =======================
# RECOMMENDED ROUTES
# =======================
if st.session_state.search_clicked:

    st.markdown("<br><br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2,3])

    with col_left:
        st.markdown("<h3 style='color:#26a69a;'>Recommended Routes</h3>", unsafe_allow_html=True)
        st.markdown(f"**{from_city} → {to_city}**")
        st.markdown(f"{date_input}")

    # =======================
    # TRANSPORT MODE SELECTOR
    # =======================
    with col_right:

        st.markdown("**Select Transportation Modes**")

        m1, m2, m3 = st.columns(3)

        def toggle(mode):
            if mode in st.session_state.selected_transport:
                st.session_state.selected_transport.remove(mode)
            else:
                st.session_state.selected_transport.append(mode)

        def mode_button(label, mode):

            active = mode in st.session_state.selected_transport
            btn_class = "mode-active" if active else "mode-normal"

            st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)

            if st.button(label, key=f"btn_{mode}", use_container_width=True):
                toggle(mode)
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        with m1:
            mode_button("✈️ Flight", "Flight")

        with m2:
            mode_button("🚆 Train", "Train")

        with m3:
            mode_button("🚌 Bus", "Bus")

    st.markdown("<br>", unsafe_allow_html=True)

    # =======================
    # MAIN LAYOUT
    # =======================
    c_filter, c_res = st.columns([1,2.5])

    # FILTER
    with c_filter:

        st.markdown("""
        <div class="filter-card">
            <h4>Refine Your Search</h4>
        """, unsafe_allow_html=True)

        st.markdown("<b>Airlines</b>", unsafe_allow_html=True)

        st.checkbox("All Airlines", value=True)
        st.checkbox("Garuda Indonesia")
        st.checkbox("Lion Air")
        st.checkbox("Batik Air")
        st.checkbox("Citilink")

        st.markdown("<br><b>Price Range</b>", unsafe_allow_html=True)

        result = st.session_state.get("optimizer_result")

        prices = []

        if result:
            prices = [combo.total_price for combo in result.all_combos]

        max_price = int(max(prices)) if prices else 5000000

        price_range = st.slider(
            "Price Range",
            0,
            max_price,
            (0, max_price),
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Reset Filter", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # RESULTS
    with c_res:

        result = st.session_state.get("optimizer_result")

        if result and result.total_options > 0:

            combos = result.all_combos

            cheapest = min(combos, key=lambda c: c.total_price)
            fastest = min(combos, key=lambda c: c.total_duration_minutes)

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"""
                <div class="card-highlight cheap-bg">
                    <small>💸 Cheapest</small>
                    <h3>{cheapest.total_price_str}</h3>
                    <small>{cheapest.mode_label}</small>
                </div>
                """, unsafe_allow_html=True)

            with col_b:
                st.markdown(f"""
                <div class="card-highlight fast-bg">
                    <small>⚡ Fastest</small>
                    <h3>{fastest.total_duration_str}</h3>
                    <small>{fastest.mode_label}</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            transport_data = []

            for combo in combos:

                transport_type = "Train"

                if combo.modes_used:

                    mode = combo.modes_used[0]

                    if mode == "flight":
                        transport_type = "Flight"

                    elif mode == "bus":
                        transport_type = "Bus"

                    elif mode == "train":
                        transport_type = "Train"

                first_segment = combo.segments[0]
                last_segment = combo.segments[-1]

                transport_data.append({
                    "type": transport_type,
                    "name": combo.mode_label,
                    "time": f"{first_segment.departure_time.strftime('%H:%M')} - {last_segment.arrival_time.strftime('%H:%M')}",
                    "duration": combo.total_duration_str,
                    "price": combo.total_price_str,
                    "rating": str(combo.average_rating if combo.average_rating else "4.5"),
                    "price_raw": combo.total_price
                })

            filtered = [
                i for i in transport_data
                if i["type"] in st.session_state.selected_transport
                and i["price_raw"] >= price_range[0]
                and i["price_raw"] <= price_range[1]
            ]

            def color_map(t):
                return {
                    "Bus":"#22c55e",
                    "Train":"#3b82f6",
                    "Flight":"#f97316"
                }[t]
            
            
            if not filtered:
                st.info("Belum ada hasil")

            for item in filtered:

                left_card, right_btn = st.columns([5,1])

                with left_card:

                    st.markdown(
                        f"""
                        <div class="result-card">

                            <div>

                                <div style="
                                    color:{color_map(item['type'])};
                                    font-weight:bold;
                                ">
                                    {item['type']}
                                </div>

                                <div style="font-weight:600;">
                                    {item['name']}
                                </div>

                                <div style="color:gray;">
                                    {item['time']} • {item['duration']}
                                </div>

                                <div style="color:#f59e0b;">
                                    ⭐ {item['rating']}
                                </div>

                            </div>

                            <div style="
                                text-align:right;
                                font-weight:bold;
                                font-size:18px;
                            ">
                                {item['price']}
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with right_btn:

                    st.markdown("<br><br><br>", unsafe_allow_html=True)

                    if st.button(
                        "Select",
                        key=f"select_{item['name']}",
                        use_container_width=True
                    ):

                        st.session_state.selected_route = item

                        st.session_state.selected_from = from_city
                        st.session_state.selected_to = to_city
                        st.session_state.selected_date = str(date_input)

                        # FIXED: check if pages/result.py exists
                        if os.path.exists("pages/result.py"):
                            st.switch_page("pages/result.py")
                        else:
                            st.success(f"✅ Route selected: {item['name']}")

                st.markdown("<br>", unsafe_allow_html=True)
