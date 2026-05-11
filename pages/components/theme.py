import streamlit as st

def apply_theme():

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "Light"

    if st.session_state.theme_mode == "Dark":

        st.markdown("""
        <style>

        /* MAIN APP */
        .stApp {
            background-color: #0b132b;
        }

        /* TEXT GLOBAL */
        body {
            color: white;
        }

        /* HEADINGS ONLY */
        h1, h2, h3, h4, h5, h6 {
            color: white !important;
        }

        /* NORMAL TEXT */
        p, span, label {
            color: #d1d5db !important;
        }

        /* CONTAINER */
        div[data-testid="stContainer"] {
            background-color: transparent !important;
            border: none !important;
        }

        /* INPUT */
        .stTextInput input {
            background-color: #1f2937 !important;
            color: white !important;
            border: 1px solid #374151 !important;
        }

        /* SELECTBOX */
        .stSelectbox div[data-baseweb="select"] {
            background-color: #1f2937 !important;
            color: white !important;
            border: 1px solid #374151 !important;
        }

        /* BUTTON */
        .stButton button {
            background-color: #1f2937;
            color: white !important;
            border: 1px solid #374151;
        }

        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: #111827 !important;
        }

        /* CHECKBOX TEXT */
        .stCheckbox label {
            color: white !important;
        }

        /* SLIDER */
        .stSlider label {
            color: white !important;
        }

        /* METRIC */
        [data-testid="stMetricValue"] {
            color: white !important;
        }

        </style>
        """, unsafe_allow_html=True)