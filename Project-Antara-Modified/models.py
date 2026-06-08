"""
models.py — ANTARA Project
==========================
Definisi dataclass untuk semua entitas utama sistem.

Hierarki konseptual:
    LocalSegment       → satu kaki perjalanan lokal (first-mile / last-mile)
                         e.g. Gojek dari rumah ke Stasiun Gambir.
                         CATATAN: saat ini hanya stub — belum di-scrape nyata.
    TransportSegment   → satu kaki perjalanan antar-kota
                         (pesawat / kereta / bus). Hasil dari scraper.
    RouteCombo         → gabungan 1+ TransportSegment (opsional dibungkus
                         LocalSegment di awal/akhir).
    OptimizerResult    → hasil akhir SmartRouteOptimizer untuk 1 pencarian.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  LocalSegment  — first-mile / last-mile (STUB)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class LocalSegment:
    """
    Kaki perjalanan lokal (di dalam kota): rumah → stasiun, bandara → hotel, dll.

    STATUS: Stub. Belum di-scrape nyata. Dihasilkan oleh placeholder
    LocalSegmentGenerator di engine.local_data agar arsitektur first-/last-mile
    sudah tertanam dan siap diisi data nyata nanti.
    """
    id: str
    mode: str                        # "ride_hail" | "taxi" | "transit" | "walk"
    provider: str                    # "Gojek" | "Grab" | "TransJakarta" | "Walk"
    origin: str                      # Titik awal lokal (alamat / nama tempat)
    destination: str                 # Titik akhir lokal (biasanya stasiun/bandara)
    duration_minutes: int            # Estimasi durasi
    price: float                     # Estimasi harga (IDR)

    @property
    def duration_str(self) -> str:
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}j {m}m" if h else f"{m}m"

    @property
    def price_str(self) -> str:
        return f"Rp {self.price:,.0f}"

    @property
    def mode_icon(self) -> str:
        return {
            "ride_hail": "🛵",
            "taxi":      "🚖",
            "transit":   "🚌",
            "walk":      "🚶",
        }.get(self.mode, "🚗")


# ─────────────────────────────────────────────────────────────────────────────
#  TransportSegment  — satu "kaki" perjalanan antar-kota
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TransportSegment:
    """
    Satu segmen perjalanan utama — pesawat, kereta, atau bus.
    Setiap RouteCombo tersusun dari 1+ TransportSegment.
    """
    id: str
    mode: str                        # "flight" | "train" | "bus"
    provider: str                    # Nama maskapai / operator
    provider_code: Optional[str]     # e.g. "GA", "SJ", "KA"
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    price: float
    seat_class: Optional[str]
    available_seats: Optional[int]
    rating: Optional[float]

    # ── derived helpers ─────────────────────────────────────────────────────
    @property
    def duration_str(self) -> str:
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}j {m}m" if m else f"{h}j"

    @property
    def price_str(self) -> str:
        return f"Rp {self.price:,.0f}"

    @property
    def mode_icon(self) -> str:
        return {"flight": "✈️", "train": "🚂", "bus": "🚌"}.get(self.mode, "🚗")

    def __repr__(self) -> str:
        return (
            f"[{self.mode_icon} {self.provider}] "
            f"{self.origin}→{self.destination} "
            f"| {self.departure_time.strftime('%H:%M')}–{self.arrival_time.strftime('%H:%M')} "
            f"| {self.duration_str} | {self.price_str}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  RouteCombo  — 1 rute lengkap origin → destination
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RouteCombo:
    """
    Satu pilihan rute lengkap dari origin ke destination.
    Bisa berupa rute langsung (1 segmen) atau multi-modal (2-3 segmen).

    first_mile dan last_mile bersifat opsional — hanya terisi jika user
    mengaktifkan fitur first-/last-mile (saat ini stub).
    """
    id: str
    segments: List[TransportSegment]
    total_price: float
    total_duration_minutes: int
    waiting_time_minutes: int
    is_cheapest: bool = False
    is_fastest: bool = False
    average_rating: Optional[float] = None

    # First-/last-mile (opsional, default None)
    first_mile: Optional[LocalSegment] = None
    last_mile: Optional[LocalSegment] = None

    # ── derived helpers ─────────────────────────────────────────────────────
    @property
    def is_multimodal(self) -> bool:
        return len(self.segments) > 1

    @property
    def modes_used(self) -> List[str]:
        seen, result = set(), []
        for s in self.segments:
            if s.mode not in seen:
                seen.add(s.mode)
                result.append(s.mode)
        return result

    @property
    def mode_label(self) -> str:
        icons = [s.mode_icon for s in self.segments]
        return " + ".join(icons)

    @property
    def route_label(self) -> str:
        cities = [self.segments[0].origin] + [s.destination for s in self.segments]
        return " → ".join(cities)

    @property
    def total_duration_str(self) -> str:
        h, m = divmod(self.total_duration_minutes, 60)
        return f"{h}j {m}m" if m else f"{h}j"

    @property
    def total_price_str(self) -> str:
        return f"Rp {self.total_price:,.0f}"

    @property
    def departure_time(self) -> datetime:
        return self.segments[0].departure_time

    @property
    def arrival_time(self) -> datetime:
        return self.segments[-1].arrival_time

    @property
    def has_local_legs(self) -> bool:
        """Apakah rute ini punya first-mile atau last-mile?"""
        return self.first_mile is not None or self.last_mile is not None

    @property
    def badges(self) -> List[str]:
        b = []
        if self.is_cheapest:
            b.append("💰 Terhemat")
        if self.is_fastest:
            b.append("⚡ Tercepat")
        if self.is_multimodal:
            b.append("🔀 Multi-Modal")
        if self.has_local_legs:
            b.append("🛵 Door-to-Door")
        return b

    def __repr__(self) -> str:
        flags = " ".join(self.badges)
        return (
            f"RouteCombo [{self.id}] {self.route_label}\n"
            f"  Moda   : {self.mode_label}\n"
            f"  Harga  : {self.total_price_str}\n"
            f"  Durasi : {self.total_duration_str} "
            f"(tunggu: {self.waiting_time_minutes}m)\n"
            f"  {flags}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  SearchCriteria
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SearchCriteria:
    """Input dari user untuk satu sesi pencarian."""
    origin: str
    destination: str
    departure_date: str          # Format: "YYYY-MM-DD"
    passengers: int = 1
    transport_modes: List[str] = field(
        default_factory=lambda: ["flight", "train", "bus"]
    )
    max_results: int = 20
    max_results_per_mode: Optional[int] = None  # None = full, int = quick search
    include_local_legs: bool = False   # First-/last-mile (stub)

    def __post_init__(self):
        self.origin = self.origin.strip().title()
        self.destination = self.destination.strip().title()
        if self.passengers < 1:
            raise ValueError("Jumlah penumpang minimal 1.")
        valid_modes = {"flight", "train", "bus"}
        for m in self.transport_modes:
            if m not in valid_modes:
                raise ValueError(f"Mode tidak valid: {m}")


# ─────────────────────────────────────────────────────────────────────────────
#  OptimizerResult — output akhir SmartRouteOptimizer
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class OptimizerResult:
    """Hasil lengkap dari SmartRouteOptimizer untuk satu pencarian."""
    criteria: SearchCriteria
    all_combos: List[RouteCombo]
    cheapest: Optional[RouteCombo] = None
    fastest: Optional[RouteCombo] = None
    processing_time_ms: float = 0.0

    @property
    def total_options(self) -> int:
        return len(self.all_combos)

    @property
    def direct_options(self) -> List[RouteCombo]:
        return [c for c in self.all_combos if not c.is_multimodal]

    @property
    def multimodal_options(self) -> List[RouteCombo]:
        return [c for c in self.all_combos if c.is_multimodal]

    def summary(self) -> str:
        lines = [
            f"📍 Rute     : {self.criteria.origin} → {self.criteria.destination}",
            f"📅 Tanggal  : {self.criteria.departure_date}",
            f"👥 Penumpang: {self.criteria.passengers}",
            f"🔍 Total opsi ditemukan : {self.total_options}",
            f"   ↳ Langsung    : {len(self.direct_options)}",
            f"   ↳ Multi-Modal : {len(self.multimodal_options)}",
        ]
        if self.cheapest:
            lines.append(f"💰 Terhemat  : {self.cheapest.total_price_str} "
                         f"({self.cheapest.mode_label})")
        if self.fastest:
            lines.append(f"⚡ Tercepat  : {self.fastest.total_duration_str} "
                         f"({self.fastest.mode_label})")
        lines.append(f"⏱️  Waktu proses: {self.processing_time_ms:.1f} ms")
        return "\n".join(lines)
