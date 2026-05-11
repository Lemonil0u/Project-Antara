import streamlit as st
import os

st.set_page_config(page_title="Sign Up - ANTARA", layout="wide")

# ======================
# LOAD CSS
# ======================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ======================
# HEADER
# ======================
left, right = st.columns([6,1.8])

with left:
    st.image("assets/logo_antara.png", width=140)

with right:
    col_login, col_signup = st.columns(2)

    with col_login:
        if st.button("Login", use_container_width=True):
            st.switch_page("pages/login.py")

    with col_signup:
        st.button("Sign Up", use_container_width=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# ======================
# CENTER AREA
# ======================
c1, c2, c3 = st.columns([1,2,1])

with c2:

    st.markdown(
        "<h2 style='text-align:center; color:#26a69a;'>Create Your ANTARA Account</h2>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # FORM
    # ======================
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # REMEMBER ME
    # ======================
    remember = st.checkbox("Remember me")

    st.markdown("<br>", unsafe_allow_html=True)

    # ======================
    # CREATE ACCOUNT BUTTON
    # ======================
    left_btn, center_btn, right_btn = st.columns([1,2,1])

    with center_btn:
        if st.button("Create Account", use_container_width=True):

            if password != confirm_password:
                st.error("Password tidak sama")

            elif name == "" or email == "" or password == "":
                st.warning("Semua field harus diisi")

            else:
                st.success("Account berhasil dibuat!")
                st.switch_page("app.py")

    # ======================
    # OR
    # ======================
    st.markdown(
        "<p style='text-align:center; color:gray;'>— OR —</p>",
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
        <a href="{google_oauth_url}" style="text-decoration:none;">
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
        <span style="font-weight:500;">Login with Google</span>
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
    # LOGIN LINK (SAME TAB)
    # ======================
    st.markdown(
    """
    <p style="text-align:center;">
    Already have an account?
    <a href="/login" target="_self" style="color:#26a69a; font-weight:600; text-decoration:none;">
    Login
    </a>
    </p>
    """,
    unsafe_allow_html=True
    )