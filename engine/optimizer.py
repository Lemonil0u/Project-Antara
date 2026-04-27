"""
engine/optimizer.py - ANTARA Project
=====================================
Smart Route Optimizer + Dummy Data Generator

Tanggung jawab modul ini:
  1. DummyDataGenerator  → menghasilkan TransportSegment palsu yang realistis
                            untuk rute langsung dan rute via kota transit
  2. SmartRouteOptimizer → menerima SearchCriteria, memanggil generator (atau
                            scraper asli nanti), menggabungkan segmen menjadi
                            RouteCombo (single & multi-modal), menghitung semua
                            metrik, memberi flag "cheapest" / "fastest", dan
                            mengembalikan OptimizerResult yang siap ditampilkan.

Saat scraper sudah jadi, cukup ganti pemanggilan DummyDataGenerator dengan
instance scraper yang punya interface yang sama:
    def get_segments(origin, destination, date, passengers) -> List[TransportSegment]
"""

import random
import time
import uuid
from datetime import datetime, timedelta
from itertools import combinations, permutations
from typing import Dict, List, Optional, Tuple

from models import (
    OptimizerResult,
    RouteCombo,
    SearchCriteria,
    TransportSegment,
)


# ══════════════════════════════════════════════════════════════════════════════
#  KONSTANTA — Data Referensi Kota & Operator Indonesia
# ══════════════════════════════════════════════════════════════════════════════

# Kota-kota besar yang bisa jadi titik transit multi-modal
TRANSIT_HUBS: Dict[str, List[str]] = {
    "Jakarta":    ["Bandung", "Semarang", "Yogyakarta", "Surabaya"],
    "Bandung":    ["Jakarta", "Yogyakarta", "Semarang"],
    "Semarang":   ["Jakarta", "Yogyakarta", "Surabaya", "Solo"],
    "Yogyakarta": ["Jakarta", "Bandung", "Semarang", "Surabaya", "Solo"],
    "Solo":       ["Semarang", "Yogyakarta", "Surabaya"],
    "Surabaya":   ["Jakarta", "Semarang", "Yogyakarta", "Bali", "Malang"],
    "Malang":     ["Surabaya", "Bali"],
    "Bali":       ["Surabaya", "Jakarta", "Lombok"],
    "Lombok":     ["Bali", "Surabaya"],
    "Medan":      ["Jakarta", "Padang", "Batam"],
    "Padang":     ["Medan", "Jakarta"],
    "Batam":      ["Medan", "Jakarta"],
    "Makassar":   ["Jakarta", "Surabaya", "Bali"],
    "Manado":     ["Makassar", "Jakarta"],
    "Palembang":  ["Jakarta", "Bandar Lampung"],
    "Bandar Lampung": ["Palembang", "Jakarta"],
}

# Kota-kota yang punya layanan kereta
TRAIN_CITIES = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Cirebon", "Purwokerto",
}

# Kota-kota yang punya bandara (layanan pesawat)
FLIGHT_CITIES = {
    "Jakarta", "Surabaya", "Bali", "Medan", "Makassar",
    "Yogyakarta", "Semarang", "Bandung", "Batam", "Lombok",
    "Manado", "Padang", "Palembang", "Bandar Lampung", "Malang",
}

# ── Operator per moda ─────────────────────────────────────────────────────────
FLIGHT_OPERATORS = [
    ("Garuda Indonesia", "GA", 4.5),
    ("Lion Air",         "JT", 3.8),
    ("Citilink",         "QG", 4.0),
    ("Batik Air",        "ID", 4.2),
    ("Super Air Jet",    "IU", 3.9),
    ("Wings Air",        "IW", 3.7),
]

TRAIN_OPERATORS = [
    ("KAI Argo Bromo Anggrek", "KA", 4.6),
    ("KAI Argo Wilis",         "KA", 4.5),
    ("KAI Taksaka",            "KA", 4.4),
    ("KAI Gajayana",           "KA", 4.3),
    ("KAI Argo Lawu",          "KA", 4.4),
    ("KAI Kertajaya",          "KA", 3.9),
    ("KAI Logawa",             "KA", 3.7),
    ("KAI Joglosemarkerto",    "KA", 4.1),
    ("KAI Sancaka",            "KA", 4.2),
]

BUS_OPERATORS = [
    ("PO Rosalia Indah",  "RI",  4.3),
    ("PO Sumber Alam",    "SA",  4.1),
    ("PO Pahala Kencana", "PK",  3.9),
    ("PO Mira",           "MI",  3.8),
    ("PO Harapan Jaya",   "HJ",  3.7),
    ("PO Lorena",         "LO",  3.6),
    ("PO Sari Harum",     "SH",  4.0),
    ("Damri",             "DM",  3.8),
]

# ── Estimasi harga IDR per rute langsung ─────────────────────────────────────
# Format: (origin, destination) → {"flight": (min, max), "train": ..., "bus": ...}
# Jika rute tidak ada di tabel, kalkulasi otomatis berdasarkan "jarak" estimasi.

ROUTE_PRICE_TABLE: Dict[Tuple[str, str], Dict[str, Tuple[int, int]]] = {
    ("Jakarta", "Surabaya"): {
        "flight": (400_000,   900_000),
        "train":  (200_000,   500_000),
        "bus":    (150_000,   300_000),
    },
    ("Jakarta", "Yogyakarta"): {
        "flight": (350_000,   750_000),
        "train":  (175_000,   400_000),
        "bus":    (120_000,   250_000),
    },
    ("Jakarta", "Semarang"): {
        "flight": (300_000,   700_000),
        "train":  (150_000,   350_000),
        "bus":    (100_000,   220_000),
    },
    ("Jakarta", "Bandung"): {
        "train":  (80_000,    200_000),
        "bus":    (50_000,    130_000),
    },
    ("Jakarta", "Bali"): {
        "flight": (500_000, 1_400_000),
    },
    ("Jakarta", "Medan"): {
        "flight": (600_000, 1_500_000),
    },
    ("Jakarta", "Makassar"): {
        "flight": (550_000, 1_300_000),
    },
    ("Surabaya", "Bali"): {
        "flight": (350_000,   850_000),
        "bus":    (200_000,   400_000),
    },
    ("Yogyakarta", "Surabaya"): {
        "train":  (100_000,   280_000),
        "bus":    (80_000,    180_000),
    },
    ("Semarang", "Surabaya"): {
        "train":  (80_000,    200_000),
        "bus":    (70_000,    160_000),
    },
    ("Semarang", "Yogyakarta"): {
        "train":  (60_000,    150_000),
        "bus":    (50_000,    120_000),
    },
    ("Bandung", "Yogyakarta"): {
        "train":  (120_000,   300_000),
        "bus":    (100_000,   220_000),
    },
    ("Bandung", "Semarang"): {
        "train":  (100_000,   250_000),
        "bus":    (90_000,    200_000),
    },
}

# ── Estimasi durasi (menit) per rute langsung ────────────────────────────────
ROUTE_DURATION_TABLE: Dict[Tuple[str, str], Dict[str, Tuple[int, int]]] = {
    ("Jakarta", "Surabaya"): {
        "flight": (75,  90),
        "train":  (480, 660),
        "bus":    (720, 900),
    },
    ("Jakarta", "Yogyakarta"): {
        "flight": (60,  75),
        "train":  (330, 480),
        "bus":    (540, 660),
    },
    ("Jakarta", "Semarang"): {
        "flight": (55,  70),
        "train":  (360, 420),
        "bus":    (420, 540),
    },
    ("Jakarta", "Bandung"): {
        "train":  (150, 210),
        "bus":    (180, 300),
    },
    ("Jakarta", "Bali"): {
        "flight": (90,  110),
    },
    ("Jakarta", "Medan"): {
        "flight": (120, 150),
    },
    ("Jakarta", "Makassar"): {
        "flight": (150, 180),
    },
    ("Surabaya", "Bali"): {
        "flight": (45,  60),
        "bus":    (480, 600),
    },
    ("Yogyakarta", "Surabaya"): {
        "train":  (240, 360),
        "bus":    (360, 480),
    },
    ("Semarang", "Surabaya"): {
        "train":  (180, 270),
        "bus":    (270, 360),
    },
    ("Semarang", "Yogyakarta"): {
        "train":  (90,  120),
        "bus":    (120, 180),
    },
    ("Bandung", "Yogyakarta"): {
        "train":  (300, 420),
        "bus":    (360, 480),
    },
    ("Bandung", "Semarang"): {
        "train":  (270, 390),
        "bus":    (360, 480),
    },
}

# Minimum waiting time antara segmen (menit)
MIN_TRANSFER_WAIT = 60   # 1 jam minimum transfer
MAX_TRANSFER_WAIT = 180  # 3 jam maksimum (masih masuk akal)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER: normalisasi kunci rute agar A→B == B→A di tabel
# ══════════════════════════════════════════════════════════════════════════════
def _normalize_key(a: str, b: str) -> Tuple[str, str]:
    """Kembalikan tuple (a, b) atau (b, a) sesuai urutan di ROUTE_PRICE_TABLE."""
    if (a, b) in ROUTE_PRICE_TABLE:
        return (a, b)
    if (b, a) in ROUTE_PRICE_TABLE:
        return (b, a)
    return (a, b)   # tidak ada di tabel, akan di-fallback


# ══════════════════════════════════════════════════════════════════════════════
#  DUMMY DATA GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
class DummyDataGenerator:
    """
    Menghasilkan daftar TransportSegment yang realistis untuk satu pasang
    (origin, destination, date) berdasarkan tabel harga & durasi di atas.

    Nanti, saat scraper sudah jadi, kelas ini bisa diganti dengan adapter
    yang memanggil plane_scraper / train_scraper / bus_scraper, asalkan
    interface `get_segments()` tetap sama.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: int opsional untuk reproducibility saat testing.
        """
        self._rng = random.Random(seed)
        self._counter = 0

    # ── public ───────────────────────────────────────────────────────────────
    def get_segments(
        self,
        origin: str,
        destination: str,
        date_str: str,
        passengers: int = 1,
        modes: Optional[List[str]] = None,
    ) -> List[TransportSegment]:
        """
        Hasilkan semua segmen tersedia untuk rute & tanggal tertentu.

        Args:
            origin      : Kota asal (title-case, e.g. "Jakarta")
            destination : Kota tujuan
            date_str    : "YYYY-MM-DD"
            passengers  : Jumlah penumpang (untuk filter available_seats)
            modes       : Subset dari ["flight","train","bus"]; None = semua

        Returns:
            List[TransportSegment] yang sudah diacak / diurutkan departure_time.
        """
        if modes is None:
            modes = ["flight", "train", "bus"]

        segments: List[TransportSegment] = []
        base_date = datetime.strptime(date_str, "%Y-%m-%d")
        key = _normalize_key(origin, destination)

        for mode in modes:
            # Cek apakah moda ini tersedia untuk kota ini
            if not self._mode_available(mode, origin, destination):
                continue

            price_range = self._get_price_range(key, mode, origin, destination)
            dur_range   = self._get_duration_range(key, mode, origin, destination)
            operators   = self._get_operators(mode)

            # Hasilkan 2–4 pilihan per moda
            n_options = self._rng.randint(2, 4)
            for _ in range(n_options):
                seg = self._make_segment(
                    mode, origin, destination, base_date,
                    price_range, dur_range, operators, passengers
                )
                segments.append(seg)

        # Urutkan berdasarkan departure_time
        segments.sort(key=lambda s: s.departure_time)
        return segments

    # ── private helpers ───────────────────────────────────────────────────────
    def _next_id(self, prefix: str = "SEG") -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:04d}"

    def _mode_available(self, mode: str, origin: str, destination: str) -> bool:
        """Apakah moda ini bisa beroperasi antara dua kota?"""
        if mode == "flight":
            return origin in FLIGHT_CITIES and destination in FLIGHT_CITIES
        if mode == "train":
            return origin in TRAIN_CITIES and destination in TRAIN_CITIES
        # Bus: selalu tersedia untuk kota-kota di Jawa; luar Jawa lebih terbatas
        jawa = {"Jakarta","Bandung","Semarang","Yogyakarta","Solo","Surabaya","Malang"}
        if origin in jawa and destination in jawa:
            return True
        # Bus antar pulau hanya Surabaya–Bali (ferry+bus)
        cross = {("Surabaya","Bali"), ("Bali","Surabaya")}
        return (origin, destination) in cross

    def _get_price_range(
        self, key: Tuple[str,str], mode: str, orig: str, dest: str
    ) -> Tuple[int, int]:
        table = ROUTE_PRICE_TABLE.get(key, {})
        if mode in table:
            return table[mode]
        # Fallback: estimasi berdasarkan "jarak" dengan faktor per moda
        base = self._rng.randint(200_000, 600_000)
        mult = {"flight": 1.5, "train": 1.0, "bus": 0.6}.get(mode, 1.0)
        lo = int(base * mult * 0.7)
        hi = int(base * mult * 1.3)
        return (lo, hi)

    def _get_duration_range(
        self, key: Tuple[str,str], mode: str, orig: str, dest: str
    ) -> Tuple[int, int]:
        table = ROUTE_DURATION_TABLE.get(key, {})
        if mode in table:
            return table[mode]
        # Fallback
        base = self._rng.randint(120, 480)
        mult = {"flight": 0.4, "train": 1.0, "bus": 1.4}.get(mode, 1.0)
        lo = int(base * mult * 0.8)
        hi = int(base * mult * 1.2)
        return (lo, hi)

    def _get_operators(self, mode: str) -> List[Tuple[str,str,float]]:
        return {
            "flight": FLIGHT_OPERATORS,
            "train":  TRAIN_OPERATORS,
            "bus":    BUS_OPERATORS,
        }[mode]

    def _make_segment(
        self,
        mode: str,
        origin: str,
        destination: str,
        base_date: datetime,
        price_range: Tuple[int, int],
        dur_range: Tuple[int, int],
        operators: List[Tuple[str, str, float]],
        passengers: int,
    ) -> TransportSegment:
        # Pilih operator acak
        provider, code, base_rating = self._rng.choice(operators)

        # Jadwal keberangkatan antara pukul 05:00–22:00
        dep_hour   = self._rng.randint(5, 22)
        dep_minute = self._rng.choice([0, 10, 15, 20, 30, 40, 45, 50])
        departure  = base_date.replace(hour=dep_hour, minute=dep_minute, second=0, microsecond=0)

        duration = self._rng.randint(*dur_range)
        arrival  = departure + timedelta(minutes=duration)

        price = self._rng.randint(*price_range)
        # Variasi harga sedikit acak agar terlihat nyata
        price = round(price / 1000) * 1000   # bulatkan ke ribuan

        rating = round(
            min(5.0, max(1.0, base_rating + self._rng.uniform(-0.3, 0.3))), 1
        )
        seats  = self._rng.randint(passengers, passengers + 50)

        seat_class = self._rng.choice(
            {"flight": ["Economy", "Business"],
             "train":  ["Economy", "Executive", "Business"],
             "bus":    ["Reguler", "Executive", "VIP"]}[mode]
        )

        return TransportSegment(
            id               = self._next_id(),
            mode             = mode,
            provider         = provider,
            provider_code    = code,
            origin           = origin,
            destination      = destination,
            departure_time   = departure,
            arrival_time     = arrival,
            duration_minutes = duration,
            price            = price,
            seat_class       = seat_class,
            available_seats  = seats,
            rating           = rating,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  SMART ROUTE OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════
class SmartRouteOptimizer:
    """
    Algoritma inti ANTARA.

    Cara kerja:
      1. Ambil segmen langsung (origin → destination) dari data source.
      2. Cari kota-kota transit yang valid antara origin dan destination.
      3. Ambil segmen untuk setiap leg (origin→transit, transit→destination,
         dan bahkan origin→transit1→transit2→destination).
      4. Gabungkan segmen menjadi RouteCombo yang time-feasible
         (waiting time ≥ MIN_TRANSFER_WAIT).
      5. Hitung total_price, total_duration, waiting_time.
      6. Flag cheapest & fastest.
      7. Kembalikan OptimizerResult.
    """

    def __init__(
        self,
        data_source=None,
        max_transits: int = 2,
        min_transfer_wait: int = MIN_TRANSFER_WAIT,
        max_transfer_wait: int = MAX_TRANSFER_WAIT,
    ):
        """
        Args:
            data_source      : Instance yang punya get_segments(). Default DummyDataGenerator.
            max_transits     : Maksimum kota transit per rute (default 2 = maks 3 kaki).
            min_transfer_wait: Minimum menit jeda antar segmen agar bisa naik.
            max_transfer_wait: Jika jeda melebihi ini, anggap tidak praktis.
        """
        self.data_source      = data_source or DummyDataGenerator()
        self.max_transits     = max_transits
        self.min_transfer_wait = min_transfer_wait
        self.max_transfer_wait = max_transfer_wait
        self._combo_counter   = 0

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────────────
    def optimize(self, criteria: SearchCriteria) -> OptimizerResult:
        """
        Titik masuk utama optimizer.

        Args:
            criteria: SearchCriteria dari user input.

        Returns:
            OptimizerResult berisi semua combo yang sudah dievaluasi.
        """
        t_start = time.perf_counter()
        self._combo_counter = 0

        origin      = criteria.origin
        destination = criteria.destination
        date_str    = criteria.departure_date
        passengers  = criteria.passengers
        modes       = criteria.transport_modes

        # ── Langkah 1: Kumpulkan semua segmen yang dibutuhkan ────────────────
        # Segmen langsung
        direct_segs: List[TransportSegment] = self.data_source.get_segments(
            origin, destination, date_str, passengers, modes
        )

        # Segmen transit (per kota transit)
        transit_cities = self._find_transit_cities(origin, destination)
        transit_seg_map: Dict[Tuple[str,str], List[TransportSegment]] = {}

        for city in transit_cities:
            # leg 1: origin → city
            key1 = (origin, city)
            if key1 not in transit_seg_map:
                transit_seg_map[key1] = self.data_source.get_segments(
                    origin, city, date_str, passengers, modes
                )
            # leg 2: city → destination
            key2 = (city, destination)
            if key2 not in transit_seg_map:
                transit_seg_map[key2] = self.data_source.get_segments(
                    city, destination, date_str, passengers, modes
                )

        # ── Langkah 2: Bangun RouteCombo ─────────────────────────────────────
        all_combos: List[RouteCombo] = []

        # Rute langsung (1 segmen)
        for seg in direct_segs:
            combo = self._single_segment_combo(seg, passengers)
            all_combos.append(combo)

        # Rute multi-modal via 1 kota transit (2 kaki)
        for city in transit_cities:
            legs_1 = transit_seg_map.get((origin, city), [])
            legs_2 = transit_seg_map.get((city, destination), [])
            combos_2 = self._combine_two_legs(legs_1, legs_2, passengers)
            all_combos.extend(combos_2)

        # Rute multi-modal via 2 kota transit (3 kaki) — jika max_transits >= 2
        if self.max_transits >= 2:
            for city_a, city_b in self._find_double_transits(origin, destination, transit_cities):
                legs_1 = transit_seg_map.get((origin, city_a), [])
                legs_2 = transit_seg_map.get((city_a, city_b),
                            self.data_source.get_segments(city_a, city_b, date_str, passengers, modes))
                legs_3 = transit_seg_map.get((city_b, destination), [])
                combos_3 = self._combine_three_legs(legs_1, legs_2, legs_3, passengers)
                all_combos.extend(combos_3)

        # ── Langkah 3: Filter, urutkan, flag ─────────────────────────────────
        all_combos = self._deduplicate(all_combos)
        all_combos = self._sort_combos(all_combos)
        all_combos = all_combos[: criteria.max_results]
        cheapest, fastest = self._flag_combos(all_combos)

        t_end = time.perf_counter()
        processing_ms = (t_end - t_start) * 1000

        return OptimizerResult(
            criteria         = criteria,
            all_combos       = all_combos,
            cheapest         = cheapest,
            fastest          = fastest,
            processing_time_ms = processing_ms,
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Transit discovery
    # ─────────────────────────────────────────────────────────────────────────
    def _find_transit_cities(self, origin: str, destination: str) -> List[str]:
        """
        Temukan kota transit yang secara geografis masuk akal antara origin
        dan destination berdasarkan TRANSIT_HUBS.
        """
        origin_neighbors = set(TRANSIT_HUBS.get(origin, []))
        dest_neighbors   = set(TRANSIT_HUBS.get(destination, []))
        # Kota yang terhubung dari origin DAN punya link ke destination
        candidates = origin_neighbors & dest_neighbors
        # Tambah kota yang langsung terhubung ke keduanya
        candidates |= {
            c for c in TRANSIT_HUBS.get(destination, [])
            if c in TRANSIT_HUBS.get(origin, [])
        }
        # Jangan masukkan origin atau destination itu sendiri
        candidates.discard(origin)
        candidates.discard(destination)
        return list(candidates)

    def _find_double_transits(
        self, origin: str, destination: str, single_transits: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Hasilkan pasangan (city_a, city_b) untuk rute 3-kaki yang masuk akal.
        city_a harus reachable dari origin, city_b harus reachable ke destination.
        """
        pairs = []
        for ca in single_transits:
            neighbors_of_ca = set(TRANSIT_HUBS.get(ca, []))
            for cb in neighbors_of_ca:
                if cb == origin or cb == destination or cb == ca:
                    continue
                # cb harus punya koneksi ke destination
                if destination in TRANSIT_HUBS.get(cb, []):
                    pairs.append((ca, cb))
        return pairs[:6]  # batasi agar tidak meledak

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Combo builders
    # ─────────────────────────────────────────────────────────────────────────
    def _next_combo_id(self) -> str:
        self._combo_counter += 1
        return f"COMBO-{self._combo_counter:04d}"

    def _single_segment_combo(
        self, seg: TransportSegment, passengers: int
    ) -> RouteCombo:
        total_price = seg.price * passengers
        return RouteCombo(
            id                     = self._next_combo_id(),
            segments               = [seg],
            total_price            = total_price,
            total_duration_minutes = seg.duration_minutes,
            waiting_time_minutes   = 0,
            average_rating         = seg.rating,
        )

    def _combine_two_legs(
        self,
        legs_1: List[TransportSegment],
        legs_2: List[TransportSegment],
        passengers: int,
    ) -> List[RouteCombo]:
        """
        Pasangkan setiap segmen di leg1 dengan setiap segmen di leg2
        yang departure-nya cukup setelah arrival leg1 (MIN ≤ wait ≤ MAX).
        """
        combos = []
        for s1 in legs_1:
            for s2 in legs_2:
                wait = int((s2.departure_time - s1.arrival_time).total_seconds() / 60)
                if not (self.min_transfer_wait <= wait <= self.max_transfer_wait):
                    continue
                total_duration = s1.duration_minutes + wait + s2.duration_minutes
                total_price    = (s1.price + s2.price) * passengers
                avg_rating     = self._avg_rating([s1, s2])
                combos.append(RouteCombo(
                    id                     = self._next_combo_id(),
                    segments               = [s1, s2],
                    total_price            = total_price,
                    total_duration_minutes = total_duration,
                    waiting_time_minutes   = wait,
                    average_rating         = avg_rating,
                ))
        return combos

    def _combine_three_legs(
        self,
        legs_1: List[TransportSegment],
        legs_2: List[TransportSegment],
        legs_3: List[TransportSegment],
        passengers: int,
    ) -> List[RouteCombo]:
        combos = []
        for s1 in legs_1:
            for s2 in legs_2:
                w1 = int((s2.departure_time - s1.arrival_time).total_seconds() / 60)
                if not (self.min_transfer_wait <= w1 <= self.max_transfer_wait):
                    continue
                for s3 in legs_3:
                    w2 = int((s3.departure_time - s2.arrival_time).total_seconds() / 60)
                    if not (self.min_transfer_wait <= w2 <= self.max_transfer_wait):
                        continue
                    total_duration = (
                        s1.duration_minutes + w1
                        + s2.duration_minutes + w2
                        + s3.duration_minutes
                    )
                    total_price = (s1.price + s2.price + s3.price) * passengers
                    avg_rating  = self._avg_rating([s1, s2, s3])
                    combos.append(RouteCombo(
                        id                     = self._next_combo_id(),
                        segments               = [s1, s2, s3],
                        total_price            = total_price,
                        total_duration_minutes = total_duration,
                        waiting_time_minutes   = w1 + w2,
                        average_rating         = avg_rating,
                    ))
        return combos

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Post-processing
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _avg_rating(segs: List[TransportSegment]) -> Optional[float]:
        ratings = [s.rating for s in segs if s.rating is not None]
        return round(sum(ratings) / len(ratings), 2) if ratings else None

    @staticmethod
    def _deduplicate(combos: List[RouteCombo]) -> List[RouteCombo]:
        """
        Buang combo duplikat: dua combo dianggap sama jika pakai segmen ID
        yang persis sama (dalam urutan yang sama).
        """
        seen = set()
        unique = []
        for c in combos:
            key = tuple(s.id for s in c.segments)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    @staticmethod
    def _sort_combos(combos: List[RouteCombo]) -> List[RouteCombo]:
        """
        Urutkan berdasarkan composite score:
          score = 0.6 × (price_rank) + 0.4 × (duration_rank)
        Skor lebih kecil = lebih baik.
        """
        if not combos:
            return combos

        prices    = [c.total_price for c in combos]
        durations = [c.total_duration_minutes for c in combos]
        min_p, max_p = min(prices), max(prices)
        min_d, max_d = min(durations), max(durations)

        def _normalize(val, lo, hi):
            return (val - lo) / (hi - lo) if hi != lo else 0.0

        def _score(c: RouteCombo) -> float:
            pr = _normalize(c.total_price, min_p, max_p)
            dr = _normalize(c.total_duration_minutes, min_d, max_d)
            return 0.6 * pr + 0.4 * dr

        combos.sort(key=_score)
        return combos

    @staticmethod
    def _flag_combos(
        combos: List[RouteCombo],
    ) -> Tuple[Optional[RouteCombo], Optional[RouteCombo]]:
        """
        Tandai combo dengan is_cheapest & is_fastest.
        Kembalikan (cheapest, fastest).
        """
        if not combos:
            return None, None

        cheapest = min(combos, key=lambda c: c.total_price)
        fastest  = min(combos, key=lambda c: c.total_duration_minutes)

        cheapest.is_cheapest = True
        fastest.is_fastest   = True

        return cheapest, fastest


# ══════════════════════════════════════════════════════════════════════════════
#  QUICK-TEST  (jalankan: python engine/optimizer.py)
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  ANTARA — Smart Route Optimizer  (Demo Mode)")
    print("=" * 60)

    criteria = SearchCriteria(
        origin           = "Jakarta",
        destination      = "Surabaya",
        departure_date   = "2026-05-10",
        passengers       = 2,
        transport_modes  = ["flight", "train", "bus"],
        max_results      = 15,
    )

    optimizer = SmartRouteOptimizer(
        data_source       = DummyDataGenerator(seed=42),
        max_transits      = 2,
        min_transfer_wait = 60,
        max_transfer_wait = 180,
    )

    result = optimizer.optimize(criteria)

    print("\n" + result.summary())
    print("\n─── Top 5 Rekomendasi ───────────────────────────────────")
    for i, combo in enumerate(result.all_combos[:5], 1):
        print(f"\n#{i}  {combo}")

    print("\n─── Cheapest ────────────────────────────────────────────")
    if result.cheapest:
        for seg in result.cheapest.segments:
            print(f"   {seg}")

    print("\n─── Fastest ─────────────────────────────────────────────")
    if result.fastest:
        for seg in result.fastest.segments:
            print(f"   {seg}")

    print("\n" + "=" * 60)
    print(f"Total combo dievaluasi : {result.total_options}")
    print(f"Multi-modal            : {len(result.multimodal_options)}")
    print(f"Langsung               : {len(result.direct_options)}")
    print(f"Waktu proses           : {result.processing_time_ms:.2f} ms")
