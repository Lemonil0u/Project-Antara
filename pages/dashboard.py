import streamlit as st
import os
import base64
import time
from pages.components.sidebar import render_sidebar

st.set_page_config(page_title="ANTARA Dashboard", layout="wide")

# =======================
# STATE
# =======================
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

if "selected_transport" not in st.session_state:
    st.session_state.selected_transport = ["Bus", "Train", "Flight"]

if "searching" not in st.session_state:
    st.session_state.searching = False

cities = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar",
    "Denpasar", "Palembang", "Balikpapan"
]

# =======================
# LOAD CSS
# =======================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# =======================
# LAYOUT
# =======================
sidebar, main = st.columns([1,4])

with sidebar:
    render_sidebar()

# =======================
# MAIN
# =======================
with main:

    st.markdown("<br>", unsafe_allow_html=True)

    # HERO
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

    # SEARCH BOX
    c1, c2, c3 = st.columns([1,3,1])

    with c2:

        st.image("assets/multi.png", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            from_city = st.selectbox(
                "From",
                cities,
                index=0,
                key="from_dash"
            )

        with col2:
            to_city = st.selectbox(
                "To",
                cities,
                index=1,
                key="to_dash"
            )

        with col3:
            date = st.date_input("Date", key="date_dash")

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns([2,1])

        with col_btn1:
            if st.button("🔍 Search", use_container_width=True, key="search_dash"):
                if from_city == to_city:
                    st.warning("Kota asal dan tujuan tidak boleh sama")
                else:
                    st.session_state.searching = True
                    st.session_state.search_clicked = False
                    st.rerun()

        with col_btn2:
            st.button("🚢 Transportasi", use_container_width=True, key="transport_dash")

    # =======================
    # LOADING (INLINE)
    # =======================
    if st.session_state.searching:

        c1, c2, c3 = st.columns([1,2,1])

        with c2:

            st.markdown("<br><br>", unsafe_allow_html=True)

            st.image("assets/logo_antara.png", width=120)

            st.markdown(
                "<h2 style='text-align:center; color:#26a69a;'>Mencari Rute...</h2>",
                unsafe_allow_html=True
            )

            progress = st.progress(0)
            status = st.empty()

            messages = [
                "Searching for flights...",
                "Searching for trains...",
                "Searching for buses..."
            ]

            for i in range(100):
                progress.progress(i + 1)
                status.markdown(
                    f"<p style='text-align:center; color:gray;'>{messages[(i//30)%3]}</p>",
                    unsafe_allow_html=True
                )
                time.sleep(0.02)

            st.markdown(
                "<p style='text-align:center;'>⏱ Estimated time: 2-3 seconds</p>",
                unsafe_allow_html=True
            )

            st.markdown(
                "<p style='text-align:center; color:#26a69a;'>mengumpulkan data dari pesawat, kereta, dan bus...</p>",
                unsafe_allow_html=True
            )

        # selesai loading
        st.session_state.searching = False
        st.session_state.search_clicked = True
        st.rerun()

    # =======================
    # POPULAR ROUTES
    # =======================
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h3>Popular Routes</h3>", unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)

    def route_card(img, title, subtitle):
        st.image(img, use_container_width=True)
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
            st.markdown(f"{date}")

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

                if st.button(label, key=f"btn_dash_{mode}", use_container_width=True):
                    toggle(mode)

                st.markdown("</div>", unsafe_allow_html=True)

            with m1:
                mode_button("✈️ Flight", "Flight")

            with m2:
                mode_button("🚆 Train", "Train")

            with m3:
                mode_button("🚌 Bus", "Bus")

        st.markdown("<br>", unsafe_allow_html=True)

        # RESULTS
        st.markdown("<br>", unsafe_allow_html=True)

        # =======================
        # MAIN LAYOUT (FILTER + RESULT)
        # =======================
        c_filter, c_res = st.columns([1,2.5])

        # =======================
        # FILTER
        # =======================
        with c_filter:

            st.markdown("""
            <div class="filter-card">
                <h4>Refine Your Search</h4>
            """, unsafe_allow_html=True)

            st.markdown("<b>Airlines</b>", unsafe_allow_html=True)

            st.checkbox("All Airlines", value=True, key="dash_all_air")
            st.checkbox("Garuda Indonesia", key="dash_garuda")
            st.checkbox("Lion Air", key="dash_lion")
            st.checkbox("Batik Air", key="dash_batik")
            st.checkbox("Citilink", key="dash_citi")

            st.markdown("<br><b>Price Range</b>", unsafe_allow_html=True)
            st.slider("", 0, 5000000, 2500000, key="dash_price")

            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Reset Filter", use_container_width=True, key="dash_reset")

            st.markdown("</div>", unsafe_allow_html=True)

        # =======================
        # RESULTS
        # =======================
        with c_res:

            # CHEAPEST & FASTEST
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("""
                <div class="card-highlight cheap-bg">
                    <small>💸 Cheapest</small>
                    <h3>Rp 250.000</h3>
                    <small>Bus Haryanto</small>
                </div>
                """, unsafe_allow_html=True)

            with col_b:
                st.markdown("""
                <div class="card-highlight fast-bg">
                    <small>⚡ Fastest</small>
                    <h3>2h 15m</h3>
                    <small>Garuda Indonesia</small>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # =======================
            # DATA
            # =======================
            transport_data = [
                {
                    "type": "Bus",
                    "name": "Haryanto",
                    "time": "19:00 - 07:00",
                    "duration": "12h",
                    "price": "Rp 250.000",
                    "rating": "4.5"
                },

                {
                    "type": "Train",
                    "name": "Gajah Mungkur",
                    "time": "18:00 - 04:00",
                    "duration": "10h",
                    "price": "Rp 350.000",
                    "rating": "4.7"
                },

                {
                    "type": "Flight",
                    "name": "Garuda Indonesia",
                    "time": "08:00 - 10:15",
                    "duration": "2h 15m",
                    "price": "Rp 1.450.000",
                    "rating": "4.9"
                },

                {
                    "type": "Flight",
                    "name": "Lion Air",
                    "time": "09:00 - 11:30",
                    "duration": "2h 30m",
                    "price": "Rp 950.000",
                    "rating": "4.3"
                },
            ]

            filtered = [
                i for i in transport_data
                if i["type"] in st.session_state.selected_transport
            ]

            def color_map(t):
                return {
                    "Bus":"#22c55e",
                    "Train":"#3b82f6",
                    "Flight":"#f97316"
                }[t]

            for i, item in enumerate(filtered):

                with st.container(border=True):

                    left_card, right_card = st.columns([6,1])

                    with left_card:

                        st.markdown(
                            f"""
                            <div style="
                                color:{color_map(item['type'])};
                                font-weight:700;
                                margin-bottom:6px;
                            ">
                                {item['type']}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f"**{item['name']}**"
                        )

                        st.caption(
                            f"{item['time']} • {item['duration']}"
                        )

                        st.markdown(
                            f"<span style='color:#f59e0b;'>⭐ {item['rating']}</span>",
                            unsafe_allow_html=True
                        )

                    with right_card:

                        st.markdown(
                            f"""
                            <div style="
                                text-align:right;
                                font-size:22px;
                                font-weight:700;
                                margin-top:10px;
                            ">
                                {item['price']}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        st.markdown("<br>", unsafe_allow_html=True)

                        if st.button(
                            "Select",
                            key=f"select_{item['name']}",
                            use_container_width=True
                        ):

                            st.session_state.selected_route = item

                            st.session_state.selected_from = from_city
                            st.session_state.selected_to = to_city
                            st.session_state.selected_date = date

                            st.switch_page("pages/result.py")

                st.markdown("<br>", unsafe_allow_html=True)