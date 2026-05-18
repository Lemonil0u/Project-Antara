"""
app.py - ANTARA Project
=======================
Entry point utama Streamlit. Halaman home / landing.
Dilengkapi dengan modal login popup.

MERGE: UI dari temanmu (modal login, form search, popular routes)
       + database/cache dari fixku (DatabaseManager, price cache 60 menit)

Cara menjalankan:
    streamlit run app.py
"""

import base64
import os

import streamlit as st

try:
    from database import DatabaseManager
    from engine.data_source import MultiModalDataSource
    from engine.optimizer import SmartRouteOptimizer
    from models import SearchCriteria
    _HAS_ENGINE = True
except ImportError:
    _HAS_ENGINE = False

st.set_page_config(page_title="ANTARA", layout="wide")

if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── DATABASE + OPTIMIZER (dengan price cache) ────────────────────────────────
# MERGE: tambah DatabaseManager dan db= ke MultiModalDataSource
# agar price cache aktif (hemat 30-90 detik per re-scrape rute sama)
if _HAS_ENGINE:
    @st.cache_resource
    def get_db():
        return DatabaseManager()

    @st.cache_resource
    def get_optimizer():
        db = get_db()
        ds = MultiModalDataSource(
            headless=True,
            timeout=30,
            enabled_modes=["train", "flight", "bus"],
            db=db,               # ← price cache aktif
            cache_ttl_minutes=60,
        )
        return SmartRouteOptimizer(data_source=ds)

    db        = get_db()
    optimizer = get_optimizer()
else:
    db        = None
    optimizer = None

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for key, default in [
    ("search_clicked", False),
    ("selected_transport", ["Bus", "Train", "Flight"]),
    ("logged_in", False),
    ("login_modal_open", False),
    ("signup_modal_open", False),
    ("searching", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.logged_in:
    st.switch_page("pages/dashboard.py")

CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar", "Denpasar",
    "Palembang", "Balikpapan",
]


def get_base64_image(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def safe_image(path, **kwargs):
    if os.path.exists(path):
        st.image(path, **kwargs)


# ── LOGIN MODAL ───────────────────────────────────────────────────────────────
@st.dialog("Login ke ANTARA")
def show_login_modal():
    st.markdown('<p class="page-eyebrow" style="margin-bottom:4px;">Welcome Back</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:14px; color:#94a3b8; margin-bottom:20px;">Enter your credentials to continue</p>', unsafe_allow_html=True)

    with st.form("login_modal_form", enter_to_submit=True):
        email = st.text_input("Email", placeholder="username", key="modal_email")
        password = st.text_input("Password", type="password", placeholder="........", key="modal_password")
        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            submit_login = st.form_submit_button("Login", use_container_width=True)
        with col2:
            cancel_login = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

    if submit_login:
        if email == "admin@antara.com" and password == "123":
            st.session_state.logged_in = True
            st.session_state.user = {
                "name": "Admin ANTARA",
                "email": email,
                "phone": "+62 812-3456-7890",
                "location": "Jakarta, Indonesia",
                "password": password,
            }
            st.success("Login berhasil!")
            st.session_state.login_modal_open = False
            st.switch_page("pages/dashboard.py")
        else:
            st.error("Email atau password salah.")

    if cancel_login:
        st.session_state.login_modal_open = False
        st.rerun()

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; font-size:12px; color:#9ca3af;">Demo: admin@antara.com / 123</p>', unsafe_allow_html=True)


# ── SIGNUP MODAL ──────────────────────────────────────────────────────────────
@st.dialog("Create Account - ANTARA")
def show_signup_modal():
    st.markdown('<p class="page-eyebrow" style="margin-bottom:4px;">Get Started</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:14px; color:#94a3b8; margin-bottom:20px;">Join ANTARA and plan smarter journeys</p>', unsafe_allow_html=True)

    with st.form("signup_modal_form", enter_to_submit=True):
        full_name = st.text_input("Full Name", placeholder="Your name", key="modal_fullname")
        email     = st.text_input("Email", placeholder="your@email.com", key="modal_email_signup")
        phone     = st.text_input("Phone Number", placeholder="+62 8xx-xxxx-xxxx", key="modal_phone")
        password  = st.text_input("Password", type="password", placeholder="Minimum 6 characters", key="modal_password_signup")
        conf_pw   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="modal_conf_pw")
        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            submit_signup = st.form_submit_button("Create Account", use_container_width=True)
        with col2:
            cancel_signup = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

    if submit_signup:
        if not all([full_name, email, password, conf_pw]):
            st.error("Semua field wajib diisi.")
        elif password != conf_pw:
            st.error("Password tidak cocok.")
        elif len(password) < 6:
            st.error("Password minimal 6 karakter.")
        else:
            st.session_state.logged_in = True
            st.session_state.user = {
                "name": full_name,
                "email": email,
                "phone": phone,
                "location": "Indonesia",
                "password": password,
            }
            st.success("Akun berhasil dibuat!")
            st.session_state.signup_modal_open = False
            st.switch_page("pages/dashboard.py")

    if cancel_signup:
        st.session_state.signup_modal_open = False
        st.rerun()


# ── HEADER ────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([6, 1.8])

with h_left:
    safe_image("assets/logo_antara.png", width=140)

with h_right:
    if st.session_state.logged_in:
        col_user, col_logout = st.columns([1.5, 1])
        with col_user:
            user_name = st.session_state.get("user", {}).get("name", "User")
            st.markdown(f'<p style="font-size:13px; color:#64748b; margin:0; padding:8px 0;">User {user_name}</p>', unsafe_allow_html=True)
        with col_logout:
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = {}
                st.rerun()
    else:
        btn_l, btn_r = st.columns(2)
        with btn_l:
            if st.button("Login", use_container_width=True):
                st.session_state.login_modal_open = True
                st.rerun()
        with btn_r:
            if st.button("Sign Up", use_container_width=True, type="secondary"):
                st.session_state.signup_modal_open = True
                st.rerun()

if st.session_state.login_modal_open:
    show_login_modal()

if st.session_state.signup_modal_open:
    show_signup_modal()

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

_, c_hero, _ = st.columns([1, 2, 1])

with c_hero:
    st.markdown(
        """
    <div style="text-align:center; padding:12px 0 20px;">
        <p class="page-eyebrow" style="text-align:center;">ANTARA · Smart Route Finder</p>
        <h1 class="hero-title">Plan Your <span>Perfect Journey</span></h1>
        <p class="hero-subtitle">Find routes, compare transport, and travel smarter</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

# ── SEARCH FORM ───────────────────────────────────────────────────────────────
_, c_mid, _ = st.columns([1, 3, 1])

with c_mid:
    safe_image("assets/multi.png", use_container_width=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    with st.container():
        with st.form("app_search_form", enter_to_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                from_city = st.selectbox("From", CITIES, index=0, key="from_app")
            with col2:
                to_city = st.selectbox("To", CITIES, index=1, key="to_app")
            with col3:
                date_input = st.date_input("Date")

            st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
            submit_search = st.form_submit_button("🔍  Search Routes", use_container_width=True)

        if submit_search:
            if from_city == to_city:
                st.warning("Kota asal dan tujuan tidak boleh sama.")
            else:
                st.session_state.origin         = from_city
                st.session_state.destination    = to_city
                st.session_state.departure_date = str(date_input)
                st.session_state.passengers     = 1
                st.switch_page("pages/loading.py")

# ── POPULAR ROUTES ────────────────────────────────────────────────────────────
st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-title">Popular Routes</p>', unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
POPULAR = [
    ("assets/train.png", "Train", "#3b82f6", "Tugu Yogyakarta Station"),
    ("assets/bus.png",   "Bus",   "#22c55e", "Blok M Bus Terminal"),
    ("assets/plane.png", "Plane", "#f97316", "Soekarno-Hatta Airport"),
]

for col, (img_path, title, color, subtitle) in zip([r1, r2, r3], POPULAR):
    with col:
        b64 = get_base64_image(img_path)
        img_html = f'<img src="data:image/png;base64,{b64}" style="width:100%; border-radius:12px;">' if b64 else ""
        st.markdown(
            f"""
        <div class="route-tile">
            {img_html}
            <p class="route-tile-type" style="color:{color}; margin-top:10px;">{title}</p>
            <p class="route-tile-title">{title}</p>
            <p class="route-tile-sub">{subtitle}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
