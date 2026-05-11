import streamlit as st
import os
from pages.components.theme import apply_theme

st.set_page_config(
    page_title="Login - ANTARA",
    layout="wide"
)

# ======================
# DEFAULT USER
# ======================
if "user" not in st.session_state:

    st.session_state.user = {
        "name": "Admin ANTARA",
        "email": "admin@antara.com",
        "phone": "+62 812-3456-7890",
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

apply_theme()

# ======================
# HEADER
# ======================
left, right = st.columns([6, 1.8])

with left:
    st.image("assets/logo_antara.png", width=140)

with right:

    col_login, col_signup = st.columns(2)

    with col_login:
        st.button(
            "Login",
            use_container_width=True,
            key="login_header"
        )

    with col_signup:

        if st.button(
            "Sign Up",
            use_container_width=True,
            key="signup_header"
        ):

            st.switch_page("pages/signup.py")

st.markdown("<br><br>", unsafe_allow_html=True)

# ======================
# CENTER AREA
# ======================
c1, c2, c3 = st.columns([1, 2, 1])

with c2:

    # ======================
    # TITLE
    # ======================
    st.markdown(
        """
        <h2 style='
            text-align:center;
            color:#26a69a;
        '>
            Welcome Back to ANTARA
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # FORM
    # ======================
    email = st.text_input(
        "Email",
        key="email"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="password"
    )

    col_remember, col_forgot = st.columns([1, 1])

    with col_remember:

        remember = st.checkbox(
            "Remember me",
            key="remember"
        )

    with col_forgot:

        st.markdown(
            """
            <div style="text-align:right;">
            <a href="#" style="
                color:#26a69a;
                text-decoration:none;
            ">
                Forgot password?
            </a>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # LOGIN BUTTON
    # ======================
    left_btn, center_btn, right_btn = st.columns([1, 2, 1])

    with center_btn:

        if st.button(
            "Login",
            use_container_width=True,
            key="login_button"
        ):

            # ======================
            # LOGIN VALIDATION
            # ======================
            if (
                email == user["email"]
                and password == user["password"]
            ):

                st.session_state.logged_in = True

                st.session_state.current_user = user

                # ======================
                # RESET DASHBOARD STATE
                # ======================
                st.session_state.search_clicked = False
                st.session_state.searching = False

                st.session_state.selected_route = None
                st.session_state.search_result = None

                st.success(
                    "Login berhasil!"
                )

                st.switch_page(
                    "pages/dashboard.py"
                )

            else:

                st.error(
                    "Email atau password salah"
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # OR
    # ======================
    st.markdown(
        """
        <p style='
            text-align:center;
            color:gray;
        '>
            — OR —
        </p>
        """,
        unsafe_allow_html=True
    )

    # ======================
    # GOOGLE LOGIN
    # ======================
    google_logo = "assets/google.png"

    google_oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?client_id=YOUR_CLIENT_ID"
        "&redirect_uri=http://localhost:8501"
        "&response_type=token"
        "&scope=email profile"
    )

    if os.path.exists(google_logo):

        st.markdown(
            f"""
            <a href="{google_oauth_url}"
               style="text-decoration:none;">

            <div style="
                display:flex;
                align-items:center;
                justify-content:center;
                gap:10px;
                border:1px solid #ddd;
                border-radius:8px;
                padding:14px;
                margin-top:10px;
                cursor:pointer;
            ">

            <img src="assets/google.png" width="24">

            <span style="font-weight:500;">
                Login with Google
            </span>

            </div>
            </a>
            """,
            unsafe_allow_html=True
        )

    else:

        st.link_button(
            "Login with Google",
            google_oauth_url,
            use_container_width=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # SIGN UP LINK
    # ======================
    st.markdown(
    """
    <p style="text-align:center;">
    Don't have an account?
    <a href="/signup" target="_self" style="color:#26a69a; font-weight:600; text-decoration:none;">
    Sign Up
    </a>
    </p>
    """,
    unsafe_allow_html=True
    )