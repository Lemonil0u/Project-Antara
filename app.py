"""
app.py — ANTARA Project
========================
Entry point utama Streamlit.

TODO (Lunaraya):
  - Implementasi semua halaman sesuai SDD:
    Landing, Login, Sign-Up, Search Results,
    Visualization, Saved Routes, Settings, Loading Page
  - Sambungkan ke optimizer dan database
  - Implementasi sidebar navbar

Cara menjalankan:
    streamlit run app.py
"""

import streamlit as st
from engine.optimizer import SmartRouteOptimizer
from models import SearchCriteria

# ── Konfigurasi halaman ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="ANTARA — Multi-Modal Travel",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inisialisasi optimizer (pakai DummyData sampai scraper jadi) ──────────────
@st.cache_resource
def get_optimizer():
    return SmartRouteOptimizer()

optimizer = get_optimizer()


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ✈️ ANTARA")
    st.markdown("---")

    page = st.radio(
        label="Navigasi",
        options=["🏠 Home", "🔍 Search", "📊 Visualization", "⭐ Saved Routes", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("👤 Profile")
    if st.button("🚪 Logout"):
        st.info("Logout belum diimplementasi.")


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTING HALAMAN
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    _render_home()

elif page == "🔍 Search":
    _render_search()

elif page == "📊 Visualization":
    _render_visualization()

elif page == "⭐ Saved Routes":
    _render_saved_routes()

elif page == "⚙️ Settings":
    _render_settings()


# ══════════════════════════════════════════════════════════════════════════════
#  PLACEHOLDER FUNCTIONS — TODO: implementasi tiap halaman
# ══════════════════════════════════════════════════════════════════════════════

def _render_home():
    """
    TODO (Lunaraya): Implementasi Landing/Home Page
    Komponen: Hero section, search form, popular routes, recommendation cards
    """
    st.title("Selamat Datang di ANTARA ✈️🚂🚌")
    st.markdown(
        "Platform perbandingan harga tiket **multi-modal** terlengkap di Indonesia."
    )
    st.info("🔧 Halaman Home sedang dalam pengembangan.")

    # ── Demo: Search form sederhana ──────────────────────────────────────────
    st.markdown("### Cari Perjalanan")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        origin = st.selectbox("Dari", ["Jakarta", "Bandung", "Surabaya", "Yogyakarta", "Bali"])
    with col2:
        destination = st.selectbox("Ke", ["Surabaya", "Bali", "Yogyakarta", "Medan", "Jakarta"])
    with col3:
        date = st.date_input("Tanggal")
    with col4:
        passengers = st.number_input("Penumpang", min_value=1, max_value=9, value=1)

    if st.button("🔍 Cari Tiket", type="primary"):
        # Simpan ke session state supaya halaman Search bisa ambil hasilnya
        st.session_state["search_criteria"] = {
            "origin": origin,
            "destination": destination,
            "date": str(date),
            "passengers": passengers,
        }
        st.success("Hasil pencarian tersedia di tab 🔍 Search!")


def _render_search():
    """
    TODO (Lunaraya): Implementasi Search Results Page
    Komponen: Filter sidebar, recommendation cards (Cheapest & Fastest),
              scatter plot, results table, action buttons
    """
    st.title("🔍 Hasil Pencarian")

    # Ambil kriteria dari session state (dikirim dari Home) atau pakai default
    sc = st.session_state.get("search_criteria", {
        "origin": "Jakarta", "destination": "Surabaya",
        "date": "2026-05-10", "passengers": 1,
    })

    criteria = SearchCriteria(
        origin          = sc["origin"],
        destination     = sc["destination"],
        departure_date  = sc["date"],
        passengers      = sc["passengers"],
    )

    with st.spinner("⏳ Mencari rute terbaik..."):
        result = optimizer.optimize(criteria)

    # ── Summary ──────────────────────────────────────────────────────────────
    st.code(result.summary())

    # ── Recommendation cards ─────────────────────────────────────────────────
    col_cheap, col_fast = st.columns(2)
    with col_cheap:
        st.markdown("### 💰 Rute Terhemat")
        if result.cheapest:
            st.metric("Total Harga", result.cheapest.total_price_str)
            st.metric("Durasi", result.cheapest.total_duration_str)
            st.caption(result.cheapest.mode_label + "  " + result.cheapest.route_label)

    with col_fast:
        st.markdown("### ⚡ Rute Tercepat")
        if result.fastest:
            st.metric("Total Harga", result.fastest.total_price_str)
            st.metric("Durasi", result.fastest.total_duration_str)
            st.caption(result.fastest.mode_label + "  " + result.fastest.route_label)

    # ── Tabel hasil ──────────────────────────────────────────────────────────
    st.markdown("### Semua Opsi")
    rows = []
    for c in result.all_combos:
        rows.append({
            "ID"       : c.id,
            "Rute"     : c.route_label,
            "Moda"     : c.mode_label,
            "Harga"    : c.total_price_str,
            "Durasi"   : c.total_duration_str,
            "Transfer" : f"{c.waiting_time_minutes}m",
            "Rating"   : c.average_rating or "-",
            "Badge"    : " ".join(c.badges),
        })
    st.dataframe(rows, use_container_width=True)

    # Simpan result ke session state untuk Visualization page
    st.session_state["optimizer_result"] = result


def _render_visualization():
    """
    TODO (Umarwa / Lunaraya): Implementasi Visualization Page
    Komponen: Scatter plot (Price vs Duration), Price Trend Chart,
              Transport Mode Breakdown bar chart
    Gunakan engine/visualizer.py untuk build chart Plotly-nya.
    """
    st.title("📊 Visualisasi")

    if "optimizer_result" not in st.session_state:
        st.warning("📭 Belum ada data. Lakukan pencarian di halaman 🔍 Search terlebih dahulu.")
        return

    result = st.session_state["optimizer_result"]

    # TODO: Ganti st.info di bawah ini dengan chart Plotly dari visualizer.py
    st.info("🔧 Chart Plotly akan diimplementasi di engine/visualizer.py")
    st.markdown(f"**Data tersedia:** {result.total_options} rute untuk {result.criteria.origin} → {result.criteria.destination}")


def _render_saved_routes():
    """
    TODO (Umarwa): Implementasi Saved Routes Page (CRUD)
    Komponen: Search/filter, list card, View / Delete / Star buttons
    Gunakan database.py untuk operasi CRUD ke SQLite.
    """
    st.title("⭐ Saved Routes")
    st.info("🔧 Fitur ini membutuhkan implementasi database.py (SQLite CRUD).")


def _render_settings():
    """
    TODO (Lunaraya): Implementasi Settings Page
    Komponen: Account management, Language/Currency, Dark mode, Notifications
    """
    st.title("⚙️ Settings")
    st.info("🔧 Halaman Settings sedang dalam pengembangan.")
