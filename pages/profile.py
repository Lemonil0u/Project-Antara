import streamlit as st
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(
    page_title="Profile - ANTARA",
    layout="wide"
)

# ======================
# APPLY THEME
# ======================
apply_theme()

# ======================
# USER DATA
# ======================
if "user" not in st.session_state:

    st.session_state.user = {
        "name": "Admin ANTARA",
        "email": "admin@antara.com",
        "phone": "+62 812-3456-7890",
        "location": "Jakarta, Indonesia",
        "password": "123"
    }

user = st.session_state.user

# ======================
# LOAD CSS
# ======================
with open("style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# ======================
# THEME COLORS
# ======================
is_dark = st.session_state.get("theme_mode") == "Dark"

TEXT = "white" if is_dark else "#1e293b"
SUBTEXT = "#cbd5e1" if is_dark else "#64748b"
CARD_BG = "#111827" if is_dark else "white"

# ======================
# LAYOUT
# ======================
sidebar, main = st.columns([1,4])

# ======================
# SIDEBAR
# ======================
with sidebar:
    render_sidebar()

# ======================
# MAIN CONTENT
# ======================
with main:

    # HEADER
    st.markdown(
        f"""
        <h1 style="
            color:#0f9db4;
            font-size:24px;
            margin-bottom:25px;
        ">
            │ Plan your Perfect Journey
        </h1>
        """,
        unsafe_allow_html=True
    )

    # TITLE
    st.markdown(
        f"""
        <h1 style="
            color:{TEXT};
            margin-bottom:0;
        ">
            Profile
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <p style="
            color:{SUBTEXT};
            margin-top:0;
            margin-bottom:30px;
        ">
            Manage your personal information and preferences.
        </p>
        """,
        unsafe_allow_html=True
    )

    # ======================
    # PROFILE CARD
    # ======================
    with st.container(border=True):

        top_left, top_right = st.columns([5,1])

        with top_right:

            if st.button(
                "🖊 Edit Profile",
                use_container_width=True
            ):
                st.switch_page("pages/settings.py")

        profile_data = [
            ("👤", "Full Name", user["name"]),
            ("✉️", "Email", user["email"]),
            ("📞", "Phone Number", user["phone"]),
            ("📍", "Location", user.get("location", "Jakarta, Indonesia"))
        ]

        for i, (icon, label, value) in enumerate(profile_data):

            c1, c2, c3 = st.columns([0.4,2,3])

            with c1:

                st.markdown(
                    f"""
                    <div style="
                        font-size:22px;
                        margin-top:4px;
                        text-align:center;
                    ">
                        {icon}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c2:

                st.markdown(
                    f"""
                    <div style="
                        font-size:15px;
                        font-weight:600;
                        color:{TEXT};
                        margin-top:4px;
                    ">
                        {label}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c3:

                st.markdown(
                    f"""
                    <div style="
                        font-size:15px;
                        color:{SUBTEXT};
                        margin-top:4px;
                        margin-bottom:14px;
                    ">
                        {value}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if i != len(profile_data) - 1:

                st.markdown(
                    """
                    <hr style="
                        margin-top:8px;
                        margin-bottom:8px;
                        border:none;
                        border-top:1px solid #e5e7eb;
                    ">
                    """,
                    unsafe_allow_html=True
                )
            else:

                st.markdown(
                    """
                    <div style="padding-bottom:18px;"></div>
                    """,
                    unsafe_allow_html=True
                ) 
    # ======================
    # ACTIVITY + PREFERENCE
    # ======================
    left_box, right_box = st.columns(2)

    # ======================
    # ACTIVITY
    # ======================
    with left_box:

        with st.container(border=True):

            st.markdown(
                f"""
                <h3 style="
                    color:{TEXT};
                    margin-bottom:4px;
                ">
                    📊 Your Activity
                </h3>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <p style="
                    color:{SUBTEXT};
                    margin-bottom:28px;
                    font-size:14px;
                ">
                    Overview of your activity on Antara.
                </p>
                """,
                unsafe_allow_html=True
            )

            a1, a2, a3, a4 = st.columns(4)

            activities = [
                ("🗺️", "12", "Routes Searched"),
                ("🔖", "5", "Routes Saved"),
                ("⭐", "3", "Favorite Routes"),
                ("🕒", "28", "Hours Saved")
            ]

            for col, data in zip(
                [a1, a2, a3, a4],
                activities
            ):

                icon, value, label = data

                with col:

                    st.markdown(
                        f"<h2 style='text-align:center; margin-bottom:0;'>{icon}</h2>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <h1 style="
                            text-align:center;
                            font-size:34px;
                            margin-top:0;
                            margin-bottom:0;
                            color:{TEXT};
                        ">
                            {value}
                        </h1>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"""
                        <p style="
                            text-align:center;
                            font-size:12px;
                            color:{SUBTEXT};
                            margin-top:4px;
                        ">
                            {label}
                        </p>
                        """,
                        unsafe_allow_html=True
                    )

    # ======================
    # PREFERENCES
    # ======================
    with right_box:

        with st.container(border=True):

            st.markdown(
                f"""
                <h3 style="
                    color:{TEXT};
                    margin-bottom:4px;
                ">
                    ⚙️ Preferences Summary
                </h3>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <p style="
                    color:{SUBTEXT};
                    margin-bottom:25px;
                    font-size:14px;
                ">
                    Your current preference settings.
                </p>
                """,
                unsafe_allow_html=True
            )

            preferences = [
                ("🚌", "Default Transport Mode", "Bus"),
                ("💲", "Default Currency", "IDR"),
                ("📏", "Distance Unit", "Kilometer (km)"),
                ("🕒", "Time Format", "24-hour"),
                (
                    "☀️",
                    "Theme",
                    st.session_state.get(
                        "theme_mode",
                        "Light"
                    ) + " Mode"
                )
            ]

            for i, (icon, label, value) in enumerate(preferences):

                p1, p2, p3 = st.columns([0.5,2.5,2])

                with p1:
                    st.markdown(
                        f"""
                        <div style="
                            font-size:18px;
                            margin-top:2px;
                        ">
                            {icon}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with p2:
                    st.markdown(
                        f"""
                        <div style="
                            color:{TEXT};
                            font-weight:500;
                            font-size:14px;
                            margin-top:4px;
                        ">
                            {label}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with p3:
                    st.markdown(
                        f"""
                        <div style="
                            text-align:right;
                            color:{SUBTEXT};
                            font-size:14px;
                            margin-top:4px;
                            margin-bottom:8px;
                        ">
                            {value}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                if i != len(preferences) - 1:

                    st.markdown(
                        """
                        <hr style="
                            margin-top:10px;
                            margin-bottom:10px;
                            border:none;
                            border-top:1px solid #e5e7eb;
                        ">
                        """,
                        unsafe_allow_html=True
                    )