"""
pages/result.py - ANTARA
========================
Detail rute yang dipilih + peta + amenities.
"""

import os
import json

import streamlit as st
import streamlit.components.v1 as components

from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DatabaseManager

st.set_page_config(page_title="Route Detail - ANTARA", layout="wide")

# CSS & THEME
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# SESSION DATA
route = st.session_state.get("selected_route")
from_city = st.session_state.get("selected_from", "")
to_city = st.session_state.get("selected_to", "")
origin_page = st.session_state.get("route_origin_page", "pages/dashboard.py")
origin_label = st.session_state.get("route_origin_label", "Results")

def get_combo_id_str(route, origin_from, origin_to):
    """Versi string dari route identity, buat disimpan di DB."""
    return json.dumps(get_route_identity(route, origin_from, origin_to))

def get_route_identity(route_data, origin_from, origin_to):
    return (
        route_data.get("type", ""),
        route_data.get("name", ""),
        origin_from,
        origin_to,
        route_data.get("time", ""),
    )


def build_saved_route(route_data, origin_from, origin_to):
    transport_type = route_data.get("type", "")
    color_map = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}
    bg_map = {"Bus": "#eef9f0", "Train": "#eef4ff", "Flight": "#fff6eb"}
    icon_map = {"Bus": "🚌", "Train": "🚆", "Flight": "✈️"}
    return {
        **route_data,
        "from": origin_from,
        "to": origin_to,
        "date": st.session_state.get("selected_date", ""),
        "icon": route_data.get("icon", icon_map.get(transport_type, "⭐")),
        "color": route_data.get("color", color_map.get(transport_type, "#26a69a")),
        "bg": route_data.get("bg", bg_map.get(transport_type, "#f8fffe")),
    }


def toggle_saved_route():
    current_route = st.session_state.get("selected_route")
    current_from  = st.session_state.get("selected_from", "")
    current_to    = st.session_state.get("selected_to", "")
    if not current_route:
        return

    user_id  = st.session_state.get("user", {}).get("id")
    combo_id = get_combo_id_str(current_route, current_from, current_to)
    route    = build_saved_route(current_route, current_from, current_to)

    db = DatabaseManager()
    if db.get_saved_route_by_combo(combo_id, user_id=user_id):
        # Sudah tersimpan → hapus
        db.delete_saved_route_by_combo(combo_id, user_id=user_id)
    else:
        # Belum tersimpan → tambah. Simpan FULL display dict di combo_json
        # biar UI nanti bisa restore tampilan persis (icon, color, bg, dll)
        db.add_saved_route(
            combo_id=combo_id,
            route_label=f"{current_from} → {current_to}",
            mode_label=route.get("type", ""),
            total_price=route.get("price_raw", 0),
            total_duration_minutes=0,  # belum ada di session, isi 0 dulu
            combo_data=route,
            user_id=user_id,
        )

if not route:
    st.warning("Silakan pilih route terlebih dahulu.")
    if st.button(f"<- Kembali ke {origin_label}"):
        st.switch_page(origin_page)
    st.stop()

departure, arrival = route["time"].split(" - ") if " - " in route.get("time", " - ") else ("-", "-")
user_id = st.session_state.get("user", {}).get("id")
_combo_id = get_combo_id_str(route, from_city, to_city)
is_saved = DatabaseManager().get_saved_route_by_combo(_combo_id, user_id=user_id) is not None

# SIDEBAR
render_sidebar()

# PAGE HEADER
top_l, top_r = st.columns([4, 1])

with top_l:
    st.markdown('<p class="page-eyebrow">ANTARA · Route Detail</p>', unsafe_allow_html=True)
    st.markdown(
        f'<h1 class="page-title">{from_city} → {to_city}</h1>',
        unsafe_allow_html=True,
    )

with top_r:
    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    st.button(
        "★ Saved Route" if is_saved else "☆ Save Route",
        use_container_width=True,
        type="secondary",
        on_click=toggle_saved_route,
    )

if st.button(f"<- Back to {origin_label}", type="secondary"):
    st.switch_page(origin_page)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# CONTENT
left_col, right_col = st.columns([3, 1.2])

with left_col:
    maps_url = f"https://www.google.com/maps?q={from_city}+to+{to_city}&output=embed"
    components.iframe(maps_url, height=420, scrolling=False)

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)

        for col, label, value in [
            (c1, "Total Duration", route.get("duration", "-")),
            (c2, "Distance", route.get("distance", "-")),
            (c3, "Departure", departure),
            (c4, "Arrival", arrival),
        ]:
            with col:
                st.caption(label)
                st.markdown(
                    f"<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:20px; font-weight:700; color:#1e2a52; margin:0;'>{value}</p>",
                    unsafe_allow_html=True,
                )

        st.divider()

        st.markdown(
            "<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:8px;'>About This Route</p>",
            unsafe_allow_html=True,
        )
        st.write(route.get("about", "No route description available."))

with right_col:
    with st.container(border=True):
        color = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}.get(route.get("type", ""), "#26a69a")

        st.markdown(
            f"""
        <p class="result-card-badge" style="color:{color};">{route.get('type', '')}</p>
        <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:20px; font-weight:700; color:#1e2a52; margin:4px 0;">{route.get('name', '')}{' <span style="color:#f59e0b;">★</span>' if is_saved else ''}</p>
        <p class="result-card-meta">{route.get('time', '')} · {route.get('duration', '')}</p>
        <p style="color:#f59e0b; font-size:14px;">⭐ {route.get('rating', '')}</p>
        <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:26px; font-weight:800; color:#1e2a52; margin:12px 0 4px;">{route.get('price', '')}</p>
        """,
            unsafe_allow_html=True,
        )

        st.button("Route Selected", use_container_width=True, disabled=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    route_details = route.get("route_details", [])
    if route_details:
        with st.container(border=True):
            st.markdown(
                "<p style='font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:12px;'>Route Details</p>",
                unsafe_allow_html=True,
            )
            for i, stop in enumerate(route_details):
                if i == 0:
                    st.markdown(f"📍 **{stop}** - {departure}")
                elif i == len(route_details) - 1:
                    st.markdown(f"📍 **{stop}** - {arrival}")
                else:
                    st.markdown(f"🟢 {stop}")

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    amenities = route.get("amenities", [])
    if amenities:
        with st.container(border=True):
            st.markdown(
                "<p style='font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:12px;'>Amenities</p>",
                unsafe_allow_html=True,
            )
            cols = st.columns(2)
            for i, amenity in enumerate(amenities):
                with cols[i % 2]:
                    st.markdown(f"✅ {amenity}")
