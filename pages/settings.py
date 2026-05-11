# pages/settings.py

import streamlit as st
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Settings",
    layout="wide"
)

# ======================================================
# AUTH GUARD
# ======================================================
if "logged_in" not in st.session_state:
    st.switch_page("pages/login.py")

if not st.session_state.logged_in:
    st.switch_page("pages/login.py")

# ======================================================
# DEFAULT USER
# ======================================================
if "user" not in st.session_state:

    st.session_state.user = {
        "name": "Admin ANTARA",
        "email": "admin@antara.com",
        "phone": "+62 812-3456-7890",
        "password": "123"
    }

# ======================================================
# USER DATA
# ======================================================
user = st.session_state.user

# ======================================================
# THEME
# ======================================================
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"

# ======================================================
# LOAD CSS
# ======================================================
with open("style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# ======================================================
# APPLY GLOBAL THEME
# ======================================================
apply_theme()

# ======================================================
# LAYOUT
# ======================================================
col_sidebar, col_main = st.columns(
    [1, 4],
    gap="large"
)

# ======================================================
# SIDEBAR
# ======================================================
with col_sidebar:
    render_sidebar()

# ======================================================
# MAIN CONTENT
# ======================================================
with col_main:

    # ======================================================
    # HEADER
    # ======================================================
    st.markdown(
        """
        <h1 style="
            color:#0f9db4;
            font-size:32px;
            font-weight:700;
            margin-bottom:25px;
        ">
            │ Plan your Perfect Journey
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <h2 style="
            color:#1e2a52;
            font-size:26px;
            font-weight:700;
            margin-bottom:0;
        ">
            Settings
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style="
            color:#6b7280;
            margin-top:5px;
            margin-bottom:25px;
        ">
            Manage your account and application preferences.
        </p>
        """,
        unsafe_allow_html=True
    )

    # ======================================================
    # PROFILE INFORMATION
    # ======================================================
    with st.container(border=True):

        top_left, top_right = st.columns([4, 1])

        with top_left:
            st.markdown("### 👤 Profile Information")

        with top_right:
            st.markdown("<br>", unsafe_allow_html=True)

            edit_profile = st.button(
                "✏️ Edit Profile",
                use_container_width=True
            )

        # ======================================================
        # EDIT MODE
        # ======================================================
        if edit_profile:
            st.session_state.edit_profile = True

        if "edit_profile" not in st.session_state:
            st.session_state.edit_profile = False

        if st.session_state.edit_profile:

            c1, c2, c3 = st.columns(3)

            with c1:
                new_name = st.text_input(
                    "Name",
                    value=user["name"]
                )

            with c2:
                new_email = st.text_input(
                    "Email",
                    value=user["email"]
                )

            with c3:
                new_phone = st.text_input(
                    "Phone Number",
                    value=user["phone"]
                )

            save_profile = st.button(
                "Save Profile"
            )

            if save_profile:

                user["name"] = new_name
                user["email"] = new_email
                user["phone"] = new_phone

                st.session_state.user = user

                st.success(
                    "Profile updated successfully."
                )

                st.session_state.edit_profile = False

                st.rerun()

        else:

            c1, c2, c3 = st.columns(3)

            with c1:
                st.caption("Name")
                st.write(user["name"])

            with c2:
                st.caption("Email")
                st.write(user["email"])

            with c3:
                st.caption("Phone Number")
                st.write(user["phone"])

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================================================
    # CHANGE PASSWORD
    # ======================================================
    with st.container(border=True):

        top_left, top_right = st.columns([4, 1])

        with top_left:
            st.markdown("### 🔒 Change Password")

        with top_right:
            st.markdown("<br>", unsafe_allow_html=True)

            update_password = st.button(
                "Update Password",
                use_container_width=True
            )

        c1, c2, c3 = st.columns(3)

        with c1:
            current_password = st.text_input(
                "Current Password",
                type="password"
            )

        with c2:
            new_password = st.text_input(
                "New Password",
                type="password"
            )

        with c3:
            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

        if update_password:

            if current_password != user["password"]:

                st.error(
                    "Current password is incorrect."
                )

            elif new_password != confirm_password:

                st.error(
                    "New password does not match."
                )

            elif len(new_password) < 3:

                st.error(
                    "Password too short."
                )

            else:

                user["password"] = new_password

                st.session_state.user = user

                st.success(
                    "Password updated successfully."
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================================================
    # PREFERENCES
    # ======================================================
    with st.container(border=True):

        st.markdown("### ⚙️ Preferences")

        left, right = st.columns(2)

        with left:

            st.selectbox(
                "Default Currency",
                [
                    "IDR (Indonesian Rupiah)",
                    "USD (US Dollar)",
                    "EUR (Euro)"
                ]
            )

        with right:

            c1, c2 = st.columns(2)

            with c1:

                st.selectbox(
                    "Distance Unit",
                    [
                        "Kilometer (km)",
                        "Miles (mi)"
                    ]
                )

            with c2:

                st.selectbox(
                    "Time Format",
                    [
                        "24-hour (14:30)",
                        "12-hour (2:30 PM)"
                    ]
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================================================
    # APPEARANCE
    # ======================================================
    with st.container(border=True):

        st.markdown("### ☀️ Appearance")

        st.markdown("#### Theme")

        t1, t2 = st.columns(2)

        with t1:

            if st.button(
                "☀️ Light Mode",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.theme_mode == "Light"
                    else "secondary"
                )
            ):

                st.session_state.theme_mode = "Light"

                st.rerun()

        with t2:

            if st.button(
                "🌙 Dark Mode",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.theme_mode == "Dark"
                    else "secondary"
                )
            ):

                st.session_state.theme_mode = "Dark"

                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================================================
    # DELETE ACCOUNT
    # ======================================================
    with st.container(border=True):

        left, right = st.columns([4, 1])

        with left:

            st.markdown("### 🗑️ Delete Account")

            st.caption(
                "Permanently remove your account and all saved routes."
            )

        with right:

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "🗑️ Delete Account",
                use_container_width=True
            ):

                st.error(
                    "Delete account disabled in demo mode."
                )