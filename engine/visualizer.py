"""
engine/visualizer.py — ANTARA Project
=======================================
Builder untuk semua chart Plotly yang ditampilkan di Streamlit.

TODO (Umarwa / Lunaraya):
  1. Implementasi setiap fungsi chart di bawah
  2. Gunakan Plotly Express (px) atau Plotly Graph Objects (go)
  3. Warna harus sesuai design system:
       Flight  → "#FFC107" (kuning)
       Train   → "#2196F3" (biru)
       Bus     → "#4CAF50" (hijau)
  4. Setiap fungsi menerima List[RouteCombo] dan return go.Figure
  5. Figure langsung di-render di app.py via st.plotly_chart(fig)
"""

from typing import List, Optional
import plotly.graph_objects as go
import plotly.express as px

from models import RouteCombo

# ── Design System Colors ──────────────────────────────────────────────────────
COLOR_MAP = {
    "flight": "#FFC107",   # Kuning — sesuai SDD
    "train":  "#2196F3",   # Biru
    "bus":    "#4CAF50",   # Hijau
    "multi":  "#9C27B0",   # Ungu — multi-modal
}

BG_COLOR    = "#F5F5F5"
ACCENT_TEAL = "#17A2B8"


def scatter_price_vs_duration(combos: List[RouteCombo]) -> go.Figure:
    """
    Scatter plot: Harga (Y) vs Durasi (X), color-coded per moda.
    Titik cheapest dan fastest diberi marker khusus.

    TODO: Implementasi ini.

    Panduan:
      - X axis : total_duration_minutes (dalam jam untuk label yang lebih bersih)
      - Y axis : total_price (dalam ribuan IDR)
      - Color  : berdasarkan mode utama (pakai combos[0].modes_used[0])
      - Hover  : tampilkan route_label, mode_label, harga, durasi
      - Highlight cheapest dengan bintang ★, fastest dengan kilat ⚡

    Returns:
        go.Figure siap dirender di Streamlit.
    """
    # TODO: Implementasi
    raise NotImplementedError("TODO: implementasi scatter_price_vs_duration()")

    # ── Template ──────────────────────────────────────────────────────────────
    # data = []
    # for c in combos:
    #     main_mode = c.modes_used[0] if c.modes_used else "multi"
    #     data.append({
    #         "Durasi (jam)"   : round(c.total_duration_minutes / 60, 1),
    #         "Harga (ribu)"   : c.total_price / 1000,
    #         "Moda"           : main_mode,
    #         "Rute"           : c.route_label,
    #         "Label"          : c.mode_label,
    #         "Cheapest"       : c.is_cheapest,
    #         "Fastest"        : c.is_fastest,
    #     })
    #
    # fig = px.scatter(
    #     data,
    #     x="Durasi (jam)", y="Harga (ribu)",
    #     color="Moda", color_discrete_map=COLOR_MAP,
    #     hover_data=["Rute", "Label"],
    #     title="Perbandingan Harga vs Durasi",
    # )
    # fig.update_layout(paper_bgcolor=BG_COLOR)
    # return fig


def price_trend_chart(combos: List[RouteCombo]) -> go.Figure:
    """
    Line chart: tren harga per jam keberangkatan.
    Berguna untuk menunjukkan jam berapa harga paling murah.

    TODO: Implementasi ini.

    Panduan:
      - X axis : jam keberangkatan (departure_time.hour)
      - Y axis : harga
      - Group  : per moda (3 garis berbeda)
    """
    raise NotImplementedError("TODO: implementasi price_trend_chart()")


def mode_breakdown_chart(combos: List[RouteCombo]) -> go.Figure:
    """
    Bar chart: jumlah opsi tersedia per moda transportasi.
    Menampilkan seberapa banyak pilihan Flight vs Train vs Bus.

    TODO: Implementasi ini.

    Panduan:
      - X axis : moda ("flight", "train", "bus")
      - Y axis : jumlah combo yang menggunakan moda ini
      - Color  : sesuai COLOR_MAP
    """
    raise NotImplementedError("TODO: implementasi mode_breakdown_chart()")


def recommendation_cards_data(
    cheapest: Optional[RouteCombo],
    fastest: Optional[RouteCombo],
) -> dict:
    """
    Siapkan data untuk card "Rute Terhemat" dan "Rute Tercepat" di Streamlit.

    TODO: Sesuaikan format output dengan kebutuhan app.py.

    Returns:
        dict dengan key "cheapest" dan "fastest", masing-masing berisi
        dict yang siap dirender sebagai st.metric() atau card HTML.
    """
    def _card(combo: Optional[RouteCombo]) -> Optional[dict]:
        if combo is None:
            return None
        return {
            "harga"   : combo.total_price_str,
            "durasi"  : combo.total_duration_str,
            "rute"    : combo.route_label,
            "moda"    : combo.mode_label,
            "segments": [str(s) for s in combo.segments],
        }

    return {
        "cheapest": _card(cheapest),
        "fastest" : _card(fastest),
    }
