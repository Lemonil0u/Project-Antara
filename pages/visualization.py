import streamlit as st
import pandas as pd
import plotly.express as px
import time
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="Visualization", layout="wide")

# =======================
# LOAD CSS
# =======================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# =======================
# STATE
# =======================
if "visual_search_clicked" not in st.session_state:
    st.session_state.visual_search_clicked = False

if "visual_searching" not in st.session_state:
    st.session_state.visual_searching = False

# =======================
# CITY DATA
# =======================
cities = [
    "Jakarta",
    "Bandung",
    "Surabaya",
    "Yogyakarta",
    "Semarang",
    "Denpasar",
    "Medan",
    "Makassar",
    "Palembang",
    "Balikpapan"
]

# =======================
# LAYOUT
# =======================
sidebar, main = st.columns([1,4])

# =======================
# SIDEBAR
# =======================
with sidebar:
    render_sidebar()

# =======================
# MAIN CONTENT
# =======================
with main:

    # =======================
    # HEADER
    # =======================
    st.markdown(
        """
        <h1 style='color:#26a69a;'>
            Transportation Visualization
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style='color:gray; font-size:18px;'>
            Compare transportation prices, duration, and ratings easily
        </p>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # =======================
    # SEARCH BOX
    # =======================
    with st.container(border=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            from_city = st.selectbox(
                "From",
                cities,
                index=0,
                key="visual_from"
            )

        with col2:
            to_city = st.selectbox(
                "To",
                cities,
                index=2,
                key="visual_to"
            )

        with col3:
            date = st.date_input(
                "Date",
                key="visual_date"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "🔍 Search Visualization",
            use_container_width=True
        ):

            if from_city == to_city:
                st.warning(
                    "Kota asal dan tujuan tidak boleh sama"
                )

            else:
                st.session_state.visual_searching = True
                st.session_state.visual_search_clicked = False
                st.rerun()

    # =======================
    # LOADING
    # =======================
    if st.session_state.visual_searching:

        st.markdown("<br><br>", unsafe_allow_html=True)

        center1, center2, center3 = st.columns([1,2,1])

        with center2:

            st.image(
                "assets/logo_antara.png",
                width=120
            )

            st.markdown(
                """
                <h2 style='text-align:center; color:#26a69a;'>
                    Generating Visualization...
                </h2>
                """,
                unsafe_allow_html=True
            )

            progress = st.progress(0)

            status = st.empty()

            messages = [
                "Collecting transportation data...",
                "Comparing ticket prices...",
                "Analyzing duration...",
                "Generating charts..."
            ]

            for i in range(100):

                progress.progress(i + 1)

                status.markdown(
                    f"""
                    <p style='text-align:center; color:gray;'>
                        {messages[(i//25)%4]}
                    </p>
                    """,
                    unsafe_allow_html=True
                )

                time.sleep(0.02)

        # =======================
        # SCRAPING RESULT (DUMMY)
        # =======================
        st.session_state.visualization_results = [

            {
                "type": "Bus",
                "name": "Haryanto",
                "duration": 12,
                "price": 250000,
                "rating": 4.5,
            },

            {
                "type": "Train",
                "name": "Gajah Mungkur",
                "duration": 10,
                "price": 350000,
                "rating": 4.7,
            },

            {
                "type": "Flight",
                "name": "Garuda Indonesia",
                "duration": 2.2,
                "price": 1450000,
                "rating": 4.9,
            },

            {
                "type": "Flight",
                "name": "Lion Air",
                "duration": 2.5,
                "price": 950000,
                "rating": 4.3,
            },
        ]

        st.session_state.visual_searching = False
        st.session_state.visual_search_clicked = True
        st.rerun()

    # =======================
    # VISUALIZATION RESULT
    # =======================
    if st.session_state.visual_search_clicked:

        transport_data = st.session_state.get(
            "visualization_results",
            []
        )

        df = pd.DataFrame(transport_data)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # =======================
        # ROUTE TITLE
        # =======================
        st.markdown(
            f"""
            <h2 style='color:#26a69a;'>
                {from_city} → {to_city}
            </h2>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <p style='color:gray;'>
                Transportation comparison analytics
            </p>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # =======================
        # SUMMARY CARDS
        # =======================
        c1, c2, c3 = st.columns(3)

        cheapest = df.loc[df["price"].idxmin()]
        fastest = df.loc[df["duration"].idxmin()]
        highest = df.loc[df["rating"].idxmax()]

        with c1:
            with st.container(border=True):

                st.caption("💸 Cheapest")

                st.subheader(
                    cheapest["name"]
                )

                st.markdown(
                    f"""
                    <h3 style='color:#26a69a;'>
                        Rp {cheapest['price']:,}
                    </h3>
                    """.replace(",", "."),
                    unsafe_allow_html=True
                )

        with c2:
            with st.container(border=True):

                st.caption("⚡ Fastest")

                st.subheader(
                    fastest["name"]
                )

                st.markdown(
                    f"""
                    <h3 style='color:#26a69a;'>
                        {fastest['duration']}h
                    </h3>
                    """,
                    unsafe_allow_html=True
                )

        with c3:
            with st.container(border=True):

                st.caption("⭐ Best Rating")

                st.subheader(
                    highest["name"]
                )

                st.markdown(
                    f"""
                    <h3 style='color:#26a69a;'>
                        {highest['rating']}
                    </h3>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("<br><br>", unsafe_allow_html=True)

        # =======================
        # CHARTS
        # =======================
        chart1, chart2 = st.columns(2)

        # =======================
        # PRICE CHART
        # =======================
        with chart1:

            with st.container(border=True):

                st.markdown(
                    """
                    <h4 style='color:#26a69a;'>
                        Price Comparison
                    </h4>
                    """,
                    unsafe_allow_html=True
                )

                fig_price = px.bar(
                    df,
                    x="name",
                    y="price",
                    color="type",
                    text_auto=True,
                    height=400,
                )

                fig_price.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                )

                st.plotly_chart(
                    fig_price,
                    use_container_width=True
                )

        # =======================
        # DURATION CHART
        # =======================
        with chart2:

            with st.container(border=True):

                st.markdown(
                    """
                    <h4 style='color:#26a69a;'>
                        Duration Comparison
                    </h4>
                    """,
                    unsafe_allow_html=True
                )

                fig_duration = px.line(
                    df,
                    x="name",
                    y="duration",
                    markers=True,
                    color="type",
                    height=400,
                )

                fig_duration.update_layout(
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                )

                st.plotly_chart(
                    fig_duration,
                    use_container_width=True
                )

        st.markdown("<br><br>", unsafe_allow_html=True)

        # =======================
        # COMPARISON TABLE
        # =======================
        with st.container(border=True):

            st.markdown(
                """
                <h4 style='color:#26a69a;'>
                    Route Comparison Table
                </h4>
                """,
                unsafe_allow_html=True
            )

            show_df = df.copy()

            show_df["price"] = show_df["price"].apply(
                lambda x: f"Rp {x:,}".replace(",", ".")
            )

            show_df.columns = [
                "Transport",
                "Provider",
                "Duration (Hour)",
                "Price",
                "Rating",
            ]

            st.dataframe(
                show_df,
                use_container_width=True,
                hide_index=True
            )