"""
pages/profile.py — ANTARA
===========================
Halaman profil user: data pribadi, aktivitas, preferensi.
"""

import streamlit as st
import os
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Profile — ANTARA", layout="wide")

# ── STATE ────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = {
        "name":     "Admin ANTARA",
        "email":    "admin@antara.com",
        "phone":    "+62 812-3456-7890",
        "location": "Jakarta, Indonesia",
        "password": "123",
    }

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"

user = st.session_state.user

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="profile")

# ── PAGE HEADER ──────────────────────────────────────────────
st.markdown('<p class="page-eyebrow">ANTARA · Your Account</p>', unsafe_allow_html=True)
st.markdown('<h1 class="page-title">Profile</h1>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Manage your personal information and preferences.</p>', unsafe_allow_html=True)

# ── PROFILE CARD ──────────────────────────────────────────────
with st.container(border=True):
    _, edit_col = st.columns([5, 1])
    with edit_col:
        if st.button("✏️  Edit Profile", use_container_width=True, type="secondary"):
            st.switch_page("pages/settings.py")

    PROFILE_ROWS = [
        ("👤", "Full Name",    user["name"]),
        ("✉️", "Email",        user["email"]),
        ("📞", "Phone Number", user["phone"]),
        ("📍", "Location",     user.get("location", "Jakarta, Indonesia")),
    ]

    for i, (icon, label, value) in enumerate(PROFILE_ROWS):
        ic, lb, vl = st.columns([0.4, 2, 4])
        with ic:
            st.markdown(f"""
            <div style="
                width:36px; height:36px;
                background:#f0fafa;
                border-radius:10px;
                display:flex; align-items:center; justify-content:center;
                font-size:17px; margin-top:4px;
            ">{icon}</div>
            """, unsafe_allow_html=True)
        with lb:
            st.markdown(f"<p style='font-size:12px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:0.05em; margin:10px 0 0;'>{label}</p>", unsafe_allow_html=True)
        with vl:
            st.markdown(f"<p style='font-size:15px; font-weight:500; color:#1e2a52; margin:10px 0 0;'>{value}</p>", unsafe_allow_html=True)

        if i < len(PROFILE_ROWS) - 1:
            st.divider()

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── ACTIVITY + PREFERENCES ────────────────────────────────────
act_col, pref_col = st.columns(2)

with act_col:
    with st.container(border=True):
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:4px;'>📊 Your Activity</p>", unsafe_allow_html=True)
        st.caption("Overview of your activity on ANTARA.")

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        ACTIVITIES = [
            ("🗺️", "12", "Routes\nSearched"),
            ("🔖",  "5",  "Routes\nSaved"),
            ("⭐",  "3",  "Favorite\nRoutes"),
            ("🕒",  "28", "Hours\nSaved"),
        ]

        cols = st.columns(4)
        for col, (icon, value, label) in zip(cols, ACTIVITIES):
            with col:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-card-icon">{icon}</div>
                    <div class="stat-card-value">{value}</div>
                    <div class="stat-card-label">{label.replace(chr(10), '<br>')}</div>
                </div>
                """, unsafe_allow_html=True)

with pref_col:
    with st.container(border=True):
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:4px;'>⚙️ Preferences Summary</p>", unsafe_allow_html=True)
        st.caption("Your current preference settings.")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        PREFS = [
            ("🚌", "Default Transport",  "Bus"),
            ("💲", "Default Currency",   "IDR"),
            ("📏", "Distance Unit",      "Kilometer (km)"),
            ("🕒", "Time Format",        "24-hour"),
            ("☀️", "Theme",              st.session_state.get("theme_mode", "Light") + " Mode"),
        ]

        for i, (icon, label, value) in enumerate(PREFS):
            p1, p2, p3 = st.columns([0.5, 3, 2])
            with p1:
                st.markdown(f"<p style='font-size:17px; margin:4px 0;'>{icon}</p>", unsafe_allow_html=True)
            with p2:
                st.markdown(f"<p style='font-size:13px; font-weight:500; color:#374151; margin:6px 0;'>{label}</p>", unsafe_allow_html=True)
            with p3:
                st.markdown(f"<p style='font-size:13px; color:#94a3b8; text-align:right; margin:6px 0;'>{value}</p>", unsafe_allow_html=True)

            if i < len(PREFS) - 1:
                st.divider()
