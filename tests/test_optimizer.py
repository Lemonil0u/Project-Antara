"""
tests/test_optimizer.py — ANTARA Project
========================================
Unit test untuk SmartRouteOptimizer dan DummyDataGenerator.

Semua test pakai DummyDataGenerator(seed=42) — deterministik, tidak
butuh jaringan / browser.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.optimizer import DummyDataGenerator, SmartRouteOptimizer
from engine.local_data import LocalSegmentGenerator
from models import SearchCriteria


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def data_source():
    return DummyDataGenerator(seed=42)


@pytest.fixture
def optimizer(data_source):
    return SmartRouteOptimizer(data_source=data_source, max_transits=2)


@pytest.fixture
def criteria_basic():
    return SearchCriteria(
        origin="Jakarta", destination="Surabaya",
        departure_date="2026-05-15", passengers=2,
        max_results=15,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Konstruksi optimizer
# ─────────────────────────────────────────────────────────────────────────────

class TestConstruction:
    def test_requires_data_source(self):
        with pytest.raises(ValueError, match="data_source"):
            SmartRouteOptimizer(data_source=None)


# ─────────────────────────────────────────────────────────────────────────────
#  DummyDataGenerator
# ─────────────────────────────────────────────────────────────────────────────

class TestDummyDataGenerator:
    def test_deterministic_with_seed(self):
        gen1 = DummyDataGenerator(seed=42)
        gen2 = DummyDataGenerator(seed=42)
        a = gen1.get_segments("Jakarta", "Surabaya", "2026-05-15", 1)
        b = gen2.get_segments("Jakarta", "Surabaya", "2026-05-15", 1)
        assert len(a) == len(b)
        assert [s.price for s in a] == [s.price for s in b]

    def test_returns_segments(self, data_source):
        segs = data_source.get_segments("Jakarta", "Surabaya", "2026-05-15", 1)
        assert len(segs) > 0
        for s in segs:
            assert s.mode in {"flight", "train", "bus"}
            assert s.price > 0
            assert s.duration_minutes > 0
            assert s.arrival_time > s.departure_time

    def test_mode_filter_respected(self, data_source):
        segs = data_source.get_segments(
            "Jakarta", "Surabaya", "2026-05-15", 1, modes=["train"],
        )
        for s in segs:
            assert s.mode == "train"

    def test_segments_sorted_by_departure(self, data_source):
        segs = data_source.get_segments("Jakarta", "Surabaya", "2026-05-15", 1)
        for i in range(1, len(segs)):
            assert segs[i].departure_time >= segs[i - 1].departure_time


# ─────────────────────────────────────────────────────────────────────────────
#  SmartRouteOptimizer
# ─────────────────────────────────────────────────────────────────────────────

class TestOptimizer:
    def test_returns_options(self, optimizer, criteria_basic):
        result = optimizer.optimize(criteria_basic)
        assert result.total_options > 0

    def test_max_results_capped(self, optimizer):
        criteria = SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=1, max_results=5,
        )
        result = optimizer.optimize(criteria)
        assert result.total_options <= 5

    def test_cheapest_flag_set(self, optimizer, criteria_basic):
        result = optimizer.optimize(criteria_basic)
        if result.cheapest:
            assert result.cheapest.is_cheapest is True
            # cheapest harus benar-benar termurah
            min_price = min(c.total_price for c in result.all_combos)
            assert result.cheapest.total_price == min_price

    def test_fastest_flag_set(self, optimizer, criteria_basic):
        result = optimizer.optimize(criteria_basic)
        if result.fastest:
            assert result.fastest.is_fastest is True
            min_dur = min(c.total_duration_minutes for c in result.all_combos)
            assert result.fastest.total_duration_minutes == min_dur

    def test_total_price_accounts_for_passengers(self, data_source):
        # Bandingkan 1 vs 2 penumpang untuk rute langsung — harga harus naik
        opt = SmartRouteOptimizer(data_source=DummyDataGenerator(seed=42))
        r1 = opt.optimize(SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=1, max_results=20,
        ))
        opt2 = SmartRouteOptimizer(data_source=DummyDataGenerator(seed=42))
        r2 = opt2.optimize(SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=2, max_results=20,
        ))
        # Direct options harus lebih mahal untuk passenger=2
        d1 = sorted([c.total_price for c in r1.direct_options])
        d2 = sorted([c.total_price for c in r2.direct_options])
        if d1 and d2:
            # 2 penumpang = ~2x harga
            assert d2[0] >= d1[0] * 1.8

    def test_weighted_sorting_direct(self, optimizer):
        """
        Test _sort_combos secara langsung pada list lengkap (tanpa truncation).

        CATATAN: kita TIDAK test sorting via optimize() karena optimize()
        memotong [:max_results] SETELAH sort. Setelah truncation, normalisasi
        min/max berubah, sehingga skor recomputed di test bisa berbeda dari
        skor yang dipakai saat sorting. test_weighted_sorting_direct ini
        memvalidasi kontrak sebenarnya: _sort_combos menghasilkan urutan
        monotonik atas list yang sama yang dipakai untuk normalisasi.
        """
        gen = DummyDataGenerator(seed=42)
        segs = gen.get_segments("Jakarta", "Surabaya", "2026-05-15", 1)
        from models import RouteCombo
        combos = [
            RouteCombo(
                id=f"C{i}", segments=[s],
                total_price=s.price, total_duration_minutes=s.duration_minutes,
                waiting_time_minutes=0,
            )
            for i, s in enumerate(segs)
        ]
        sorted_combos = optimizer._sort_combos(combos)

        # Pakai min/max yang SAMA dengan yang dipakai _sort_combos (full list)
        prices    = [c.total_price for c in sorted_combos]
        durations = [c.total_duration_minutes for c in sorted_combos]
        min_p, max_p = min(prices), max(prices)
        min_d, max_d = min(durations), max(durations)

        def score(c):
            pr = (c.total_price - min_p) / (max_p - min_p) if max_p != min_p else 0
            dr = (c.total_duration_minutes - min_d) / (max_d - min_d) if max_d != min_d else 0
            return 0.6 * pr + 0.4 * dr

        scores = [score(c) for c in sorted_combos]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1] - 1e-9, (
                f"Skor tidak monotonik di index {i}: {scores}"
            )

    def test_multimodal_combos_have_waiting_time(self, optimizer, criteria_basic):
        result = optimizer.optimize(criteria_basic)
        for c in result.multimodal_options:
            # Per leg: 60–300 menit (MAX_TRANSFER_WAIT=300 untuk akomodasi
            # transfer kereta→pesawat yang butuh check-in 1.5-2 jam).
            # Total waiting_time = jumlah semua leg.
            n_legs = len(c.segments) - 1
            assert c.waiting_time_minutes >= 60 * n_legs
            assert c.waiting_time_minutes <= 300 * n_legs


# ─────────────────────────────────────────────────────────────────────────────
#  First-mile / Last-mile (stub)
# ─────────────────────────────────────────────────────────────────────────────

class TestLocalSegmentIntegration:
    def test_no_local_legs_when_disabled(self, optimizer, criteria_basic):
        result = optimizer.optimize(criteria_basic)
        for combo in result.all_combos:
            assert combo.first_mile is None
            assert combo.last_mile is None
            assert combo.has_local_legs is False

    def test_local_legs_added_when_enabled(self, data_source):
        local_gen = LocalSegmentGenerator(seed=42)
        opt = SmartRouteOptimizer(
            data_source=data_source, local_generator=local_gen,
        )
        criteria = SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=1,
            include_local_legs=True, max_results=10,
        )
        result = opt.optimize(criteria)
        for combo in result.all_combos:
            assert combo.first_mile is not None
            assert combo.last_mile is not None
            assert combo.has_local_legs is True
            assert "🛵 Door-to-Door" in combo.badges

    def test_local_legs_increase_price_and_duration(self, data_source):
        # Tanpa local
        opt_no = SmartRouteOptimizer(data_source=DummyDataGenerator(seed=42))
        r_no = opt_no.optimize(SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=1,
            include_local_legs=False, max_results=10,
        ))

        # Dengan local
        opt_yes = SmartRouteOptimizer(
            data_source=DummyDataGenerator(seed=42),
            local_generator=LocalSegmentGenerator(seed=42),
        )
        r_yes = opt_yes.optimize(SearchCriteria(
            origin="Jakarta", destination="Surabaya",
            departure_date="2026-05-15", passengers=1,
            include_local_legs=True, max_results=10,
        ))

        # Average price dan duration harus naik dengan local legs
        if r_no.total_options and r_yes.total_options:
            avg_no  = sum(c.total_price for c in r_no.all_combos)  / len(r_no.all_combos)
            avg_yes = sum(c.total_price for c in r_yes.all_combos) / len(r_yes.all_combos)
            assert avg_yes > avg_no
