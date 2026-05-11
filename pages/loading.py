import streamlit as st
import time
from pages.components.theme import apply_theme

st.set_page_config(layout="centered")

# =========================
# CSS
# =========================
st.markdown("""
<style>

.container{
    text-align:center;
    margin-top:120px;
}

.title{
    font-size:34px;
    font-weight:700;
    color:#26a69a;
}

.subtitle{
    font-size:18px;
    color:gray;
}

.progress-wrapper{
    width:60%;
    margin:auto;
    margin-top:25px;
}

.estimate{
    margin-top:25px;
    font-size:16px;
    color:#555;
}

.desc{
    color:gray;
    margin-top:5px;
}

</style>
""", unsafe_allow_html=True)

apply_theme()

# =========================
# LAYOUT
# =========================

st.markdown('<div class="container">', unsafe_allow_html=True)

st.image("assets/logo_antara.png", width=180)

st.markdown('<div class="title">Mencari Rute...</div>', unsafe_allow_html=True)

text_placeholder = st.empty()

st.markdown('<div class="progress-wrapper">', unsafe_allow_html=True)

progress = st.progress(0)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="estimate">
⏱ Estimated time: 2–3 seconds
</div>

<div class="desc">
mengumpulkan data dari pesawat, kereta, dan bus...
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# TEXT ROTATION
# =========================

messages = [
"Searching for flights...",
"Searching for trains...",
"Searching for buses..."
]

# =========================
# LOADING LOOP
# =========================

for i in range(100):

    msg = messages[(i // 30) % 3]

    text_placeholder.markdown(
        f'<div class="subtitle">{msg}</div>',
        unsafe_allow_html=True
    )

    progress.progress(i + 1)

    time.sleep(0.03)

# =========================
# REDIRECT
# =========================

st.session_state.search_clicked = True
st.switch_page("app.py")