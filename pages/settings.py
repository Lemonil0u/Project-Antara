"""
pages/settings.py — ANTARA
============================
Pengaturan akun, password, preferensi, dan tampilan.
"""

import streamlit as st
import os
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Settings — ANTARA", layout="wide")

# ── AUTH GUARD ───────────────────────────────────────────────
if not st.session_state.get("logged_in", False):
    st.switch_page("pages/login.py")

# ── STATE ────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = {
        "name": "Admin ANTARA",
        "email": "admin@antara.com",
        "phone": "+62 812-3456-7890",
        "password": "123",
    }
if "theme_mode"    not in st.session_state:
    st.session_state.theme_mode = "Light"
if "edit_profile"  not in st.session_state:
    st.session_state.edit_profile = False

user = st.session_state.user

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="settings")

# ── PAGE HEADER ──────────────────────────────────────────────
st.markdown('<p class="page-eyebrow">ANTARA · Configuration</p>', unsafe_allow_html=True)
st.markdown('<h1 class="page-title">Settings</h1>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Manage your account and application preferences.</p>', unsafe_allow_html=True)

# ── PROFILE INFORMATION ───────────────────────────────────────
with st.container(border=True):
    tl, tr = st.columns([4, 1])
    with tl:
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:0;'>👤 Profile Information</p>", unsafe_allow_html=True)
    with tr:
        if st.button("✏️  Edit", use_container_width=True, type="secondary", key="edit_btn"):
            st.session_state.edit_profile = not st.session_state.edit_profile

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    if st.session_state.edit_profile:
        c1, c2, c3 = st.columns(3)
        with c1: new_name  = st.text_input("Name",         value=user["name"])
        with c2: new_email = st.text_input("Email",        value=user["email"])
        with c3: new_phone = st.text_input("Phone Number", value=user["phone"])

        save_col, cancel_col, _ = st.columns([1, 1, 4])
        with save_col:
            if st.button("Save", key="save_profile"):
                user.update({"name": new_name, "email": new_email, "phone": new_phone})
                st.session_state.user = user
                st.session_state.edit_profile = False
                st.success("Profile updated.")
                st.rerun()
        with cancel_col:
            if st.button("Cancel", type="secondary", key="cancel_profile"):
                st.session_state.edit_profile = False
                st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        for col, label, value in [
            (c1, "Name",         user["name"]),
            (c2, "Email",        user["email"]),
            (c3, "Phone Number", user["phone"]),
        ]:
            with col:
                st.caption(label)
                st.markdown(f"<p style='font-size:15px; font-weight:500; color:#1e2a52; margin-top:2px;'>{value}</p>", unsafe_allow_html=True)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── CHANGE PASSWORD ───────────────────────────────────────────
with st.container(border=True):
    tl, tr = st.columns([4, 1])
    with tl:
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:0;'>🔒 Change Password</p>", unsafe_allow_html=True)
    with tr:
        update_pw = st.button("Update", use_container_width=True, key="update_pw")

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: cur_pw  = st.text_input("Current Password", type="password")
    with c2: new_pw  = st.text_input("New Password",     type="password")
    with c3: conf_pw = st.text_input("Confirm Password", type="password")

    if update_pw:
        if cur_pw != user["password"]:
            st.error("Current password incorrect.")
        elif new_pw != conf_pw:
            st.error("New passwords do not match.")
        elif len(new_pw) < 3:
            st.error("Password too short (min. 3 characters).")
        else:
            user["password"] = new_pw
            st.session_state.user = user
            st.success("Password updated successfully.")

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── PREFERENCES ───────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:12px;'>⚙️ Preferences</p>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    with p1:
        st.selectbox("Default Currency",  ["IDR (Indonesian Rupiah)", "USD (US Dollar)", "EUR (Euro)"])
    with p2:
        st.selectbox("Distance Unit",     ["Kilometer (km)", "Miles (mi)"])
    with p3:
        st.selectbox("Time Format",       ["24-hour (14:30)", "12-hour (2:30 PM)"])

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── APPEARANCE ────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#1e2a52; margin-bottom:12px;'>☀️ Appearance</p>", unsafe_allow_html=True)
    st.caption("Changes theme across all pages.")

    t1, t2, *_ = st.columns([1, 1, 2])
    with t1:
        if st.button(
            "☀️  Light Mode",
            use_container_width=True,
            type="primary" if st.session_state.theme_mode == "Light" else "secondary",
        ):
            st.session_state.theme_mode = "Light"
            st.rerun()
    with t2:
        if st.button(
            "🌙  Dark Mode",
            use_container_width=True,
            type="primary" if st.session_state.theme_mode == "Dark" else "secondary",
        ):
            st.session_state.theme_mode = "Dark"
            st.rerun()

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# ── DANGER ZONE ───────────────────────────────────────────────
with st.container(border=True):
    dl, dr = st.columns([4, 1])
    with dl:
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:17px; font-weight:700; color:#ef4444; margin-bottom:2px;'>🗑️ Delete Account</p>", unsafe_allow_html=True)
        st.caption("Permanently remove your account and all saved data.")
    with dr:
        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        if st.button("Delete Account", use_container_width=True, type="secondary"):
            st.error("Delete account is disabled in demo mode.")
