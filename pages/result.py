import streamlit as st
from pages.components.sidebar import render_sidebar
import streamlit.components.v1 as components
from pages.components.theme import apply_theme

st.set_page_config(page_title="Route Detail", layout="wide")

# =======================
# LOAD CSS
# =======================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# =======================
# GET SESSION DATA
# =======================
route = st.session_state.get("selected_route")
from_city = st.session_state.get("selected_from")
to_city = st.session_state.get("selected_to")

# =======================
# VALIDATION
# =======================
if not route:
    st.warning("Silakan pilih route terlebih dahulu.")
    st.stop()

departure, arrival = route["time"].split(" - ")

# =======================
# GOOGLE MAPS URL
# =======================
maps_url = f"""
https://www.google.com/maps?q={from_city}+to+{to_city}&output=embed
"""

# =======================
# LAYOUT
# =======================
sidebar, main = st.columns([1,4])

with sidebar:
    render_sidebar()

with main:

    # HEADER
    top1, top2 = st.columns([3,1])

    with top1:
        st.markdown(
            "<h2 style='color:#26a69a;'>Plan your Perfect Journey</h2>",
            unsafe_allow_html=True
        )

    with top2:
        st.button("⭐ Save Route", use_container_width=True)

    st.markdown("")

    if st.button("← Back to Recommended Routes"):
        st.switch_page("pages/dashboard.py")

    st.title(f"{from_city} → {to_city}")

    st.markdown("")

    # =======================
    # CONTENT
    # =======================
    left, right = st.columns([3,1.2])

    # =====================================================
    # LEFT
    # =====================================================
    with left:

        # GOOGLE MAPS
        components.iframe(
            maps_url,
            height=450,
            scrolling=False
        )

        st.markdown("")

        # ABOUT CARD
        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.caption("Total Duration")
                st.subheader(route["duration"])

            with c2:
                st.caption("Distance")
                st.subheader(route.get("distance", "-"))

            with c3:
                st.caption("Departure")
                st.subheader(departure)

            with c4:
                st.caption("Arrival")
                st.subheader(arrival)

            st.divider()

            st.subheader("About This Route")

            st.write(route.get("about", "No route description available."))

    # =====================================================
    # RIGHT
    # =====================================================
    with right:

        # SELECTED CARD
        with st.container(border=True):

            st.markdown(f"### {route['type']}")
            st.subheader(route["name"])

            st.caption(
                f"{route['time']} • {route['duration']}"
            )

            st.markdown(f"⭐ {route['rating']}")

            st.subheader(route["price"])

            st.button(
                "Selected",
                use_container_width=True,
                disabled=True
            )

        st.markdown("")

        # ROUTE DETAILS
        with st.container(border=True):

            st.subheader("Route Details")

            for i, stop in enumerate(route.get("route_details", [])):

                if i == 0:
                    st.markdown(f"📍 **{stop}** — {departure}")

                elif i == len(route["route_details"]) - 1:
                    st.markdown(f"📍 **{stop}** — {arrival}")

                else:
                    st.markdown(f"🟢 {stop}")

        st.markdown("")

        # AMENITIES
        with st.container(border=True):

            st.subheader("Amenities")

            cols = st.columns(2)

            for i, amenity in enumerate(route.get("amenities", [])):

                with cols[i % 2]:
                    st.markdown(f"✅ {amenity}")