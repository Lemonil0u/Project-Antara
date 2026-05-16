"""
pages/visualization.py — ANTARA
=================================
Halaman analitik dan perbandingan transportasi.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Visualization — ANTARA", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
            st.session_state.visual_searching = True
            st.session_state.visual_search_clicked = False
            st.rerun()

# ── LOADING ───────────────────────────────────────────────────
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

        progress = st.progress(0)
        status_text = st.empty()
        messages = [
            "Collecting transportation data...",
            "Comparing ticket prices...",
            "Analyzing duration...",
            "Generating charts...",
        ]
        for i in range(100):
            progress.progress(i + 1)
            status_text.markdown(
                f"<p style='text-align:center; color:#94a3b8; font-size:14px;'>{messages[(i // 25) % 4]}</p>",
                unsafe_allow_html=True,
            )
            time.sleep(0.018)

    st.session_state.visualization_results = [
        {"type": "Bus",    "name": "Haryanto",        "duration": 12,  "price": 250_000,   "rating": 4.5},
        {"type": "Train",  "name": "Gajah Mungkur",   "duration": 10,  "price": 350_000,   "rating": 4.7},
        {"type": "Flight", "name": "Garuda Indonesia", "duration": 2.2, "price": 1_450_000, "rating": 4.9},
        {"type": "Flight", "name": "Lion Air",         "duration": 2.5, "price": 950_000,   "rating": 4.3},
    ]
    st.session_state.visual_searching = False
    st.session_state.visual_search_clicked = True
    st.rerun()

# ── VISUALIZATION RESULT ──────────────────────────────────────
if not st.session_state.visual_search_clicked:
    st.stop()

transport_data = st.session_state.get("visualization_results", [])
df = pd.DataFrame(transport_data)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

st.markdown(f"""
<h2 style="color:#26a69a; font-family:'Plus Jakarta Sans',sans-serif; font-weight:800; margin-bottom:2px;">{from_city} → {to_city}</h2>
<p class="page-subtitle">Transportation comparison analytics · {travel_date}</p>
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
