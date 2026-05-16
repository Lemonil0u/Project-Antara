"""
pages/result.py — ANTARA
==========================
Detail rute yang dipilih + peta + amenities.
"""

import streamlit as st
import streamlit.components.v1 as components
import os
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Route Detail — ANTARA", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── SESSION DATA ─────────────────────────────────────────────
route     = st.session_state.get("selected_route")
from_city = st.session_state.get("selected_from", "")
to_city   = st.session_state.get("selected_to", "")

if not route:
    st.warning("Silakan pilih route terlebih dahulu.")
    if st.button("← Kembali ke Dashboard"):
        st.switch_page("pages/dashboard.py")
    st.stop()

departure, arrival = route["time"].split(" - ") if " - " in route.get("time", " - ") else ("—", "—")

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar()

# ── PAGE HEADER ──────────────────────────────────────────────
top_l, top_r = st.columns([4, 1])

with top_l:
    st.markdown('<p class="page-eyebrow">ANTARA · Route Detail</p>', unsafe_allow_html=True)
    st.markdown(
        f'<h1 class="page-title">{from_city} → {to_city}</h1>',
        unsafe_allow_html=True
    )

with top_r:
    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    st.button("⭐  Save Route", use_container_width=True, type="secondary")

if st.button("← Back to Results", type="secondary"):
    st.switch_page("pages/dashboard.py")

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── CONTENT ──────────────────────────────────────────────────
left_col, right_col = st.columns([3, 1.2])

with left_col:

    # Maps embed
    maps_url = f"https://www.google.com/maps?q={from_city}+to+{to_city}&output=embed"
    components.iframe(maps_url, height=420, scrolling=False)

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    # Route info card
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)

        for col, label, value in [
            (c1, "Total Duration", route.get("duration", "—")),
            (c2, "Distance",       route.get("distance", "—")),
            (c3, "Departure",      departure),
            (c4, "Arrival",        arrival),
        ]:
            with col:
                st.caption(label)
                st.markdown(f"<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:20px; font-weight:700; color:#1e2a52; margin:0;'>{value}</p>", unsafe_allow_html=True)

        st.divider()

        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:8px;'>About This Route</p>", unsafe_allow_html=True)
        st.write(route.get("about", "No route description available."))

with right_col:

    # Selected route card
    with st.container(border=True):
        color = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}.get(route.get("type", ""), "#26a69a")

        st.markdown(f"""
        <p class="result-card-badge" style="color:{color};">{route.get('type', '')}</p>
        <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:20px; font-weight:700; color:#1e2a52; margin:4px 0;">{route.get('name', '')}</p>
        <p class="result-card-meta">{route.get('time', '')} · {route.get('duration', '')}</p>
        <p style="color:#f59e0b; font-size:14px;">⭐ {route.get('rating', '')}</p>
        <p style="font-family:Plus Jakarta Sans,sans-serif; font-size:26px; font-weight:800; color:#1e2a52; margin:12px 0 4px;">{route.get('price', '')}</p>
        """, unsafe_allow_html=True)

        st.button("✓ Route Selected", use_container_width=True, disabled=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    # Route stops
    route_details = route.get("route_details", [])
    if route_details:
        with st.container(border=True):
            st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:12px;'>Route Details</p>", unsafe_allow_html=True)
            for i, stop in enumerate(route_details):
                if i == 0:
                    st.markdown(f"📍 **{stop}** — {departure}")
                elif i == len(route_details) - 1:
                    st.markdown(f"📍 **{stop}** — {arrival}")
                else:
                    st.markdown(f"🟢 {stop}")

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    # Amenities
    amenities = route.get("amenities", [])
    if amenities:
        with st.container(border=True):
            st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-weight:700; font-size:15px; color:#1e2a52; margin-bottom:12px;'>Amenities</p>", unsafe_allow_html=True)
            cols = st.columns(2)
            for i, amenity in enumerate(amenities):
                with cols[i % 2]:
                    st.markdown(f"✅ {amenity}")
