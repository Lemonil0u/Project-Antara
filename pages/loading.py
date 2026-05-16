import streamlit as st
import time
import os

# ENGINE
from engine.data_source import MultiModalDataSource
from engine.optimizer import SmartRouteOptimizer
from models import SearchCriteria

st.set_page_config(
    page_title="Searching... — ANTARA",
    layout="centered"
)

# CSS
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# CACHE OPTIMIZER
@st.cache_resource
def get_optimizer():
    ds = MultiModalDataSource(
        headless=True,
        timeout=30,
        enabled_modes=["train", "flight"]
    )
    return SmartRouteOptimizer(data_source=ds)

optimizer = get_optimizer()

# UI
st.markdown(
    '<div style="height:80px"></div>',
    unsafe_allow_html=True
)

_, c, _ = st.columns([1, 2, 1])

with c:

    if os.path.exists("assets/logo_antara.png"):
        st.image("assets/logo_antara.png", width=100)

    st.markdown(
        """
        <h2 style='
            text-align:center;
            color:#14b8a6;
            font-weight:700;
            margin-bottom:0;
        '>
            Mencari Rute Terbaik...
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style='
            text-align:center;
            color:#64748b;
            font-size:15px;
            margin-top:8px;
        '>
            Sedang membandingkan semua opsi transportasi untukmu
        </p>
        """,
        unsafe_allow_html=True
    )
    progress = st.progress(0)
    status = st.empty()

    messages = [
        "Searching flights...",
        "Searching trains...",
        "Searching buses...",
        "Comparing prices..."
    ]

    # pastikan data ada
    if "origin" not in st.session_state:
        st.switch_page("app.py")

    origin = st.session_state.get("origin")
    destination = st.session_state.get("destination")
    departure_date = st.session_state.get("departure_date")
    passengers = st.session_state.get("passengers", 1)

    import threading

    result_holder = {"result": None}

    # function scraper
    def run_search():
        criteria = SearchCriteria(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
        )

        result_holder["result"] = optimizer.optimize(criteria)

    # jalankan scraper di thread
    thread = threading.Thread(target=run_search)
    thread.start()

    messages = [
        "Searching flights",
        "Searching trains",
        "Searching buses",
        "Comparing ticket prices",
        "Finding best route",
    ]

    progress_value = 0
    message_index = 0
    dot_count = 1

    # LOOP SELAMA SCRAPER MASIH JALAN
    progress_value = 0.0

    while thread.is_alive():

        # progress natural super smooth
        increment = max(0.08, (100 - progress_value) / 180)

        progress_value += increment

        # maksimal sebelum selesai scraper
        if progress_value > 96:
            progress_value = 96

        progress.progress(int(progress_value))

        dots = "." * dot_count

        status.markdown(
            f"""
            <p style='
                text-align:center;
                color:#94a3b8;
                font-size:14px;
                margin-top:10px;
            '>
                {messages[message_index]}{dots}
            </p>
            """,
            unsafe_allow_html=True
        )

        dot_count += 1

        if dot_count > 3:
            dot_count = 1
            message_index = (message_index + 1) % len(messages)

        time.sleep(0.12)

    thread.join()

    # selesai
    progress.progress(100)

    status.markdown(
        """
        <p style='
            text-align:center;
            color:#10b981;
            font-size:14px;
            margin-top:10px;
        '>
            Route ditemukan!
        </p>
        """,
        unsafe_allow_html=True
    )

    result = result_holder["result"]

    # selesai
    progress.progress(100)

    status.markdown(
        """
        <p style='
            text-align:center;
            color:#10b981;
            font-size:14px;
        '>
            Route ditemukan!
        </p>
        """,
        unsafe_allow_html=True
    )

    time.sleep(1)

    # pindah ke app.py lagi
    st.switch_page("app.py")