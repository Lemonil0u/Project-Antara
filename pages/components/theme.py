"""
pages/components/theme.py
==========================
Terapkan dark mode via CSS injection.
"""

import streamlit as st


def apply_theme():
    """Inject CSS dark mode jika theme_mode == 'Dark'."""

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "Light"

    if st.session_state.theme_mode != "Dark":
        return

    st.markdown("""
    <style>

    /* ── DARK MODE GLOBAL ─────────────────────────── */
    .stApp {
        background-color: #0b132b !important;
    }

    .block-container {
        background-color: transparent !important;
    }

    /* HEADINGS */
    h1, h2, h3, h4, h5, h6,
    .page-title, .auth-title, .section-title,
    .hero-title, .result-card-name,
    .highlight-value, .stat-card-value {
        color: #f1f5f9 !important;
    }

    /* BODY TEXT */
    p, span, li,
    .page-subtitle, .hero-subtitle,
    .result-card-meta, .route-tile-sub,
    .highlight-desc, .filter-section-label {
        color: #94a3b8 !important;
    }

    /* LABELS */
    .stTextInput label,
    .stSelectbox label,
    .stDateInput label,
    .stSlider label,
    .stCheckbox > label,
    .stCheckbox label span {
        color: #cbd5e1 !important;
    }

    /* INPUTS */
    .stTextInput input,
    [data-testid="stDateInput"] input {
        background: #1f2937 !important;
        color: #f1f5f9 !important;
        border-color: #374151 !important;
    }

    .stSelectbox [data-baseweb="select"] > div:first-child {
        background: #1f2937 !important;
        color: #f1f5f9 !important;
        border-color: #374151 !important;
    }

    /* CONTAINERS WITH BORDER */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #111827 !important;
        border-color: #1f2937 !important;
    }

    /* SIDEBAR DARK */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1f1e 0%, #0b1a19 100%) !important;
        border-color: #1e3d3a !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        color: #d1d5db !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(38,166,154,0.15) !important;
        color: #26a69a !important;
    }

    .sb-section-label { color: #4b5563 !important; }

    .sb-divider {
        background: linear-gradient(90deg, #1e3d3a, transparent) !important;
    }

    /* CUSTOM CARDS DARK */
    .result-card,
    .saved-card {
        background: #111827 !important;
        border-color: #1f2937 !important;
    }

    .filter-panel {
        background: #0f1b2d !important;
        border-color: #1f2937 !important;
    }

    .filter-panel-title { color: #f1f5f9 !important; }

    .search-card {
        background: #111827 !important;
        border-color: #1f2937 !important;
    }

    .route-tile {
        background: #111827 !important;
        border-color: #1f2937 !important;
    }

    .route-tile-title { color: #f1f5f9 !important; }

    .highlight-card.cheap {
        background: linear-gradient(135deg, #052e16, #14532d) !important;
    }

    .highlight-card.fast {
        background: linear-gradient(135deg, #0c1a3d, #1e3a6e) !important;
    }

    .stat-card {
        background: #111827 !important;
        border-color: #1f2937 !important;
    }

    /* CHECKBOXES */
    .stCheckbox > label { color: #d1d5db !important; }

    /* DATAFRAME */
    [data-testid="stDataFrame"] th {
        background: #1f2937 !important;
        color: #f1f5f9 !important;
    }

    [data-testid="stDataFrame"] td {
        color: #d1d5db !important;
    }

    </style>
    """, unsafe_allow_html=True)
