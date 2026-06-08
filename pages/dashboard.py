"""
pages/dashboard.py — ANTARA
=============================
Halaman utama: hero, search, popular routes, hasil pencarian.
"""

import base64
import streamlit as st
import time
import os
import json
from pages.components.sidebar import render_sidebar
from pages.components.theme import apply_theme

st.set_page_config(page_title="ANTARA — Dashboard", layout="wide")

# ── CSS & THEME ──────────────────────────────────────────────
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

apply_theme()

# ── AGGRESSIVE CSS OVERRIDE FOR FILTERS ──────────────────────
st.markdown("""
<style>
    /* 1. Ultra-High Specificity for Active States */
    div.stApp [data-testid="column"]:has(.mode-btn-bus-active) .stButton > button,
    div.stApp [data-testid="column"]:has(.mode-btn-bus-active) .stButton > button:not([kind="nothing"]) {
        background: linear-gradient(135deg, #22c55e, #16a34a) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 10px rgba(34, 197, 94, 0.35) !important;
    }
    
    div.stApp [data-testid="column"]:has(.mode-btn-train-active) .stButton > button,
    div.stApp [data-testid="column"]:has(.mode-btn-train-active) .stButton > button:not([kind="nothing"]) {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.35) !important;
    }
    
    div.stApp [data-testid="column"]:has(.mode-btn-flight-active) .stButton > button,
    div.stApp [data-testid="column"]:has(.mode-btn-flight-active) .stButton > button:not([kind="nothing"]) {
        background: linear-gradient(135deg, #f97316, #ea580c) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 10px rgba(249, 115, 22, 0.35) !important;
    }

    /* 2. Inactive State */
    div.stApp [data-testid="column"]:has(.mode-btn-inactive) .stButton > button,
    div.stApp [data-testid="column"]:has(.mode-btn-inactive) .stButton > button:not([kind="nothing"]) {
        background: #ffffff !important;
        color: #6b7280 !important;
        border: 1.5px solid #e2e8f0 !important;
        box-shadow: none !important;
    }

    /* Ensure text visibility */
    div.stApp [data-testid="column"]:has([class*="-active"]) button p {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ────────────────────────────────────────────
for key, default in [
    ("search_clicked", False),
    ("searching", False),
    ("selected_transport", ["Bus", "Train", "Flight"]),
    ("airline_filter_mode", "All Airlines"),
    ("f_garuda", True),
    ("f_lion", True),
    ("f_batik", True),
    ("f_citilink", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default

CITIES = [
    "Jakarta", "Surabaya", "Bandung", "Yogyakarta",
    "Semarang", "Medan", "Makassar", "Denpasar",
    "Palembang", "Balikpapan",
]

DEFAULT_TRANSPORT_MODES = ["Bus", "Train", "Flight"]
AIRLINE_OPTIONS = ["Garuda Indonesia", "Lion Air", "Batik Air", "Citilink"]
TRANSPORT_ICONS = {"Bus": "🚌", "Train": "🚆", "Flight": "✈️"}
TRANSPORT_COLORS = {"Bus": "#22c55e", "Train": "#3b82f6", "Flight": "#f97316"}

# ── SIDEBAR ──────────────────────────────────────────────────
render_sidebar(active="home")

# ── UTIL ─────────────────────────────────────────────────────
def get_base64_image(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def reset_dashboard_filters():
    st.session_state.airline_filter_mode = "All Airlines"
    st.session_state.f_garuda = True
    st.session_state.f_lion = True
    st.session_state.f_batik = True
    st.session_state.f_citilink = True
    st.session_state.f_price = (0, 5_000_000)
    st.session_state.selected_transport = DEFAULT_TRANSPORT_MODES.copy()


def get_route_identity(route, origin_from, origin_to):
    return (
        route.get("type", ""),
        route.get("name", ""),
        origin_from,
        origin_to,
        route.get("time", ""),
    )


def get_saved_route_ids():
    from database import DatabaseManager
    user_id = st.session_state.get("user", {}).get("id")
    rows = DatabaseManager().get_saved_routes(user_id=user_id)
    return {row["combo_id"] for row in rows}

# ── HERO ─────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 32px 0 20px;">
    <p class="page-eyebrow">ANTARA · Smart Route Finder</p>
    <h1 class="hero-title">Plan Your <span>Perfect Journey</span></h1>
    <p class="hero-subtitle">Find routes, compare transport, and travel smarter across Indonesia</p>
</div>
""", unsafe_allow_html=True)

# ── SEARCH BOX ───────────────────────────────────────────────
_, c_mid, _ = st.columns([1, 3.5, 1])

with c_mid:
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        # FIX: kalau ada hasil pencarian terakhir, default widget = rute itu
        # supaya user tidak bingung "kok widget reset?"
        _last_origin      = st.session_state.get("origin")
        _last_destination = st.session_state.get("destination")
        _default_from_idx = CITIES.index(_last_origin) if _last_origin in CITIES else 0
        _default_to_idx   = CITIES.index(_last_destination) if _last_destination in CITIES else 1

        with col1:
            from_city = st.selectbox("From", CITIES, index=_default_from_idx, key="from_dash")
        with col2:
            to_city = st.selectbox("To", CITIES, index=_default_to_idx, key="to_dash")
        with col3:
            travel_date = st.date_input("Date", key="date_dash")

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        if st.button("🔍  Search Routes", use_container_width=True, key="search_dash"):
            if from_city == to_city:
                st.warning("Kota asal dan tujuan tidak boleh sama.")
            else:
                # MERGE: arahkan ke loading.py (real scraper + progress bar)
                # sama seperti flow dari app.py
                st.session_state.origin         = from_city
                st.session_state.destination    = to_city
                st.session_state.departure_date = str(travel_date)
                st.session_state.passengers     = 1
                st.switch_page("pages/loading.py")

# ── POPULAR ROUTES ────────────────────────────────────────────
if not st.session_state.search_clicked:
    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Popular Routes</p>', unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)

    POPULAR = [
        ("assets/train.png", "Train",  "#3b82f6", "Tugu Yogyakarta Station"),
        ("assets/bus.png",   "Bus",    "#22c55e", "Blok M Bus Terminal"),
        ("assets/plane.png", "Plane",  "#f97316", "Soekarno-Hatta Airport"),
    ]

    for col, (img_path, title, color, subtitle) in zip([r1, r2, r3], POPULAR):
        with col:
            b64 = get_base64_image(img_path)
            img_html = f'<img src="data:image/png;base64,{b64}" style="width:100%; border-radius:12px;">' if b64 else ""

            st.markdown(f"""
            <div class="route-tile">
                {img_html}
                <p class="route-tile-type" style="color:{color}; margin-top:10px;">{title}</p>
                <p class="route-tile-title">{title}</p>
                <p class="route-tile-sub">{subtitle}</p>
            </div>
            """, unsafe_allow_html=True)

# ── RECOMMENDED ROUTES ────────────────────────────────────────
if not st.session_state.search_clicked:
    st.stop()

st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

# Header baris: judul + mode toggle
top_left, top_right = st.columns([2, 3])

with top_left:
    # FIX: pakai tanggal dari pencarian (session_state.departure_date),
    # bukan widget date_input yang bisa berubah-ubah
    _shown_date = st.session_state.get("departure_date", str(travel_date))
    _shown_from = st.session_state.get("origin", from_city)
    _shown_to   = st.session_state.get("destination", to_city)
    st.markdown(f"""
    <p class="section-title" style="margin-bottom:4px;">Recommended Routes</p>
    <p style="font-size:16px; font-weight:700; color:#1e2a52; margin:0;">{_shown_from} → {_shown_to}</p>
    <p style="font-size:13px; color:#94a3b8; margin:2px 0 0;">{_shown_date}</p>
    """, unsafe_allow_html=True)

with top_right:
    st.markdown('<p style="font-size:13px; font-weight:600; color:#374151; margin-bottom:8px;">Filter Mode Transportasi</p>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)

    def _toggle(mode):
        sel = st.session_state.selected_transport
        if mode in sel:
            sel.remove(mode)
        else:
            sel.append(mode)

    def _mode_btn(label, mode, col):
        is_active = mode in st.session_state.selected_transport
        wrap = f"mode-btn-{mode.lower()}-active" if is_active else "mode-btn-inactive"
        
        with col:
            # Marker div sebagai identitas kolom
            st.markdown(f'<div class="{wrap}"></div>', unsafe_allow_html=True)
            display_label = f"✅ {label}" if is_active else label # Add checkmark emoji
            if st.button(display_label, key=f"mbtn_{mode}", use_container_width=True):
                _toggle(mode)
                st.rerun()

    _mode_btn("✈️ Flight", "Flight", m1)
    _mode_btn("🚆 Train",  "Train",  m2)
    _mode_btn("🚌 Bus",    "Bus",    m3)

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# Filter + Hasil
c_filter, c_results = st.columns([1, 2.6])

# ── FILTER PANEL ──────────────────────────────────────────────
with c_filter:
    st.markdown("""
    <div class="filter-panel">
        <p class="filter-panel-title">Refine Your Search</p>
        <p class="filter-section-label">Sort By</p>
    </div>
    """, unsafe_allow_html=True)

    # FIX: Dropdown Sort - sesuai visi user pilih sendiri prioritas
    # "Cheapest" = murni harga, "Fastest" = murni durasi, "Best Value" = weighted
    sort_by = st.selectbox(
        "Sort By",
        ["Cheapest", "Fastest", "Best Value"],
        index=0,
        key="sort_mode",
        label_visibility="collapsed",
        help=(
            "Cheapest: urut harga termurah dulu (kereta sering menang). "
            "Fastest: urut durasi tercepat (pesawat biasanya menang). "
            "Best Value: kombinasi 60% harga + 40% durasi."
        ),
    )

    st.markdown('<p class="filter-section-label" style="margin-top:16px;">Airlines</p>', unsafe_allow_html=True)

    st.selectbox(
        "Airline Mode",
        ["All Airlines", "Custom Selection"],
        key="airline_filter_mode",
        label_visibility="collapsed",
        help="Pilih mode dulu, lalu checkbox airlines akan muncul jika Custom Selection dipilih.",
    )

    if st.session_state.airline_filter_mode == "Custom Selection":
        st.markdown('<p class="filter-section-label" style="margin-top:10px; padding:10px;">Choose Airlines</p>', unsafe_allow_html=True)
        st.checkbox("Garuda Indonesia", key="f_garuda")
        st.checkbox("Lion Air", key="f_lion")
        st.checkbox("Batik Air", key="f_batik")
        st.checkbox("Citilink", key="f_citilink")

    st.markdown('<p class="filter-section-label" style="margin-top:16px;">Price Range</p>', unsafe_allow_html=True)

    price_max = 5_000_000
    # FIX: tambah step=50_000 supaya slider naik per Rp 50.000, bukan per Rp 1
    price_range = st.slider(
        "Price", 0, price_max, (0, price_max),
        step=50_000,
        format="Rp %d",
        label_visibility="collapsed",
        key="f_price"
    )

    is_transport_filtered = set(st.session_state.selected_transport) != set(DEFAULT_TRANSPORT_MODES)
    is_airline_filtered = st.session_state.airline_filter_mode != "All Airlines"
    is_price_filtered = price_range != (0, price_max)
    is_filter_used = is_transport_filtered or is_airline_filtered or is_price_filtered

    if is_filter_used:
        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
        st.button(
            "Reset Filter",
            use_container_width=True,
            type="secondary",
            key="f_reset",
            on_click=reset_dashboard_filters,
        )

# ── HASIL ─────────────────────────────────────────────────────
with c_results:

    # MERGE: ganti dummy data dengan hasil optimizer nyata
    # Ambil dari session_state["optimizer_result"] yang diisi oleh loading.py
    result = st.session_state.get("optimizer_result")
    TRANSPORT_DATA = []

    if result and result.total_options > 0:
        for combo in result.all_combos:
            # Tentukan tipe transport dari moda utama
            if combo.modes_used:
                mode = combo.modes_used[0]
                if mode == "flight":
                    t_type = "Flight"
                elif mode == "train":
                    t_type = "Train"
                else:
                    t_type = "Bus"
            else:
                t_type = "Train"

            first_seg = combo.segments[0]
            last_seg  = combo.segments[-1]

            # Bangun route_details dari nama-nama kota di segmen
            route_cities = [first_seg.origin] + [s.destination for s in combo.segments]
            route_details = route_cities

            # Auto-generate amenities berdasarkan moda
            if t_type == "Flight":
                amenities = ["Bagasi 20kg", "Snack/Minuman", "AC", "Entertainment", "USB Charging"]
            elif t_type == "Train":
                amenities = ["AC", "Kursi Recliner", "Restorasi", "Toilet", "Stop Kontak"]
            else:
                amenities = ["AC", "Reclining Seat", "Toilet", "Hiburan"]

            TRANSPORT_DATA.append({
                "combo_id":         combo.id,  # FIX: tambah ID unik dari combo
                "type":             t_type,
                "name":             combo.mode_label + " " + first_seg.provider,
                "time":             f"{first_seg.departure_time.strftime('%H:%M')} - {last_seg.arrival_time.strftime('%H:%M')}",
                "duration":         combo.total_duration_str,
                "duration_minutes": combo.total_duration_minutes,  # FIX: numeric untuk sort
                "price":            combo.total_price_str,
                "price_raw":        combo.total_price,
                "rating":           str(combo.average_rating) if combo.average_rating else "4.5",
                "route_details":    route_details,
                "amenities":     amenities,
                "about":         f"Perjalanan dari {first_seg.origin} ke {last_seg.destination} menggunakan {first_seg.provider}. Total durasi {combo.total_duration_str}.",
            })
    else:
        # Fallback: tidak ada hasil scraping
        st.info("Tidak ada hasil ditemukan untuk rute ini. Coba ubah kota atau tanggal.")
        st.stop()

    # --- LOGIKA FILTER AIRLINES ---
    if st.session_state.airline_filter_mode == "Custom Selection":
        selected_airlines = []
        if st.session_state.get("f_garuda"):
            selected_airlines.append("Garuda Indonesia")
        if st.session_state.get("f_lion"):
            selected_airlines.append("Lion Air")
        if st.session_state.get("f_batik"):
            selected_airlines.append("Batik Air")
        if st.session_state.get("f_citilink"):
            selected_airlines.append("Citilink")
        all_airlines_selected = set(selected_airlines) == set(AIRLINE_OPTIONS)
    else:
        selected_airlines = AIRLINE_OPTIONS
        all_airlines_selected = True

    st.session_state.selected_airlines = selected_airlines

    filtered = [
        i for i in TRANSPORT_DATA
        if i["type"] in st.session_state.selected_transport
        and price_range[0] <= i["price_raw"] <= price_range[1]
        and (
            i["type"] != "Flight" or 
            all_airlines_selected or 
            i["name"] in selected_airlines
        )
    ]

    # FIX: Sortir berdasarkan pilihan user di dropdown "Sort By"
    # - Cheapest: harga termurah dulu
    # - Fastest:  durasi tercepat (pakai duration_minutes numeric, bukan string)
    # - Best Value: weighted score 60% harga + 40% durasi (sama dengan optimizer)
    sort_mode = st.session_state.get("sort_mode", "Cheapest")
    if filtered:
        if sort_mode == "Cheapest":
            filtered.sort(key=lambda x: x["price_raw"])
        elif sort_mode == "Fastest":
            filtered.sort(key=lambda x: x["duration_minutes"])
        else:  # Best Value
            prices = [x["price_raw"] for x in filtered]
            durations = [x["duration_minutes"] for x in filtered]
            min_p, max_p = min(prices), max(prices)
            min_d, max_d = min(durations), max(durations)
            def _score(x):
                pr = (x["price_raw"] - min_p) / (max_p - min_p) if max_p != min_p else 0
                dr = (x["duration_minutes"] - min_d) / (max_d - min_d) if max_d != min_d else 0
                return 0.6 * pr + 0.4 * dr
            filtered.sort(key=_score)

    if filtered:
        # FIX: pakai duration_minutes (numeric), bukan duration string yang sort-nya salah
        cheapest = min(filtered, key=lambda x: x["price_raw"])
        fastest  = min(filtered, key=lambda x: x["duration_minutes"])

        hc1, hc2 = st.columns(2)
        with hc1:
            st.markdown(f"""
            <div class="highlight-card cheap">
                <p class="highlight-label">💸 Cheapest</p>
                <p class="highlight-value">{cheapest['price']}</p>
                <p class="highlight-desc">{cheapest['name']}</p>
            </div>
            """, unsafe_allow_html=True)
        with hc2:
            st.markdown(f"""
            <div class="highlight-card fast">
                <p class="highlight-label">⚡ Fastest</p>
                <p class="highlight-value">{fastest['duration']}</p>
                <p class="highlight-desc">{fastest['name']}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    COLOR_MAP = TRANSPORT_COLORS
    saved_route_ids = get_saved_route_ids()

    if not filtered:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <p class="empty-state-title">Tidak ada hasil</p>
            <p class="empty-state-sub">Coba ubah filter atau mode transportasi</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, item in enumerate(filtered):
            color = COLOR_MAP.get(item["type"], "#26a69a")
            is_saved = json.dumps(get_route_identity(item, from_city, to_city)) in saved_route_ids
            saved_badge = '<span style="color:#f59e0b; font-size:16px; margin-left:8px;">★</span>' if is_saved else ""

            card_col, btn_col = st.columns([5, 1])

            with card_col:
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <p class="result-card-badge" style="color:{color};">{item['type']}</p>
                        <p class="result-card-name">{item['name']}{saved_badge}</p>
                        <p class="result-card-meta">{item['time']} &nbsp;·&nbsp; {item['duration']}</p>
                        <p class="result-card-rating">⭐ {item['rating']}</p>
                    </div>
                    <div class="result-card-price">{item['price']}</div>
                </div>
                """, unsafe_allow_html=True)

            with btn_col:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                # FIX: key unik pakai combo_id (dari optimizer) + index sebagai safety net
                # Sebelumnya pakai f"sel_{item['name']}" yang bisa duplicate kalau
                # ada 2 combo dengan nama provider sama (e.g. 2 flight Citilink)
                _unique_key = f"sel_{item.get('combo_id', 'unknown')}_{idx}"
                if st.button("Select", key=_unique_key, use_container_width=True):
                    st.session_state.selected_route  = item
                    st.session_state.selected_from   = from_city
                    st.session_state.selected_to     = to_city
                    st.session_state.selected_date   = str(travel_date)
                    st.session_state.route_origin_page = "pages/dashboard.py"
                    st.session_state.route_origin_label = "Results"
                    if os.path.exists("pages/result.py"):
                        st.switch_page("pages/result.py")