"""
pages/login.py — ANTARA
=========================
Halaman login.
"""

import streamlit as st
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DatabaseManager

st.set_page_config(page_title="Login — ANTARA", layout="centered")

# ── CSS ──────────────────────────────────────────────────────
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── REDIRECT jika sudah login ────────────────────────────────
if st.session_state.get("logged_in"):
    st.switch_page("pages/dashboard.py")

# ── LAYOUT ───────────────────────────────────────────────────
st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)

_, c_mid, _ = st.columns([1, 2, 1])

with c_mid:
    # Logo
    if os.path.exists("assets/logo_antara.png"):
        st.image("assets/logo_antara.png", width=110)
    else:
        st.markdown("<p style='font-family:Plus Jakarta Sans,sans-serif; font-size:26px; font-weight:800; color:#26a69a;'>ANTARA</p>", unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<p class="page-eyebrow" style="margin-bottom:4px;">Welcome Back</p>', unsafe_allow_html=True)
        st.markdown('<h2 style="font-family:Plus Jakarta Sans,sans-serif; font-size:1.6rem; font-weight:800; color:#1e2a52; margin:0 0 4px;">Sign In</h2>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:14px; color:#94a3b8; margin-bottom:20px;">Enter your credentials to continue</p>', unsafe_allow_html=True)

        email    = st.text_input("Email", placeholder="username")
        password = st.text_input("Password", type="password", placeholder="••••••••")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        if st.button("Sign In", use_container_width=True):
            if not email or not password:
                st.error("Email dan password wajib diisi.")
            else:
                db = DatabaseManager()
                user = db.get_user_by_email(email.strip(), password)

                # Fallback demo credentials (biar ga break demo)
                if user is None and email == "admin@antara.com" and password == "123":
                    user = {
                        "id":       None,
                        "name":     "Admin ANTARA",
                        "email":    email,
                        "phone":    "+62 812-3456-7890",
                        "location": "Jakarta, Indonesia",
                    }

                if user is not None:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success("Login berhasil! Redirecting...")
                    st.switch_page("pages/dashboard.py")
                else:
                    st.error("Email atau password salah.")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        st.markdown('<p style="text-align:center; font-size:14px; color:#94a3b8;">Belum punya akun?</p>', unsafe_allow_html=True)

        if st.button("Buat Akun Baru", use_container_width=True, type="secondary"):
            if os.path.exists("pages/signup.py"):
                st.switch_page("pages/signup.py")

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; font-size:12px; color:#9ca3af;">Demo: admin@antara.com / 123</p>', unsafe_allow_html=True)
