"""
pages/favorite_routes.py — ANTARA
====================================
Daftar rute yang disimpan user.
"""

import streamlit as st
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DatabaseManager
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Saved Routes — ANTARA", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── DATA ─────────────────────────────────────────────────────
DEFAULT_ROUTES = [
    {
        "type": "Bus",    "name": "Haryanto",        "icon": "🚌",
        "from": "Jakarta", "to": "Denpasar",
        "date": "20 May 2024", "duration": "12h",    "rating": "4.5",
        "price": "Rp 250.000",   "price_raw": 250_000,
        "color": "#22c55e", "bg": "#eef9f0",
        "time": "19:00 - 07:00", "distance": "1,150 km",
        "amenities": ["AC", "Wi-Fi", "Charging Port"],
    },
    {
        "type": "Train",  "name": "Gajah Mungkur",   "icon": "🚆",
        "from": "Jakarta", "to": "Bandung",
        "date": "18 May 2024", "duration": "3h 10m", "rating": "4.7",
        "price": "Rp 350.000",   "price_raw": 350_000,
        "color": "#3b82f6", "bg": "#eef4ff",
        "time": "08:00 - 11:10", "distance": "180 km",
        "amenities": ["AC", "Meal", "Toilet"],
    },
    {
        "type": "Flight", "name": "Garuda Indonesia", "icon": "✈️",
        "from": "Jakarta", "to": "Bali (DPS)",
        "date": "15 May 2024", "duration": "2h 15m", "rating": "4.9",
        "price": "Rp 1.450.000", "price_raw": 1_450_000,
        "color": "#f97316", "bg": "#fff6eb",
        "time": "09:00 - 11:15", "distance": "980 km",
        "amenities": ["Meal", "Cabin Bag", "Entertainment"],
    },
    {
        "type": "Bus",    "name": "Sinar Jaya",       "icon": "🚌",
        "from": "Yogyakarta", "to": "Surabaya",
        "date": "12 May 2024", "duration": "5h 30m", "rating": "4.3",
        "price": "Rp 180.000",   "price_raw": 180_000,
        "color": "#22c55e", "bg": "#eef9f0",
        "time": "10:00 - 15:30", "distance": "320 km",
        "amenities": ["AC", "Seat", "Snacks"],
    },
    {
        "type": "Train",  "name": "Argo Parahyangan", "icon": "🚆",
        "from": "Bandung", "to": "Jakarta",
        "date": "10 May 2024", "duration": "3h",     "rating": "4.6",
        "price": "Rp 200.000",   "price_raw": 200_000,
        "color": "#3b82f6", "bg": "#eef4ff",
        "time": "13:00 - 16:00", "distance": "180 km",
        "amenities": ["AC", "Toilet", "Meal"],
    },
]

user_id = st.session_state.get("user", {}).get("id")
db = DatabaseManager()
db_rows = db.get_saved_routes(user_id=user_id)

# Restore display dict dari combo_json yang disimpan result.py
import json as _json
saved_routes = []
for row in db_rows:
    try:
        display = _json.loads(row["combo_json"])
        display["_db_id"] = row["id"]  # buat tombol delete nanti
        saved_routes.append(display)
    except Exception:
        continue

# Fallback ke DEFAULT_ROUTES cuma kalau belum ada user_id (mode demo)
if not user_id and not saved_routes:
    saved_routes = DEFAULT_ROUTES

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="favorites")

# ── PAGE HEADER ──────────────────────────────────────────────
st.markdown('<p class="page-eyebrow">ANTARA · Your Library</p>', unsafe_allow_html=True)

header_l, header_r = st.columns([2, 2])

with header_l:
    st.markdown('<h1 class="page-title">Saved Routes</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Your saved routes for quick access and future planning.</p>', unsafe_allow_html=True)

with header_r:
    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns([2.5, 1])
    with sc1:
        search = st.text_input("", placeholder="🔍 Search saved routes...", label_visibility="collapsed")
    with sc2:
        sort_by = st.selectbox("", ["Newest", "Oldest", "Cheapest"], label_visibility="collapsed")

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

# ── FILTER & SORT ─────────────────────────────────────────────
if search:
    kw = search.lower()
    saved_routes = [
        r for r in saved_routes
        if any(kw in r[k].lower() for k in ["name", "type", "from", "to"])
    ]

if sort_by == "Newest":
    saved_routes = list(reversed(saved_routes))
elif sort_by == "Cheapest":
    saved_routes = sorted(saved_routes, key=lambda r: r.get("price_raw", 0))

# ── CARDS ─────────────────────────────────────────────────────
if not saved_routes:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🗺️</div>
        <p class="empty-state-title">No saved routes found</p>
        <p class="empty-state-sub">Your saved routes will appear here after you bookmark them.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for route in saved_routes:
        with st.container(border=True):
            icon_col, info_col, price_col = st.columns([1, 5, 1.5])

            with icon_col:
                st.markdown(f"""
                <div style="
                    background:{route['bg']};
                    width:60px; height:60px;
                    border-radius:14px;
                    display:flex; align-items:center; justify-content:center;
                    font-size:28px;
                    margin-top:4px;
                ">{route['icon']}</div>
                """, unsafe_allow_html=True)

            with info_col:
                st.markdown(f"""
                <p class="result-card-badge" style="color:{route['color']}; margin-bottom:2px;">{route['type']}</p>
                <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:18px; font-weight:700; color:#1e2a52; margin:0 0 2px;">{route['name']} <span style="color:#f59e0b;">★</span></p>
                <p style="font-size:14px; color:#6b7280; margin:0 0 6px;">{route['from']} → {route['to']}</p>
                <p style="font-size:13px; color:#94a3b8; margin:0;">
                    📅 {route['date']} &nbsp;·&nbsp; ⏱ {route['duration']} &nbsp;·&nbsp; ⭐ {route['rating']}
                </p>
                """, unsafe_allow_html=True)

            with price_col:
                st.markdown(f"""
                <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:20px; font-weight:800; color:#1e2a52; text-align:right; margin:4px 0 12px;">{route['price']}</p>
                """, unsafe_allow_html=True)
                if st.button("View Details", key=f"fav_{route['from']}_{route['to']}_{route['name']}", use_container_width=True):
                    st.session_state.selected_route = route
                    st.session_state.selected_from  = route["from"]
                    st.session_state.selected_to    = route["to"]
                    st.session_state.selected_date  = route.get("date", "")
                    st.session_state.route_origin_page = "pages/favorite_routes.py"
                    st.session_state.route_origin_label = "Saved Routes"
                    if os.path.exists("pages/result.py"):
                        st.switch_page("pages/result.py")

        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
