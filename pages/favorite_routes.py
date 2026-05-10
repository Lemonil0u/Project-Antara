import streamlit as st
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

# =======================
# PAGE CONFIG
# =======================
st.set_page_config(
    page_title="Saved Routes",
    layout="wide"
)

# =======================
# LOAD CSS
# =======================
with open("style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# =======================
# APPLY THEME
# =======================
apply_theme()

# =======================
# THEME COLORS
# =======================
is_dark = st.session_state.get("theme_mode") == "Dark"

TEXT = "white" if is_dark else "#1e2a52"
SUBTEXT = "#d1d5db" if is_dark else "#6b7280"
CARD_BG = "#111827" if is_dark else "white"

# =======================
# DATA
# =======================
saved_routes = st.session_state.get("saved_routes", [])

# =======================
# FALLBACK DATA
# =======================
if not saved_routes:

    saved_routes = [

        {
            "type": "Bus",
            "name": "Haryanto",
            "icon": "🚌",
            "from": "Jakarta",
            "to": "Bali (Denpasar)",
            "date": "20 May 2024",
            "duration": "12h",
            "rating": "4.5",
            "price": "Rp 250.000",
            "color": "#22c55e",
            "bg": "#eef9f0",
            "time": "19:00 - 07:00",
            "distance": "1,150 km",
            "amenities": [
                "AC",
                "Wi-Fi",
                "Charging Port"
            ]
        },

        {
            "type": "Train",
            "name": "Gajah Mungkur",
            "icon": "🚆",
            "from": "Jakarta",
            "to": "Bandung",
            "date": "18 May 2024",
            "duration": "3h 10m",
            "rating": "4.7",
            "price": "Rp 350.000",
            "color": "#3b82f6",
            "bg": "#eef4ff",
            "time": "08:00 - 11:10",
            "distance": "180 km",
            "amenities": [
                "AC",
                "Meal",
                "Toilet"
            ]
        },

        {
            "type": "Flight",
            "name": "Garuda Indonesia",
            "icon": "✈️",
            "from": "Jakarta",
            "to": "Bali (DPS)",
            "date": "15 May 2024",
            "duration": "2h 15m",
            "rating": "4.9",
            "price": "Rp 1.450.000",
            "color": "#f97316",
            "bg": "#fff6eb",
            "time": "09:00 - 11:15",
            "distance": "980 km",
            "amenities": [
                "Meal",
                "Cabin Bag",
                "Entertainment"
            ]
        },

        {
            "type": "Bus",
            "name": "Sinar Jaya",
            "icon": "🚌",
            "from": "Yogyakarta",
            "to": "Surabaya",
            "date": "12 May 2024",
            "duration": "5h 30m",
            "rating": "4.3",
            "price": "Rp 180.000",
            "color": "#22c55e",
            "bg": "#eef9f0",
            "time": "10:00 - 15:30",
            "distance": "320 km",
            "amenities": [
                "AC",
                "Seat",
                "Snacks"
            ]
        },

        {
            "type": "Train",
            "name": "Argo Parahyangan",
            "icon": "🚆",
            "from": "Bandung",
            "to": "Jakarta",
            "date": "10 May 2024",
            "duration": "3h",
            "rating": "4.6",
            "price": "Rp 200.000",
            "color": "#3b82f6",
            "bg": "#eef4ff",
            "time": "13:00 - 16:00",
            "distance": "180 km",
            "amenities": [
                "AC",
                "Toilet",
                "Meal"
            ]
        }

    ]

# =======================
# LAYOUT
# =======================
col_sidebar, col_main = st.columns(
    [1, 4],
    gap="large"
)

# =======================
# SIDEBAR
# =======================
with col_sidebar:
    render_sidebar()

# =======================
# MAIN CONTENT
# =======================
with col_main:

    # =======================
    # HEADER
    # =======================
    st.markdown(
        """
        <h1 style="
            color:#0f9db4;
            font-size:32px;
            margin-bottom:30px;
            font-weight:700;
        ">
            │ Plan your Perfect Journey
        </h1>
        """,
        unsafe_allow_html=True
    )

    # =======================
    # TOP SECTION
    # =======================
    left, right = st.columns([2, 2])

    with left:

        st.markdown(
            f"""
            <h2 style="
                margin-bottom:0;
                color:{TEXT};
                font-size:26px;
                font-weight:700;
            ">
                Saved Routes
            </h2>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <p style="
                color:{SUBTEXT};
                font-size:15px;
                margin-top:5px;
            ">
                Your saved routes for quick access and future planning.
            </p>
            """,
            unsafe_allow_html=True
        )

    with right:

        c1, c2 = st.columns([2.5, 1])

        with c1:
            search = st.text_input(
                "",
                placeholder="🔍 Search saved routes..."
            )

        with c2:
            sort_by = st.selectbox(
                "",
                ["Newest", "Oldest", "Cheapest"]
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # =======================
    # SEARCH
    # =======================
    if search:

        keyword = search.lower()

        saved_routes = [

            route for route in saved_routes

            if (
                keyword in route["name"].lower()
                or keyword in route["type"].lower()
                or keyword in route["from"].lower()
                or keyword in route["to"].lower()
            )
        ]

    # =======================
    # SORT
    # =======================
    if sort_by == "Newest":
        saved_routes = list(reversed(saved_routes))

    elif sort_by == "Cheapest":

        def extract_price(route):
            return int(
                route["price"]
                .replace("Rp", "")
                .replace(".", "")
                .strip()
            )

        saved_routes = sorted(
            saved_routes,
            key=extract_price
        )

    # =======================
    # ROUTE CARDS
    # =======================
    for route in saved_routes:

        with st.container(border=True):

            left, center, right = st.columns([1, 4, 1])

            # =======================
            # ICON
            # =======================
            with left:

                st.markdown(
                    f"""
                    <div style="
                        background:{route['bg']};
                        width:80px;
                        height:80px;
                        border-radius:18px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-size:38px;
                        margin-top:10px;
                    ">
                        {route['icon']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # =======================
            # CENTER INFO
            # =======================
            with center:

                st.markdown(
                    f"""
                    <div style="
                        color:{route['color']};
                        font-size:15px;
                        font-weight:700;
                        margin-top:10px;
                    ">
                        {route['type']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div style="
                        font-size:22px;
                        font-weight:700;
                        color:{TEXT};
                        margin-top:6px;
                    ">
                        {route['name']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div style="
                        color:{SUBTEXT};
                        font-size:15px;
                        margin-top:5px;
                    ">
                        {route['from']} → {route['to']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div style="
                        color:{SUBTEXT};
                        font-size:14px;
                        margin-top:10px;
                    ">
                        📅 {route['date']}
                        &nbsp;&nbsp;&nbsp;
                        ⏱ {route['duration']}
                        &nbsp;&nbsp;&nbsp;
                        ⭐ {route['rating']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # =======================
            # RIGHT
            # =======================
            with right:

                st.markdown(
                    f"""
                    <div style="
                        font-size:24px;
                        font-weight:700;
                        color:{TEXT};
                        text-align:right;
                        margin-top:10px;
                        margin-bottom:15px;
                    ">
                        {route['price']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button(
                    "View Details",
                    key=f"detail_{route['from']}_{route['to']}_{route['name']}",
                    use_container_width=True
                ):

                    st.session_state.selected_route = route

                    st.session_state.selected_from = route["from"]

                    st.session_state.selected_to = route["to"]

                    st.switch_page("pages/result.py")

                st.markdown(
                    """
                    <div style="
                        text-align:right;
                        font-size:28px;
                        color:#0f9db4;
                        margin-top:8px;
                    ">
                        ⋮
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

    # =======================
    # EMPTY STATE
    # =======================
    if len(saved_routes) == 0:

        st.info(
            "No saved routes found."
        )