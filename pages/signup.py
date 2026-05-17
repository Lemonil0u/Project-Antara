"""
pages/signup.py — ANTARA
==========================
Halaman registrasi akun baru.
"""

import streamlit as st
import os

st.set_page_config(page_title="Sign Up — ANTARA", layout="centered")

# ── CSS ──────────────────────────────────────────────────────
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if st.session_state.get("logged_in"):
    st.switch_page("pages/dashboard.py")

# ── LAYOUT ───────────────────────────────────────────────────
st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)

_, c_mid, _ = st.columns([1, 2, 1])

with c_mid:
    if os.path.exists("assets/logo_antara.png"):
        st.image("assets/logo_antara.png", width=110)
    else:
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:26px; font-weight:800; color:#26a69a;'>ANTARA</p>", unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<p class="page-eyebrow" style="margin-bottom:4px;">Get Started</p>', unsafe_allow_html=True)
        st.markdown('<h2 style="font-family:Plus Jakarta Sans,sans-serif; font-size:1.6rem; font-weight:800; color:#1e2a52; margin:0 0 4px;">Create Account</h2>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:14px; color:#94a3b8; margin-bottom:20px;">Join ANTARA and plan smarter journeys</p>', unsafe_allow_html=True)

        full_name = st.text_input("Full Name",       placeholder="Your name")
        email     = st.text_input("Email",           placeholder="your@email.com")
        phone     = st.text_input("Phone Number",    placeholder="+62 8xx-xxxx-xxxx")
        password  = st.text_input("Password",        type="password", placeholder="Minimum 6 characters")
        conf_pw   = st.text_input("Confirm Password", type="password", placeholder="Repeat password")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        if st.button("Create Account", use_container_width=True):
            if not all([full_name, email, password, conf_pw]):
                st.error("Semua field wajib diisi.")
            elif password != conf_pw:
                st.error("Password tidak cocok.")
            elif len(password) < 6:
                st.error("Password minimal 6 karakter.")
            else:
                st.session_state.logged_in = True
                st.session_state.user = {
                    "name":     full_name,
                    "email":    email,
                    "phone":    phone,
                    "location": "Indonesia",
                    "password": password,
                }
                st.success("Akun berhasil dibuat!")
                st.switch_page("pages/dashboard.py")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; font-size:14px; color:#94a3b8;">Sudah punya akun?</p>', unsafe_allow_html=True)

        if st.button("Sign In", use_container_width=True, type="secondary"):
            if os.path.exists("pages/login.py"):
                st.switch_page("pages/login.py")
