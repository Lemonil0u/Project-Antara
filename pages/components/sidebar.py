import streamlit as st

def render_sidebar():
    with st.container():

        st.markdown('<div class="sidebar-dashboard">', unsafe_allow_html=True)

        st.image("assets/logo_antara.png", width=130)
        st.markdown("<br>", unsafe_allow_html=True)

        # MENU
        if st.button("🏠 Home", use_container_width=True, key="sb_home"):
            st.switch_page("pages/dashboard.py")

        if st.button("📊 Visualization", use_container_width=True, key="sb_vis"):
            st.switch_page("pages/visualization.py")

        if st.button("⭐ Favorite Route", use_container_width=True, key="sb_fav"):
            st.switch_page("pages/favorite_routes.py")

        if st.button("⚙️ Settings", use_container_width=True, key="sb_set"):
            st.switch_page("pages/settings.py")

        st.markdown("<br><br>", unsafe_allow_html=True)

        if st.button("👤 Profile", use_container_width=True, key="sb_profile"):
            st.switch_page("pages/profile.py")

        if st.button("🚪 Logout", use_container_width=True, key="sb_logout"):
            st.session_state.logged_in = False
            st.switch_page("app.py")

        st.markdown('</div>', unsafe_allow_html=True)