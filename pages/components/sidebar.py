"""
pages/components/sidebar.py
============================
Sidebar navigasi ANTARA — menggunakan st.sidebar native Streamlit.
CSS disuntikkan sekali di sini, tidak perlu duplikasi di halaman lain.
"""

import streamlit as st
import os


def render_sidebar(active: str = ""):
    """
    Render sidebar navigasi.
    
    Args:
        active: Nama halaman aktif untuk highlight.
                Nilai: "home", "visualization", "favorites", "settings", "profile"
    """

    # Fix permanen untuk "keyboard_double_arrow_left" dan "cache" artifacts
    st.markdown("""
        <style>
        [data-testid="collapsedControl"], 
        button[aria-label="Collapse sidebar"], 
        button[aria-label="Expand sidebar"],
        .st-emotion-cache-5r6ut5 {
            display: none !important;
            font-size: 0 !important;
            color: transparent !important;
            visibility: hidden !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:

        # ── LOGO ─────────────────────────────────────
        if os.path.exists("assets/logo_antara.png"):
            st.image("assets/logo_antara.png", width=130)
        else:
            st.markdown(
                "<div style='font-family:Plus Jakarta Sans,sans-serif; font-size:22px; font-weight:800; color:#26a69a; padding:4px 4px 0;'>ANTARA</div>",
                unsafe_allow_html=True
            )

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

        # ── MENU ─────────────────────────────────────
        st.markdown('<span class="sb-section-label">Menu</span>', unsafe_allow_html=True)

        _nav_button("🏠  Home",         "sb_home",    active == "home",          "pages/dashboard.py")
        _nav_button("📊  Visualization", "sb_vis",     active == "visualization", "pages/visualization.py")
        _nav_button("⭐  Saved Routes",  "sb_fav",     active == "favorites",     "pages/favorite_routes.py")
        _nav_button("⚙️  Settings",      "sb_set",     active == "settings",      "pages/settings.py")

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

        # ── ACCOUNT ──────────────────────────────────
        st.markdown('<span class="sb-section-label">Account</span>', unsafe_allow_html=True)

        _nav_button("👤  Profile", "sb_profile", active == "profile", "pages/profile.py")

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        if st.button("🚪  Logout", key="sb_logout", use_container_width=True):
            st.session_state.logged_in = False
            st.switch_page("app.py")

        # ── USER BADGE (bottom) ───────────────────────
        if st.session_state.get("logged_in") and st.session_state.get("user"):
            user = st.session_state.user
            st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="
                    background: rgba(38,166,154,0.08);
                    border-radius: 12px;
                    padding: 10px 12px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <div style="
                        width: 32px; height: 32px;
                        background: linear-gradient(135deg, #26a69a, #1e8a80);
                        border-radius: 50%;
                        display: flex; align-items: center; justify-content: center;
                        color: white; font-weight: 700; font-size: 14px;
                        flex-shrink: 0;
                    ">{user.get('name', 'U')[0].upper()}</div>
                    <div>
                        <div style="font-size:13px; font-weight:600; color:#1e2a52; line-height:1.2;">{user.get('name', 'User')}</div>
                        <div style="font-size:11px; color:#9ca3af; line-height:1.2;">{user.get('email', '')}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def _nav_button(label: str, key: str, is_active: bool, target_page: str):
    """Render satu tombol navigasi sidebar."""
    wrap_class = "sb-nav-active" if is_active else ""
    st.markdown(f'<div class="{wrap_class}">', unsafe_allow_html=True)
    if st.button(label, key=key, use_container_width=True):
        if os.path.exists(target_page):
            st.switch_page(target_page)
    st.markdown("</div>", unsafe_allow_html=True)
