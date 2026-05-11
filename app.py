"""
app.py — ANTARA Project
========================
Entry point utama Streamlit. Semua halaman ada di sini.

Cara menjalankan:
    streamlit run app.py
"""

import json
import sqlite3
from datetime import date, datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database.database import DatabaseManager
from engine.data_source import MultiModalDataSource
from engine.optimizer import SmartRouteOptimizer
from models import RouteCombo, SearchCriteria

# ══════════════════════════════════════════════════════════════════════════════
#  KONFIGURASI HALAMAN
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ANTARA — Multi-Modal Travel",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system sesuai SDD ──────────────────────────────────────────────────
# Primary Teal  : #17A2B8
# Secondary Org : #FF8C42
# Flight Yellow : #FFC107
# Train Blue    : #2196F3
# Bus Green     : #4CAF50
# Background    : #F5F5F5
# Text Dark     : #333333

st.markdown("""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #F5F5F5;
    color: #333333;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E0E0E0;
}
[data-testid="stSidebar"] .stRadio > label {
    display: none;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    gap: 0;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 4px;
    transition: background 0.2s;
    font-size: 15px;
    cursor: pointer;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    background-color: #F0F9FB;
    color: #17A2B8;
}

/* ── Cards ── */
.antara-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 16px;
}
.antara-card-orange {
    background: linear-gradient(135deg, #FF8C42 0%, #FF6B00 100%);
    color: white;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.antara-card-teal {
    background: linear-gradient(135deg, #17A2B8 0%, #0d7a8a 100%);
    color: white;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

/* ── Badge ── */
.badge-cheapest {
    background: #FF8C42;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-fastest {
    background: #17A2B8;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-multi {
    background: #9C27B0;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

/* ── Section header ── */
.section-title {
    font-size: 22px;
    font-weight: 700;
    color: #17A2B8;
    margin-bottom: 4px;
}
.section-subtitle {
    font-size: 14px;
    color: #777;
    margin-bottom: 20px;
}

/* ── Metric override ── */
[data-testid="stMetric"] {
    background: #fff;
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Buttons ── */
.stButton > button {
    background-color: #17A2B8;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 600;
    transition: background 0.2s;
}
.stButton > button:hover {
    background-color: #138a9e;
    color: white;
}

/* ── Saved route card ── */
.saved-card {
    background: white;
    border-radius: 10px;
    padding: 16px 20px;
    border-left: 4px solid #17A2B8;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ── Loading animation ── */
@keyframes fly {
    0%   { transform: translateX(-60px); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateX(calc(100vw + 60px)); opacity: 0; }
}
.plane-anim {
    font-size: 28px;
    display: inline-block;
    animation: fly 2.5s ease-in-out infinite;
}

/* ── Divider ── */
hr { border-color: #E8E8E8; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  INISIALISASI RESOURCES (cached agar tidak re-init setiap render)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_optimizer():
    data_source = MultiModalDataSource(
        headless=True,
        timeout=30,
        enabled_modes=["train", "flight"],
    )
    return SmartRouteOptimizer(data_source=data_source)

@st.cache_resource
def get_db():
    return DatabaseManager()

optimizer = get_optimizer()
db        = get_db()

# Kota yang tersedia untuk kereta
KOTA_TERSEDIA = [
    "Jakarta", "Bandung", "Yogyakarta", "Semarang",
    "Surabaya", "Solo", "Malang", "Cirebon", "Purwokerto",
]

COLOR_MAP = {
    "flight": "#FFC107",
    "train":  "#2196F3",
    "bus":    "#4CAF50",
    "multi":  "#9C27B0",
}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _run_search(origin: str, destination: str, date_str: str, passengers: int):
    """
    Jalanin pencarian, simpan hasilnya ke session_state.
    Dipanggil dari Home dan Search page.
    """
    criteria = SearchCriteria(
        origin         = origin,
        destination    = destination,
        departure_date = date_str,
        passengers     = passengers,
    )
    with st.spinner(""):
        # Tampilkan loading animation selama scraping
        loading_slot = st.empty()
        loading_slot.markdown("""
        <div style="text-align:center; padding: 40px 0;">
            <div style="overflow:hidden; width:100%; position:relative; height:50px;">
                <span class="plane-anim">✈️</span>
            </div>
            <p style="color:#17A2B8; font-size:18px; font-weight:600; margin-top:16px;">
                Mengumpulkan data tiket...
            </p>
            <p style="color:#999; font-size:13px;">
                Scraping dari Traveloka, mohon tunggu sebentar
            </p>
        </div>
        """, unsafe_allow_html=True)

        result = optimizer.optimize(criteria)
        loading_slot.empty()

    st.session_state["search_criteria"] = {
        "origin":      origin,
        "destination": destination,
        "date":        date_str,
        "passengers":  passengers,
    }
    st.session_state["optimizer_result"] = result

    # Simpan ke recent searches (database)
    try:
        cheapest_json = {}
        if result.cheapest:
            cheapest_json = {
                "route":    result.cheapest.route_label,
                "price":    result.cheapest.total_price_str,
                "duration": result.cheapest.total_duration_str,
                "mode":     result.cheapest.mode_label,
            }
        db.save_result(origin, destination, date_str, cheapest_json)
    except Exception:
        pass  # Jangan crash hanya karena DB error

    return result


def _combo_main_mode(combo: RouteCombo) -> str:
    """Ambil moda utama dari sebuah RouteCombo untuk keperluan warna."""
    if len(combo.modes_used) > 1:
        return "multi"
    return combo.modes_used[0] if combo.modes_used else "train"


# ══════════════════════════════════════════════════════════════════════════════
#  HALAMAN 1: HOME
# ══════════════════════════════════════════════════════════════════════════════

def _render_home():
    # Hero
    st.markdown("""
    <div style="background: linear-gradient(135deg, #17A2B8 0%, #0d7a8a 100%);
                border-radius: 16px; padding: 36px 40px; margin-bottom: 28px; color: white;">
        <h1 style="font-size:36px; font-weight:800; margin:0;">
            Selamat Datang di ANTARA 🚉
        </h1>
        <p style="font-size:16px; margin: 8px 0 0; opacity:0.9;">
            Bandingkan harga tiket <b>kereta · bus · pesawat</b> dan temukan rute terbaik untukmu.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Form pencarian
    st.markdown('<p class="section-title">🔍 Cari Perjalanan</p>', unsafe_allow_html=True)

    with st.container():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            origin = st.selectbox("Dari", KOTA_TERSEDIA, key="home_origin")
        with col2:
            dest_options = [k for k in KOTA_TERSEDIA if k != origin]
            destination  = st.selectbox("Ke", dest_options, key="home_dest")
        with col3:
            travel_date = st.date_input(
                "Tanggal", value=date.today(), min_value=date.today(), key="home_date"
            )
        with col4:
            passengers = st.number_input(
                "Penumpang", min_value=1, max_value=9, value=1, key="home_pax"
            )

        if st.button("🔍 Cari Tiket Sekarang", use_container_width=True):
            if origin == destination:
                st.error("Kota asal dan tujuan tidak boleh sama.")
            else:
                result = _run_search(origin, destination, str(travel_date), passengers)
                if result.total_options == 0:
                    st.warning("Tidak ada tiket ditemukan untuk rute ini. Coba tanggal atau rute lain.")
                else:
                    st.success(f"✅ {result.total_options} rute ditemukan! Lihat di halaman **🔍 Search**.")

    st.markdown("---")

    # Popular routes
    st.markdown('<p class="section-title">🔥 Rute Populer</p>', unsafe_allow_html=True)
    popular = [
        ("Jakarta", "Surabaya", "🚂 Kereta tersedia"),
        ("Jakarta", "Yogyakarta", "🚂 Kereta tersedia"),
        ("Bandung", "Yogyakarta", "🚂 Kereta tersedia"),
    ]
    cols = st.columns(3)
    for i, (orig, dest, label) in enumerate(popular):
        with cols[i]:
            st.markdown(f"""
            <div class="antara-card" style="cursor:pointer; border-top: 3px solid #17A2B8;">
                <p style="font-size:18px; font-weight:700; margin:0;">{orig} → {dest}</p>
                <p style="font-size:13px; color:#777; margin:4px 0 0;">{label}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Cari {orig}→{dest}", key=f"pop_{i}", use_container_width=True):
                result = _run_search(orig, dest, str(date.today()), 1)
                if result.total_options > 0:
                    st.success(f"✅ {result.total_options} rute ditemukan! Lihat di halaman **🔍 Search**.")

    # Recent searches
    st.markdown("---")
    st.markdown('<p class="section-title">🕐 Pencarian Terakhir</p>', unsafe_allow_html=True)
    try:
        history = db.get_history(limit=5)
        if not history:
            st.info("Belum ada riwayat pencarian.")
        else:
            for h in history:
                combo_data = {}
                try:
                    combo_data = json.loads(h.get("best_route_combo_json") or "{}")
                except Exception:
                    pass
                col_a, col_b, col_c = st.columns([3, 3, 1])
                with col_a:
                    st.markdown(f"**{h['origin']} → {h['destination']}**  \n"
                                f"<span style='color:#999;font-size:12px'>{h['date']}</span>",
                                unsafe_allow_html=True)
                with col_b:
                    if combo_data.get("price"):
                        st.markdown(f"💰 {combo_data['price']}  |  ⏱ {combo_data['duration']}")
                    else:
                        st.markdown("—")
                with col_c:
                    if st.button("Ulangi", key=f"re_{h['origin']}_{h['date']}"):
                        result = _run_search(h["origin"], h["destination"], h["date"], 1)
                        if result.total_options > 0:
                            st.success(f"✅ {result.total_options} rute ditemukan!")
                st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Tidak bisa memuat riwayat: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  HALAMAN 2: SEARCH RESULTS
# ══════════════════════════════════════════════════════════════════════════════

def _render_search():
    st.markdown('<p class="section-title">🔍 Hasil Pencarian</p>', unsafe_allow_html=True)

    # ── Panel pencarian ulang (di atas hasil) ────────────────────────────────
    sc = st.session_state.get("search_criteria", {})
    with st.expander("✏️ Ubah Pencarian", expanded=not bool(sc)):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            s_origin = st.selectbox("Dari", KOTA_TERSEDIA,
                                    index=KOTA_TERSEDIA.index(sc.get("origin", KOTA_TERSEDIA[0]))
                                          if sc.get("origin") in KOTA_TERSEDIA else 0,
                                    key="search_origin")
        with col2:
            dest_opts = [k for k in KOTA_TERSEDIA if k != s_origin]
            s_dest    = st.selectbox("Ke", dest_opts,
                                     index=dest_opts.index(sc.get("destination", dest_opts[0]))
                                           if sc.get("destination") in dest_opts else 0,
                                     key="search_dest")
        with col3:
            default_date = date.today()
            if sc.get("date"):
                try:
                    default_date = datetime.strptime(sc["date"], "%Y-%m-%d").date()
                except Exception:
                    pass
            s_date = st.date_input("Tanggal", value=default_date,
                                   min_value=date.today(), key="search_date")
        with col4:
            s_pax = st.number_input("Penumpang", min_value=1, max_value=9,
                                    value=sc.get("passengers", 1), key="search_pax")
        if st.button("🔍 Cari", key="search_cari", use_container_width=True):
            if s_origin == s_dest:
                st.error("Kota asal dan tujuan tidak boleh sama.")
            else:
                _run_search(s_origin, s_dest, str(s_date), s_pax)
                st.rerun()

    # ── Cek apakah ada hasil ─────────────────────────────────────────────────
    result = st.session_state.get("optimizer_result")
    if result is None:
        st.info("👆 Isi form di atas dan klik **Cari** untuk mulai mencari tiket.")
        return

    if result.total_options == 0:
        st.warning("😕 Tidak ada tiket ditemukan untuk rute ini.")
        return

    combos = result.all_combos
    criteria = result.criteria

    st.markdown(f'<p class="section-subtitle">{criteria.origin} → {criteria.destination} · '
                f'{criteria.departure_date} · {criteria.passengers} penumpang · '
                f'<b>{result.total_options} rute ditemukan</b></p>',
                unsafe_allow_html=True)

    # ── Sidebar filter ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎚️ Filter Hasil")

        all_modes = sorted({m for c in combos for m in c.modes_used})
        mode_labels = {"flight": "✈️ Pesawat", "train": "🚂 Kereta", "bus": "🚌 Bus"}
        selected_modes = []
        for m in all_modes:
            if st.checkbox(mode_labels.get(m, m), value=True, key=f"filter_{m}"):
                selected_modes.append(m)

        st.markdown("---")
        all_prices = [c.total_price for c in combos]
        if all_prices:
            price_min, price_max = int(min(all_prices)), int(max(all_prices))
            price_range = st.slider(
                "Rentang Harga (Rp ribu)",
                min_value=price_min // 1000,
                max_value=price_max // 1000 + 1,
                value=(price_min // 1000, price_max // 1000 + 1),
                key="filter_price",
            )
        else:
            price_range = (0, 99999)

        st.markdown("---")
        if st.button("🔄 Reset Filter", key="reset_filter"):
            st.rerun()

    # ── Terapkan filter ──────────────────────────────────────────────────────
    filtered = [
        c for c in combos
        if any(m in selected_modes for m in c.modes_used)
        and price_range[0] * 1000 <= c.total_price <= price_range[1] * 1000
    ]

    if not filtered:
        st.warning("Tidak ada hasil yang cocok dengan filter ini.")
        return

    # ── Recommendation cards ─────────────────────────────────────────────────
    st.markdown("### 🏆 Rekomendasi Terbaik")
    col_cheap, col_fast = st.columns(2)

    with col_cheap:
        cheapest = min(filtered, key=lambda c: c.total_price)
        st.markdown(f"""
        <div class="antara-card-orange">
            <p style="font-size:13px; opacity:0.9; margin:0;">💰 RUTE TERHEMAT</p>
            <p style="font-size:24px; font-weight:800; margin:4px 0;">{cheapest.total_price_str}</p>
            <p style="font-size:14px; opacity:0.95; margin:0;">{cheapest.route_label}</p>
            <p style="font-size:13px; opacity:0.8; margin:4px 0 0;">
                {cheapest.mode_label} · {cheapest.total_duration_str}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_fast:
        fastest = min(filtered, key=lambda c: c.total_duration_minutes)
        st.markdown(f"""
        <div class="antara-card-teal">
            <p style="font-size:13px; opacity:0.9; margin:0;">⚡ RUTE TERCEPAT</p>
            <p style="font-size:24px; font-weight:800; margin:4px 0;">{fastest.total_duration_str}</p>
            <p style="font-size:14px; opacity:0.95; margin:0;">{fastest.route_label}</p>
            <p style="font-size:13px; opacity:0.8; margin:4px 0 0;">
                {fastest.mode_label} · {fastest.total_price_str}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ── Scatter plot mini ────────────────────────────────────────────────────
    st.markdown("### 📊 Harga vs Durasi")
    _render_scatter(filtered)

    # ── Tabel semua hasil ────────────────────────────────────────────────────
    st.markdown("### 📋 Semua Opsi")

    # Sort control
    sort_by = st.radio("Urutkan:", ["Harga", "Durasi", "Score Terbaik"],
                       horizontal=True, key="sort_by")
    if sort_by == "Harga":
        filtered = sorted(filtered, key=lambda c: c.total_price)
    elif sort_by == "Durasi":
        filtered = sorted(filtered, key=lambda c: c.total_duration_minutes)

    for combo in filtered:
        _render_combo_card(combo, criteria.passengers)


def _render_combo_card(combo: RouteCombo, passengers: int):
    """Render satu card combo rute."""
    badges = []
    if combo.is_cheapest:
        badges.append('<span class="badge-cheapest">💰 Terhemat</span>')
    if combo.is_fastest:
        badges.append('<span class="badge-fastest">⚡ Tercepat</span>')
    if combo.is_multimodal:
        badges.append('<span class="badge-multi">🔀 Multi-Modal</span>')
    badge_html = " ".join(badges)

    segments_html = ""
    for seg in combo.segments:
        segments_html += (
            f"<span style='font-size:12px; color:#555;'>"
            f"{seg.mode_icon} <b>{seg.provider}</b> "
            f"{seg.origin}→{seg.destination} "
            f"{seg.departure_time.strftime('%H:%M')}–{seg.arrival_time.strftime('%H:%M')} "
            f"({seg.duration_str}) · {seg.price_str}/pax"
            f"</span><br>"
        )

    with st.container():
        st.markdown(f"""
        <div class="antara-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <p style="font-size:17px; font-weight:700; margin:0 0 4px;">
                        {combo.route_label}
                    </p>
                    <p style="margin:0 0 6px;">{badge_html}</p>
                    {segments_html}
                </div>
                <div style="text-align:right; min-width:120px;">
                    <p style="font-size:22px; font-weight:800; color:#FF8C42; margin:0;">
                        {combo.total_price_str}
                    </p>
                    <p style="font-size:13px; color:#777; margin:0;">
                        {combo.total_duration_str}
                    </p>
                    {'<p style="font-size:12px; color:#999;">⭐ ' + str(combo.average_rating) + '</p>'
                     if combo.average_rating else ''}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tombol save — di luar HTML agar bisa diproses Python
        col_save, _ = st.columns([1, 4])
        with col_save:
            if st.button("⭐ Simpan", key=f"save_{combo.id}"):
                _save_route(combo)


def _save_route(combo: RouteCombo):
    """Simpan rute ke saved_routes di session_state."""
    if "saved_routes" not in st.session_state:
        st.session_state["saved_routes"] = []
    existing_ids = [r["id"] for r in st.session_state["saved_routes"]]
    if combo.id in existing_ids:
        st.info("Rute ini sudah disimpan.")
        return
    st.session_state["saved_routes"].append({
        "id":       combo.id,
        "route":    combo.route_label,
        "mode":     combo.mode_label,
        "price":    combo.total_price_str,
        "price_raw": combo.total_price,
        "duration": combo.total_duration_str,
        "duration_raw": combo.total_duration_minutes,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes":    "",
        "starred":  False,
    })
    st.success("✅ Rute disimpan!")


# ══════════════════════════════════════════════════════════════════════════════
#  HALAMAN 3: VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def _render_visualization():
    st.markdown('<p class="section-title">📊 Visualisasi Data</p>', unsafe_allow_html=True)

    result = st.session_state.get("optimizer_result")
    if result is None or result.total_options == 0:
        st.markdown("""
        <div class="antara-card" style="text-align:center; padding:48px;">
            <p style="font-size:48px; margin:0;">📭</p>
            <p style="font-size:18px; font-weight:700; margin:8px 0 4px;">Belum Ada Data</p>
            <p style="color:#777;">Lakukan pencarian terlebih dahulu untuk melihat visualisasi.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    combos   = result.all_combos
    criteria = result.criteria
    st.markdown(f'<p class="section-subtitle">{criteria.origin} → {criteria.destination} · '
                f'{criteria.departure_date}</p>', unsafe_allow_html=True)

    # ── Scatter plot: Harga vs Durasi ─────────────────────────────────────────
    st.markdown("### 🎯 Scatter Plot: Harga vs Durasi")
    st.caption("Titik di kiri-bawah = tercepat sekaligus termurah (ideal)")
    _render_scatter(combos)

    st.markdown("---")

    # ── Price trend: harga per jam keberangkatan ──────────────────────────────
    st.markdown("### 📈 Tren Harga per Jam Keberangkatan")
    st.caption("Jam keberangkatan mana yang biasanya lebih murah?")
    _render_price_trend(combos)

    st.markdown("---")

    # ── Mode breakdown ────────────────────────────────────────────────────────
    st.markdown("### 🚦 Jumlah Opsi per Moda Transportasi")
    _render_mode_breakdown(combos)

    st.markdown("---")

    # ── Summary stats ─────────────────────────────────────────────────────────
    st.markdown("### 📌 Ringkasan Statistik")
    prices    = [c.total_price for c in combos]
    durations = [c.total_duration_minutes for c in combos]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Opsi",      result.total_options)
    col2.metric("Harga Terendah",  f"Rp {min(prices):,.0f}")
    col3.metric("Harga Tertinggi", f"Rp {max(prices):,.0f}")
    col4.metric("Durasi Tercepat", f"{min(durations) // 60}j {min(durations) % 60}m")


def _render_scatter(combos: list):
    data = []
    for c in combos:
        main_mode = _combo_main_mode(c)
        data.append({
            "Durasi (jam)":  round(c.total_duration_minutes / 60, 2),
            "Harga (ribu)":  round(c.total_price / 1000, 0),
            "Moda":          main_mode,
            "Rute":          c.route_label,
            "Label Moda":    c.mode_label,
            "Harga":         c.total_price_str,
            "Durasi":        c.total_duration_str,
            "Tag":           " · ".join(c.badges) if c.badges else "",
        })
    if not data:
        st.info("Tidak ada data untuk ditampilkan.")
        return
    fig = px.scatter(
        data,
        x="Durasi (jam)",
        y="Harga (ribu)",
        color="Moda",
        color_discrete_map={k: v for k, v in COLOR_MAP.items()},
        hover_data=["Rute", "Label Moda", "Harga", "Durasi", "Tag"],
        title="Perbandingan Harga vs Durasi Perjalanan",
        size_max=12,
    )
    fig.update_traces(marker=dict(size=10, opacity=0.8))
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F9F9F9",
        font=dict(family="Segoe UI", size=13),
        title_font_size=16,
        legend_title_text="Moda",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_price_trend(combos: list):
    from collections import defaultdict
    hour_price: dict = defaultdict(list)
    for c in combos:
        if c.segments:
            hour = c.segments[0].departure_time.hour
            hour_price[hour].append(c.total_price)
    if not hour_price:
        st.info("Tidak cukup data untuk tren harga.")
        return
    hours     = sorted(hour_price.keys())
    avg_price = [sum(hour_price[h]) / len(hour_price[h]) for h in hours]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[f"{h:02d}:00" for h in hours],
        y=avg_price,
        mode="lines+markers",
        line=dict(color="#17A2B8", width=2.5),
        marker=dict(size=8),
        name="Rata-rata Harga",
        hovertemplate="Jam: %{x}<br>Harga: Rp %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Jam Keberangkatan",
        yaxis_title="Rata-rata Harga (IDR)",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F9F9F9",
        font=dict(family="Segoe UI", size=13),
        title_font_size=16,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_mode_breakdown(combos: list):
    from collections import Counter
    mode_count: Counter = Counter()
    for c in combos:
        main_mode = _combo_main_mode(c)
        mode_count[main_mode] += 1
    if not mode_count:
        st.info("Tidak ada data moda.")
        return
    mode_labels = {"flight": "✈️ Pesawat", "train": "🚂 Kereta", "bus": "🚌 Bus", "multi": "🔀 Multi"}
    modes  = list(mode_count.keys())
    counts = [mode_count[m] for m in modes]
    colors = [COLOR_MAP.get(m, "#888") for m in modes]
    labels = [mode_labels.get(m, m) for m in modes]
    fig = go.Figure(go.Bar(
        x=labels,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition="auto",
    ))
    fig.update_layout(
        xaxis_title="Moda Transportasi",
        yaxis_title="Jumlah Opsi",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F9F9F9",
        font=dict(family="Segoe UI", size=13),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HALAMAN 4: SAVED ROUTES
# ══════════════════════════════════════════════════════════════════════════════

def _render_saved_routes():
    st.markdown('<p class="section-title">⭐ Saved Routes</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Rute favorit yang kamu simpan</p>',
                unsafe_allow_html=True)

    saved: list = st.session_state.get("saved_routes", [])

    if not saved:
        st.markdown("""
        <div class="antara-card" style="text-align:center; padding:48px;">
            <p style="font-size:40px; margin:0;">⭐</p>
            <p style="font-size:18px; font-weight:700; margin:8px 0 4px;">
                Belum Ada Rute Tersimpan
            </p>
            <p style="color:#777;">
                Cari tiket dulu, lalu klik <b>⭐ Simpan</b> di hasil pencarian.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Filter & sort bar
    col_filter, col_sort = st.columns([3, 1])
    with col_filter:
        keyword = st.text_input("🔍 Cari rute tersimpan...", key="saved_search", label_visibility="collapsed",
                                placeholder="Cari rute tersimpan...")
    with col_sort:
        sort_saved = st.selectbox("Urutkan", ["Terbaru", "Harga", "Durasi"],
                                  key="saved_sort", label_visibility="collapsed")

    filtered_saved = saved
    if keyword:
        filtered_saved = [r for r in saved if keyword.lower() in r["route"].lower()]

    if sort_saved == "Harga":
        filtered_saved = sorted(filtered_saved, key=lambda r: r.get("price_raw", 0))
    elif sort_saved == "Durasi":
        filtered_saved = sorted(filtered_saved, key=lambda r: r.get("duration_raw", 0))

    if not filtered_saved:
        st.info("Tidak ada rute yang cocok dengan pencarian.")
        return

    st.markdown(f"**{len(filtered_saved)} rute tersimpan**")

    for i, route in enumerate(filtered_saved):
        star_icon = "⭐" if route.get("starred") else "☆"
        with st.container():
            st.markdown(f"""
            <div class="saved-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <p style="font-size:17px; font-weight:700; margin:0;">{route['route']}</p>
                        <p style="font-size:13px; color:#777; margin:2px 0;">
                            {route['mode']} · {route['price']} · {route['duration']}
                        </p>
                        <p style="font-size:12px; color:#aaa; margin:2px 0 0;">
                            Disimpan: {route['saved_at']}
                        </p>
                    </div>
                    <p style="font-size:22px; font-weight:800; color:#FF8C42; margin:0;">
                        {route['price']}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_note, col_star, col_del = st.columns([4, 1, 1])
            with col_note:
                new_note = st.text_input(
                    "Catatan", value=route.get("notes", ""),
                    placeholder="Tambah catatan...",
                    key=f"note_{route['id']}",
                    label_visibility="collapsed",
                )
                # Update notes kalau berubah
                if new_note != route.get("notes", ""):
                    st.session_state["saved_routes"][i]["notes"] = new_note

            with col_star:
                if st.button(star_icon, key=f"star_{route['id']}"):
                    st.session_state["saved_routes"][i]["starred"] = not route.get("starred", False)
                    st.rerun()

            with col_del:
                if st.button("🗑️", key=f"del_{route['id']}"):
                    st.session_state["saved_routes"] = [
                        r for r in st.session_state["saved_routes"] if r["id"] != route["id"]
                    ]
                    st.rerun()

            st.markdown("<hr style='margin:4px 0 8px;'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HALAMAN 5: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

def _render_settings():
    st.markdown('<p class="section-title">⚙️ Settings</p>', unsafe_allow_html=True)

    if "settings" not in st.session_state:
        st.session_state["settings"] = {
            "language": "Indonesian",
            "currency": "IDR",
            "dark_mode": False,
            "price_alerts": True,
            "booking_reminders": True,
            "headless_scraper": True,
            "max_results": 20,
            "max_transits": 2,
        }

    cfg = st.session_state["settings"]

    # ── Preferences ──────────────────────────────────────────────────────────
    st.markdown("### 🌐 Preferensi")
    col1, col2 = st.columns(2)
    with col1:
        cfg["language"] = st.selectbox(
            "Bahasa", ["Indonesian", "English"], key="lang",
            index=["Indonesian", "English"].index(cfg.get("language", "Indonesian"))
        )
    with col2:
        cfg["currency"] = st.selectbox(
            "Mata Uang", ["IDR", "USD", "SGD"], key="curr",
            index=["IDR", "USD", "SGD"].index(cfg.get("currency", "IDR"))
        )

    st.markdown("---")

    # ── Notifikasi ────────────────────────────────────────────────────────────
    st.markdown("### 🔔 Notifikasi")
    cfg["price_alerts"]       = st.toggle("Notifikasi perubahan harga",   value=cfg.get("price_alerts", True))
    cfg["booking_reminders"]  = st.toggle("Pengingat pemesanan",          value=cfg.get("booking_reminders", True))

    st.markdown("---")

    # ── Scraper settings ──────────────────────────────────────────────────────
    st.markdown("### 🤖 Pengaturan Scraper")
    cfg["headless_scraper"] = st.toggle(
        "Jalankan browser tanpa tampilan (headless mode) — matikan untuk debug",
        value=cfg.get("headless_scraper", True),
    )
    cfg["max_results"] = st.slider(
        "Maksimum hasil yang ditampilkan", 5, 50, cfg.get("max_results", 20)
    )
    cfg["max_transits"] = st.slider(
        "Maksimum kota transit (0 = langsung saja)", 0, 3, cfg.get("max_transits", 2)
    )

    st.markdown("---")

    # ── Danger zone ───────────────────────────────────────────────────────────
    st.markdown("### ⚠️ Danger Zone")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Hapus Semua Rute Tersimpan", type="secondary"):
            st.session_state["saved_routes"] = []
            st.success("Semua rute tersimpan telah dihapus.")
    with col_b:
        if st.button("🧹 Bersihkan Cache Pencarian", type="secondary"):
            for key in ["search_criteria", "optimizer_result"]:
                st.session_state.pop(key, None)
            st.success("Cache pencarian dibersihkan.")

    st.markdown("---")
    if st.button("💾 Simpan Pengaturan", type="primary"):
        st.session_state["settings"] = cfg
        st.success("✅ Pengaturan berhasil disimpan!")


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 16px 0 8px;">
        <p style="font-size:28px; margin:0;">🚉</p>
        <p style="font-size:22px; font-weight:800; color:#17A2B8; margin:0;">ANTARA</p>
        <p style="font-size:11px; color:#aaa; margin:0;">Multi-Modal Travel</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        label="nav",
        options=["🏠 Home", "🔍 Search", "📊 Visualization", "⭐ Saved Routes", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Info status pencarian
    result = st.session_state.get("optimizer_result")
    if result:
        sc = st.session_state.get("search_criteria", {})
        st.markdown(f"""
        <div style="background:#F0F9FB; border-radius:8px; padding:10px 12px; font-size:12px;">
            <b>Pencarian terakhir</b><br>
            {sc.get('origin','?')} → {sc.get('destination','?')}<br>
            <span style="color:#17A2B8;">{result.total_options} rute ditemukan</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")

    saved_count = len(st.session_state.get("saved_routes", []))
    if saved_count:
        st.markdown(f"<p style='font-size:12px; color:#777;'>⭐ {saved_count} rute tersimpan</p>",
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='font-size:12px; color:#aaa; text-align:center;'>ANTARA v1.0<br>Politeknik Negeri Bandung</p>",
                unsafe_allow_html=True)


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