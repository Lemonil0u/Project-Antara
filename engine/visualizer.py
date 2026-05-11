"""
engine/visualizer.py — ANTARA Project
=====================================
Builder semua chart Plotly yang dipakai di app.py.

Modul ini hanya MEMBANGUN go.Figure — render ke layar dilakukan di app.py
via st.plotly_chart(fig, use_container_width=True).

Setiap fungsi:
  - Menerima List[RouteCombo].
  - Return go.Figure siap render.
  - Aman terhadap list kosong (return Figure kosong dengan annotation).
"""

from collections import Counter, defaultdict
from typing import List, Optional

import plotly.express as px
import plotly.graph_objects as go

from models import RouteCombo


# ── Design system colors (sesuai SDD) ────────────────────────────────────────
COLOR_MAP = {
    "flight": "#FFC107",
    "train":  "#2196F3",
    "bus":    "#4CAF50",
    "multi":  "#9C27B0",
}
BG_COLOR    = "#FFFFFF"
PLOT_BG     = "#F9F9F9"
ACCENT_TEAL = "#17A2B8"


def _empty_figure(message: str) -> go.Figure:
    """Figure kosong dengan annotation tengah."""
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#777"),
    )
    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor=PLOT_BG,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def _combo_main_mode(combo: RouteCombo) -> str:
    """Moda utama untuk warna marker. Multi-modal → 'multi'."""
    if len(combo.modes_used) > 1:
        return "multi"
    return combo.modes_used[0] if combo.modes_used else "train"


# ─────────────────────────────────────────────────────────────────────────────
#  1. SCATTER — Harga vs Durasi
# ─────────────────────────────────────────────────────────────────────────────

def scatter_price_vs_duration(combos: List[RouteCombo]) -> go.Figure:
    """Scatter plot: Harga (Y) vs Durasi (X), color-coded per moda."""
    if not combos:
        return _empty_figure("Tidak ada data untuk ditampilkan")

    data = []
    for c in combos:
        data.append({
            "Durasi (jam)": round(c.total_duration_minutes / 60, 2),
            "Harga (ribu)": round(c.total_price / 1000, 0),
            "Moda":         _combo_main_mode(c),
            "Rute":         c.route_label,
            "Label Moda":   c.mode_label,
            "Harga":        c.total_price_str,
            "Durasi":       c.total_duration_str,
            "Tag":          " · ".join(c.badges) if c.badges else "",
        })

    fig = px.scatter(
        data,
        x="Durasi (jam)", y="Harga (ribu)",
        color="Moda",
        color_discrete_map=COLOR_MAP,
        hover_data=["Rute", "Label Moda", "Harga", "Durasi", "Tag"],
        title="Perbandingan Harga vs Durasi Perjalanan",
    )
    fig.update_traces(marker=dict(size=10, opacity=0.8))
    fig.update_layout(
        paper_bgcolor=BG_COLOR, plot_bgcolor=PLOT_BG,
        font=dict(family="Segoe UI", size=13),
        title_font_size=16,
        legend_title_text="Moda",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  2. LINE — Tren Harga per Jam Keberangkatan
# ─────────────────────────────────────────────────────────────────────────────

def price_trend_chart(combos: List[RouteCombo]) -> go.Figure:
    """Line chart: rata-rata harga per jam keberangkatan."""
    if not combos:
        return _empty_figure("Tidak ada data untuk ditampilkan")

    hour_price = defaultdict(list)
    for c in combos:
        if c.segments:
            hour_price[c.segments[0].departure_time.hour].append(c.total_price)

    if not hour_price:
        return _empty_figure("Tidak cukup data untuk tren harga")

    hours = sorted(hour_price.keys())
    avg   = [sum(hour_price[h]) / len(hour_price[h]) for h in hours]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[f"{h:02d}:00" for h in hours],
        y=avg,
        mode="lines+markers",
        line=dict(color=ACCENT_TEAL, width=2.5),
        marker=dict(size=8),
        name="Rata-rata Harga",
        hovertemplate="Jam: %{x}<br>Harga: Rp %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Jam Keberangkatan",
        yaxis_title="Rata-rata Harga (IDR)",
        paper_bgcolor=BG_COLOR, plot_bgcolor=PLOT_BG,
        font=dict(family="Segoe UI", size=13),
        title_font_size=16,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  3. BAR — Jumlah Opsi per Moda
# ─────────────────────────────────────────────────────────────────────────────

def mode_breakdown_chart(combos: List[RouteCombo]) -> go.Figure:
    """Bar chart: jumlah combo per moda utama."""
    if not combos:
        return _empty_figure("Tidak ada data untuk ditampilkan")

    mode_count: Counter = Counter()
    for c in combos:
        mode_count[_combo_main_mode(c)] += 1

    if not mode_count:
        return _empty_figure("Tidak ada data moda")

    labels_map = {
        "flight": "✈️ Pesawat", "train": "🚂 Kereta",
        "bus":    "🚌 Bus",     "multi": "🔀 Multi-Modal",
    }
    modes  = list(mode_count.keys())
    counts = [mode_count[m] for m in modes]
    colors = [COLOR_MAP.get(m, "#888") for m in modes]
    labels = [labels_map.get(m, m) for m in modes]

    fig = go.Figure(go.Bar(
        x=labels, y=counts, marker_color=colors,
        text=counts, textposition="auto",
    ))
    fig.update_layout(
        xaxis_title="Moda Transportasi",
        yaxis_title="Jumlah Opsi",
        paper_bgcolor=BG_COLOR, plot_bgcolor=PLOT_BG,
        font=dict(family="Segoe UI", size=13),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  4. RECOMMENDATION CARDS DATA — Untuk di-render manual sebagai HTML card
# ─────────────────────────────────────────────────────────────────────────────

def recommendation_cards_data(
    cheapest: Optional[RouteCombo],
    fastest: Optional[RouteCombo],
) -> dict:
    """Siapkan data untuk card 'Rute Terhemat' & 'Rute Tercepat'."""
    def _card(combo: Optional[RouteCombo]) -> Optional[dict]:
        if combo is None:
            return None
        return {
            "harga":    combo.total_price_str,
            "durasi":   combo.total_duration_str,
            "rute":     combo.route_label,
            "moda":     combo.mode_label,
            "segments": [str(s) for s in combo.segments],
        }

    return {"cheapest": _card(cheapest), "fastest": _card(fastest)}
