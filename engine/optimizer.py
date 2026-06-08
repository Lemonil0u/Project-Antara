"""
engine/optimizer.py — ANTARA Project
====================================
Smart Route Optimizer.

Komponen:
  SmartRouteOptimizer — menerima SearchCriteria, memanggil data_source,
  menggabungkan segmen jadi RouteCombo (langsung + multi-modal),
  menghitung metrik, memberi flag cheapest/fastest, sorting via
  weighted score (0.6 × harga + 0.4 × durasi), return OptimizerResult.

Pemilihan data_source:
    Production : MultiModalDataSource(...)

Optional first-mile / last-mile (stub):
    optimizer = SmartRouteOptimizer(
        data_source=...,
        local_generator=LocalSegmentGenerator(seed=42),
    )
"""

import time
from typing import Dict, List, Optional, Tuple

from models import (
    LocalSegment,
    OptimizerResult,
    RouteCombo,
    SearchCriteria,
    TransportSegment,
)


# ══════════════════════════════════════════════════════════════════════════════
#  KONSTANTA — Data Referensi Kota & Operator Indonesia
# ══════════════════════════════════════════════════════════════════════════════

TRANSIT_HUBS: Dict[str, List[str]] = {
    "Jakarta":        ["Bandung", "Semarang", "Yogyakarta", "Surabaya"],
    "Bandung":        ["Jakarta", "Yogyakarta", "Semarang"],
    "Semarang":       ["Jakarta", "Yogyakarta", "Surabaya", "Solo"],
    "Yogyakarta":     ["Jakarta", "Bandung", "Semarang", "Surabaya", "Solo"],
    "Solo":           ["Semarang", "Yogyakarta", "Surabaya"],
    "Surabaya":       ["Jakarta", "Semarang", "Yogyakarta", "Bali", "Denpasar", "Malang"],
    "Malang":         ["Surabaya", "Bali", "Denpasar"],
    "Bali":           ["Surabaya", "Jakarta", "Lombok"],
    "Denpasar":       ["Surabaya", "Jakarta", "Lombok"],  # Alias Bali
    "Lombok":         ["Bali", "Denpasar", "Surabaya"],
    "Medan":          ["Jakarta", "Padang", "Batam"],
    "Padang":         ["Medan", "Jakarta"],
    "Batam":          ["Medan", "Jakarta"],
    "Makassar":       ["Jakarta", "Surabaya", "Bali", "Denpasar"],
    "Manado":         ["Makassar", "Jakarta"],
    "Palembang":      ["Jakarta", "Bandar Lampung"],
    "Bandar Lampung": ["Palembang", "Jakarta"],
}

# Alias mapping: nama alternatif kota → nama kanonik
CITY_ALIASES = {
    "Denpasar": "Bali",   # Saat scrape pesawat, "Bali" lebih umum
    # Tambah alias lain di sini bila perlu
}

TRAIN_CITIES = {
    "Jakarta", "Bandung", "Semarang", "Yogyakarta",
    "Solo", "Surabaya", "Malang", "Cirebon", "Purwokerto",
}
FLIGHT_CITIES = {
    "Jakarta", "Surabaya", "Bali", "Denpasar", "Medan", "Makassar",
    "Yogyakarta", "Semarang", "Bandung", "Batam", "Lombok",
    "Manado", "Padang", "Palembang", "Bandar Lampung", "Malang",
    "Balikpapan", "Pontianak", "Banjarmasin", "Pekanbaru",
}

# Operator per moda
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
    ("PO Rosalia Indah",  "RI", 4.3),
    ("PO Sumber Alam",    "SA", 4.1),
    ("PO Pahala Kencana", "PK", 3.9),
    ("PO Mira",           "MI", 3.8),
    ("PO Harapan Jaya",   "HJ", 3.7),
    ("PO Lorena",         "LO", 3.6),
    ("PO Sari Harum",     "SH", 4.0),
    ("Damri",             "DM", 3.8),
]

# Estimasi harga IDR per rute langsung (dipakai dummy generator)
ROUTE_PRICE_TABLE: Dict[Tuple[str, str], Dict[str, Tuple[int, int]]] = {
    ("Jakarta", "Surabaya"):     {"flight": (400_000, 900_000),   "train": (200_000, 500_000), "bus": (150_000, 300_000)},
    ("Jakarta", "Yogyakarta"):   {"flight": (350_000, 750_000),   "train": (175_000, 400_000), "bus": (120_000, 250_000)},
    ("Jakarta", "Semarang"):     {"flight": (300_000, 700_000),   "train": (150_000, 350_000), "bus": (100_000, 220_000)},
    ("Jakarta", "Bandung"):      {"train": (80_000, 200_000),     "bus":   (50_000, 130_000)},
    ("Jakarta", "Bali"):         {"flight": (500_000, 1_400_000)},
    ("Jakarta", "Medan"):        {"flight": (600_000, 1_500_000)},
    ("Jakarta", "Makassar"):     {"flight": (550_000, 1_300_000)},
    ("Surabaya", "Bali"):        {"flight": (350_000, 850_000),   "bus":   (200_000, 400_000)},
    ("Yogyakarta", "Surabaya"):  {"train": (100_000, 280_000),    "bus":   (80_000, 180_000)},
    ("Semarang", "Surabaya"):    {"train": (80_000, 200_000),     "bus":   (70_000, 160_000)},
    ("Semarang", "Yogyakarta"):  {"train": (60_000, 150_000),     "bus":   (50_000, 120_000)},
    ("Bandung", "Yogyakarta"):   {"train": (120_000, 300_000),    "bus":   (100_000, 220_000)},
    ("Bandung", "Semarang"):     {"train": (100_000, 250_000),    "bus":   (90_000, 200_000)},
}

# Estimasi durasi (menit) per rute langsung (dipakai dummy generator)
ROUTE_DURATION_TABLE: Dict[Tuple[str, str], Dict[str, Tuple[int, int]]] = {
    ("Jakarta", "Surabaya"):     {"flight": (75, 90),    "train": (480, 660),  "bus": (720, 900)},
    ("Jakarta", "Yogyakarta"):   {"flight": (60, 75),    "train": (330, 480),  "bus": (540, 660)},
    ("Jakarta", "Semarang"):     {"flight": (55, 70),    "train": (360, 420),  "bus": (420, 540)},
    ("Jakarta", "Bandung"):      {"train": (150, 210),   "bus":   (180, 300)},
    ("Jakarta", "Bali"):         {"flight": (90, 110)},
    ("Jakarta", "Medan"):        {"flight": (120, 150)},
    ("Jakarta", "Makassar"):     {"flight": (150, 180)},
    ("Surabaya", "Bali"):        {"flight": (45, 60),    "bus":   (480, 600)},
    ("Yogyakarta", "Surabaya"):  {"train": (240, 360),   "bus":   (360, 480)},
    ("Semarang", "Surabaya"):    {"train": (180, 270),   "bus":   (270, 360)},
    ("Semarang", "Yogyakarta"):  {"train": (90, 120),    "bus":   (120, 180)},
    ("Bandung", "Yogyakarta"):   {"train": (300, 420),   "bus":   (360, 480)},
    ("Bandung", "Semarang"):     {"train": (270, 390),   "bus":   (360, 480)},
}

# Constraints transfer multi-modal
# Catatan: 60-300 menit (1-5 jam) untuk akomodasi transfer multi-modal
# yang butuh waktu check-in bandara (1.5-2 jam) + buffer antar-stasiun
MIN_TRANSFER_WAIT = 60   # menit (1 jam minimum)
MAX_TRANSFER_WAIT = 300  # menit (5 jam maksimum)

# Bobot weighted scoring
WEIGHT_PRICE    = 0.6
WEIGHT_DURATION = 0.4


def _resolve_alias(city: str) -> str:
    """Resolve nama alias ke nama kanonik di ROUTE_PRICE_TABLE."""
    return CITY_ALIASES.get(city, city)


def _normalize_key(a: str, b: str) -> Tuple[str, str]:
    """
    Kembalikan (a, b) atau (b, a) sesuai yang ada di ROUTE_PRICE_TABLE.
    Resolve alias dulu (e.g. Denpasar → Bali).
    """
    a_canon = _resolve_alias(a)
    b_canon = _resolve_alias(b)
    if (a_canon, b_canon) in ROUTE_PRICE_TABLE:
        return (a_canon, b_canon)
    if (b_canon, a_canon) in ROUTE_PRICE_TABLE:
        return (b_canon, a_canon)
    return (a_canon, b_canon)

# ══════════════════════════════════════════════════════════════════════════════
#  SMART ROUTE OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════
class SmartRouteOptimizer:
    """
    Algoritma inti ANTARA.

    Cara kerja:
      1. Ambil segmen langsung (origin → destination) dari data source.
      2. Cari kota-kota transit yang valid.
      3. Ambil segmen untuk setiap leg multi-modal (≤ max_transits transit).
      4. Gabungkan segmen menjadi RouteCombo yang waktunya feasible.
      5. (Opsional) Bungkus dengan first-mile / last-mile LocalSegment.
      6. Hitung total_price, total_duration_minutes, waiting_time.
      7. Sort dengan weighted score: 0.6 × harga + 0.4 × durasi.
      8. Flag cheapest & fastest.
      9. Return OptimizerResult.
    """

    def __init__(
        self,
        data_source=None,
        max_transits: int = 2,
        min_transfer_wait: int = MIN_TRANSFER_WAIT,
        max_transfer_wait: int = MAX_TRANSFER_WAIT,
        local_generator=None,    # Optional LocalSegmentGenerator
        weight_price: float = WEIGHT_PRICE,
        weight_duration: float = WEIGHT_DURATION,
    ):
        if data_source is None:
            raise ValueError(
                "data_source wajib diisi. Pakai MultiModalDataSource() untuk data nyata."
            )
        self.data_source       = data_source
        self.max_transits      = max_transits
        self.min_transfer_wait = min_transfer_wait
        self.max_transfer_wait = max_transfer_wait
        self.local_generator   = local_generator
        self.weight_price      = weight_price
        self.weight_duration   = weight_duration
        self._combo_counter    = 0

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────────────

    def optimize(self, criteria: SearchCriteria) -> OptimizerResult:
        """Titik masuk utama. Kembalikan OptimizerResult lengkap."""
        t_start = time.perf_counter()
        self._combo_counter = 0

        origin      = criteria.origin
        destination = criteria.destination
        date_str    = criteria.departure_date
        passengers  = criteria.passengers
        modes       = criteria.transport_modes

        # ── Langkah 1: Kumpulkan segmen ──────────────────────────────────────
        direct_segs = self.data_source.get_segments(
            origin, destination, date_str, passengers, modes
        )

        transit_cities = self._find_transit_cities(origin, destination)
        transit_seg_map: Dict[Tuple[str, str], List[TransportSegment]] = {}

        for city in transit_cities:
            key1 = (origin, city)
            if key1 not in transit_seg_map:
                transit_seg_map[key1] = self.data_source.get_segments(
                    origin, city, date_str, passengers, modes
                )
            key2 = (city, destination)
            if key2 not in transit_seg_map:
                transit_seg_map[key2] = self.data_source.get_segments(
                    city, destination, date_str, passengers, modes
                )

        # ── Langkah 2: Bangun RouteCombo ─────────────────────────────────────
        all_combos: List[RouteCombo] = []

        for seg in direct_segs:
            all_combos.append(self._single_segment_combo(seg, passengers))

        for city in transit_cities:
            legs_1 = transit_seg_map.get((origin, city), [])
            legs_2 = transit_seg_map.get((city, destination), [])
            all_combos.extend(self._combine_two_legs(legs_1, legs_2, passengers))

        if self.max_transits >= 2:
            for ca, cb in self._find_double_transits(origin, destination, transit_cities):
                legs_1 = transit_seg_map.get((origin, ca), [])
                legs_2 = transit_seg_map.get(
                    (ca, cb),
                    self.data_source.get_segments(ca, cb, date_str, passengers, modes),
                )
                legs_3 = transit_seg_map.get((cb, destination), [])
                all_combos.extend(self._combine_three_legs(legs_1, legs_2, legs_3, passengers))

        # ── Langkah 3 (Opsional): Tambah first-mile / last-mile ──────────────
        if criteria.include_local_legs and self.local_generator is not None:
            all_combos = self._wrap_with_local(all_combos, origin, destination)

        # ── Langkah 4: Dedup, sort, flag ─────────────────────────────────────
        all_combos = self._deduplicate(all_combos)
        all_combos = self._sort_combos(all_combos)
        all_combos = all_combos[: criteria.max_results]
        cheapest, fastest = self._flag_combos(all_combos)

        return OptimizerResult(
            criteria           = criteria,
            all_combos         = all_combos,
            cheapest           = cheapest,
            fastest            = fastest,
            processing_time_ms = (time.perf_counter() - t_start) * 1000,
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Transit discovery
    # ─────────────────────────────────────────────────────────────────────────

    def _find_transit_cities(self, origin: str, destination: str) -> List[str]:
        """
        Cari kota transit yang valid antara origin dan destination.

        Logika:
          1. Cari intersection neighbors origin & destination di TRANSIT_HUBS.
          2. Kalau salah satu kota tidak terdaftar (kota baru/kecil),
             pakai DEFAULT_TRANSIT_HUBS sebagai kandidat universal.
        """
        # Default hubs untuk kota-kota tidak terdaftar — kota besar yang
        # umumnya jadi titik transit di Indonesia
        DEFAULT_TRANSIT_HUBS = ["Jakarta", "Surabaya", "Yogyakarta", "Semarang", "Bandung"]

        origin_neighbors = set(TRANSIT_HUBS.get(origin, DEFAULT_TRANSIT_HUBS))
        dest_neighbors   = set(TRANSIT_HUBS.get(destination, DEFAULT_TRANSIT_HUBS))
        candidates = origin_neighbors & dest_neighbors
        candidates |= {
            c for c in TRANSIT_HUBS.get(destination, DEFAULT_TRANSIT_HUBS)
            if c in TRANSIT_HUBS.get(origin, DEFAULT_TRANSIT_HUBS)
        }
        candidates.discard(origin)
        candidates.discard(destination)
        return list(candidates)

    def _find_double_transits(
        self, origin: str, destination: str, single_transits: List[str],
    ) -> List[Tuple[str, str]]:
        pairs = []
        for ca in single_transits:
            for cb in TRANSIT_HUBS.get(ca, []):
                if cb in (origin, destination, ca):
                    continue
                if destination in TRANSIT_HUBS.get(cb, []):
                    pairs.append((ca, cb))
        return pairs[:6]

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Combo builders
    # ─────────────────────────────────────────────────────────────────────────

    def _next_combo_id(self) -> str:
        self._combo_counter += 1
        return f"COMBO-{self._combo_counter:04d}"

    def _single_segment_combo(self, seg: TransportSegment, passengers: int) -> RouteCombo:
        return RouteCombo(
            id                     = self._next_combo_id(),
            segments               = [seg],
            total_price            = seg.price * passengers,
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
        combos = []
        for s1 in legs_1:
            for s2 in legs_2:
                wait = int((s2.departure_time - s1.arrival_time).total_seconds() / 60)
                if not (self.min_transfer_wait <= wait <= self.max_transfer_wait):
                    continue
                combos.append(RouteCombo(
                    id                     = self._next_combo_id(),
                    segments               = [s1, s2],
                    total_price            = (s1.price + s2.price) * passengers,
                    total_duration_minutes = s1.duration_minutes + wait + s2.duration_minutes,
                    waiting_time_minutes   = wait,
                    average_rating         = self._avg_rating([s1, s2]),
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
                    combos.append(RouteCombo(
                        id                     = self._next_combo_id(),
                        segments               = [s1, s2, s3],
                        total_price            = (s1.price + s2.price + s3.price) * passengers,
                        total_duration_minutes = (
                            s1.duration_minutes + w1
                            + s2.duration_minutes + w2
                            + s3.duration_minutes
                        ),
                        waiting_time_minutes   = w1 + w2,
                        average_rating         = self._avg_rating([s1, s2, s3]),
                    ))
        return combos

    def _wrap_with_local(
        self,
        combos: List[RouteCombo],
        origin: str,
        destination: str,
    ) -> List[RouteCombo]:
        """
        Bungkus setiap combo dengan first-mile dan last-mile dari local_generator.
        Total price dan duration ditambah sesuai estimasi lokal.

        CATATAN: Saat ini local_generator masih placeholder (stub).
        """
        if self.local_generator is None:
            return combos

        wrapped = []
        for combo in combos:
            first: LocalSegment = self.local_generator.generate_first_mile(origin)
            last:  LocalSegment = self.local_generator.generate_last_mile(destination)
            combo.first_mile = first
            combo.last_mile  = last
            combo.total_price += first.price + last.price
            combo.total_duration_minutes += first.duration_minutes + last.duration_minutes
            wrapped.append(combo)
        return wrapped

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE — Post-processing
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _avg_rating(segs: List[TransportSegment]) -> Optional[float]:
        ratings = [s.rating for s in segs if s.rating is not None]
        return round(sum(ratings) / len(ratings), 2) if ratings else None

    @staticmethod
    def _deduplicate(combos: List[RouteCombo]) -> List[RouteCombo]:
        """Buang combo duplikat: sama jika urutan segment ID-nya identik."""
        seen = set()
        unique = []
        for c in combos:
            key = tuple(s.id for s in c.segments)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _sort_combos(self, combos: List[RouteCombo]) -> List[RouteCombo]:
        """
        Urutkan berdasarkan weighted composite score:
            score = weight_price × normalized_price
                  + weight_duration × normalized_duration

        Normalisasi min-max [0, 1]; skor terendah = combo terbaik.
        Default weights: 0.6 price + 0.4 duration.
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
            return self.weight_price * pr + self.weight_duration * dr

        combos.sort(key=_score)
        return combos

    @staticmethod
    def _flag_combos(
        combos: List[RouteCombo],
    ) -> Tuple[Optional[RouteCombo], Optional[RouteCombo]]:
        """Tandai combo dengan is_cheapest & is_fastest."""
        if not combos:
            return None, None
        cheapest = min(combos, key=lambda c: c.total_price)
        fastest  = min(combos, key=lambda c: c.total_duration_minutes)
        cheapest.is_cheapest = True
        fastest.is_fastest   = True
        return cheapest, fastest


# ══════════════════════════════════════════════════════════════════════════════
#  QUICK-TEST  (jalankan: python -m engine.optimizer)
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import os

    # Tambah root project ke path agar import config & engine berjalan
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from config import SCRAPER_TIMEOUT, SCRAPER_HEADLESS, SCRAPER_ENABLED_MODES, CACHE_TTL_MINUTES
    from database import DatabaseManager
    from engine.data_source import MultiModalDataSource

    print("=" * 60)
    print("  ANTARA — Smart Route Optimizer  (Live via MultiModalDataSource)")
    print("=" * 60)

    # Ambil argumen opsional dari command line:
    #   python -m engine.optimizer [origin] [destination] [YYYY-MM-DD] [passengers]
    # Default: Jakarta → Surabaya, hari ini, 1 penumpang
    from datetime import date as _date
    _origin      = sys.argv[1] if len(sys.argv) > 1 else "Jakarta"
    _destination = sys.argv[2] if len(sys.argv) > 2 else "Surabaya"
    _date_str    = sys.argv[3] if len(sys.argv) > 3 else _date.today().isoformat()
    _passengers  = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    print(f"  Rute      : {_origin} → {_destination}")
    print(f"  Tanggal   : {_date_str}")
    print(f"  Penumpang : {_passengers}")
    print(f"  Timeout   : {SCRAPER_TIMEOUT}s  |  Headless: {SCRAPER_HEADLESS}")
    print(f"  Moda      : {', '.join(SCRAPER_ENABLED_MODES)}")
    print("=" * 60)

    _db = DatabaseManager()
    _ds = MultiModalDataSource(
        headless=SCRAPER_HEADLESS,
        timeout=SCRAPER_TIMEOUT,
        enabled_modes=SCRAPER_ENABLED_MODES,
        db=_db,
        cache_ttl_minutes=CACHE_TTL_MINUTES,
    )

    criteria = SearchCriteria(
        origin=_origin,
        destination=_destination,
        departure_date=_date_str,
        passengers=_passengers,
        transport_modes=SCRAPER_ENABLED_MODES,
        max_results=15,
    )
    optimizer = SmartRouteOptimizer(
        data_source=_ds,
        max_transits=2,
    )
    result = optimizer.optimize(criteria)

    print("\n" + result.summary())
    print("\n─── Top 5 Rekomendasi ─────────────────────────")
    for i, combo in enumerate(result.all_combos[:5], 1):
        print(f"\n#{i}  {combo}")
    print()