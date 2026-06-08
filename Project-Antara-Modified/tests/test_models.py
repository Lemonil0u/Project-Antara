"""
tests/test_models.py — ANTARA Project
=====================================
Unit test untuk dataclass di models.py.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Tambahkan root project ke sys.path agar `import models` jalan saat pytest dipanggil
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    LocalSegment, TransportSegment, RouteCombo,
    SearchCriteria, OptimizerResult,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_segment_train():
    return TransportSegment(
        id="SEG-001", mode="train", provider="KAI Argo Bromo", provider_code="KA",
        origin="Jakarta", destination="Surabaya",
        departure_time=datetime(2026, 5, 15, 8, 0),
        arrival_time=datetime(2026, 5, 15, 16, 30),
        duration_minutes=510, price=350_000,
        seat_class="Executive", available_seats=20, rating=4.5,
    )


@pytest.fixture
def sample_segment_flight():
    return TransportSegment(
        id="SEG-002", mode="flight", provider="Garuda Indonesia", provider_code="GA",
        origin="Jakarta", destination="Bali",
        departure_time=datetime(2026, 5, 15, 10, 0),
        arrival_time=datetime(2026, 5, 15, 11, 45),
        duration_minutes=105, price=900_000,
        seat_class="Economy", available_seats=12, rating=4.5,
    )


@pytest.fixture
def sample_segment_bus():
    return TransportSegment(
        id="SEG-003", mode="bus", provider="Rosalia Indah", provider_code="RI",
        origin="Surabaya", destination="Bali",
        departure_time=datetime(2026, 5, 15, 19, 0),
        arrival_time=datetime(2026, 5, 16, 5, 0),
        duration_minutes=600, price=180_000,
        seat_class="Executive", available_seats=8, rating=4.0,
    )


@pytest.fixture
def sample_local_first():
    return LocalSegment(
        id="LOCAL-001", mode="ride_hail", provider="Gojek",
        origin="Rumah", destination="Stasiun Gambir",
        duration_minutes=30, price=40_000,
    )


@pytest.fixture
def sample_local_last():
    return LocalSegment(
        id="LOCAL-002", mode="ride_hail", provider="Grab",
        origin="Stasiun Gubeng", destination="Hotel",
        duration_minutes=20, price=25_000,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  LocalSegment
# ─────────────────────────────────────────────────────────────────────────────

class TestLocalSegment:
    def test_duration_str_formats_correctly(self, sample_local_first):
        assert sample_local_first.duration_str == "30m"

    def test_duration_str_with_hours(self):
        seg = LocalSegment(
            id="L", mode="walk", provider="Walk",
            origin="A", destination="B",
            duration_minutes=75, price=0,
        )
        assert seg.duration_str == "1j 15m"

    def test_price_str_format(self, sample_local_first):
        assert sample_local_first.price_str == "Rp 40,000"

    def test_mode_icon(self, sample_local_first):
        assert sample_local_first.mode_icon == "🛵"

    def test_mode_icon_unknown_falls_back(self):
        seg = LocalSegment(
            id="L", mode="hovercraft", provider="X",
            origin="A", destination="B",
            duration_minutes=10, price=1,
        )
        assert seg.mode_icon == "🚗"


# ─────────────────────────────────────────────────────────────────────────────
#  TransportSegment
# ─────────────────────────────────────────────────────────────────────────────

class TestTransportSegment:
    def test_duration_str_with_minutes(self, sample_segment_train):
        assert sample_segment_train.duration_str == "8j 30m"

    def test_duration_str_round_hours(self):
        seg = TransportSegment(
            id="X", mode="train", provider="Test", provider_code="T",
            origin="A", destination="B",
            departure_time=datetime(2026, 1, 1, 8),
            arrival_time=datetime(2026, 1, 1, 10),
            duration_minutes=120, price=100_000,
            seat_class=None, available_seats=None, rating=None,
        )
        assert seg.duration_str == "2j"

    def test_price_str_format(self, sample_segment_train):
        assert sample_segment_train.price_str == "Rp 350,000"

    def test_mode_icons(self, sample_segment_train, sample_segment_flight, sample_segment_bus):
        assert sample_segment_train.mode_icon  == "🚂"
        assert sample_segment_flight.mode_icon == "✈️"
        assert sample_segment_bus.mode_icon    == "🚌"


# ─────────────────────────────────────────────────────────────────────────────
#  RouteCombo
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteCombo:
    def test_single_segment_combo_not_multimodal(self, sample_segment_train):
        combo = RouteCombo(
            id="C1", segments=[sample_segment_train],
            total_price=350_000, total_duration_minutes=510,
            waiting_time_minutes=0,
        )
        assert combo.is_multimodal is False
        assert combo.modes_used == ["train"]

    def test_multi_segment_combo_is_multimodal(self, sample_segment_train, sample_segment_flight):
        combo = RouteCombo(
            id="C2", segments=[sample_segment_train, sample_segment_flight],
            total_price=1_250_000, total_duration_minutes=700,
            waiting_time_minutes=85,
        )
        assert combo.is_multimodal is True
        assert combo.modes_used == ["train", "flight"]

    def test_modes_used_deduplicates(self):
        seg1 = TransportSegment(
            id="A", mode="train", provider="X", provider_code="X",
            origin="A", destination="B",
            departure_time=datetime(2026, 1, 1, 8),
            arrival_time=datetime(2026, 1, 1, 10),
            duration_minutes=120, price=100_000,
            seat_class=None, available_seats=None, rating=None,
        )
        seg2 = TransportSegment(
            id="B", mode="train", provider="Y", provider_code="Y",
            origin="B", destination="C",
            departure_time=datetime(2026, 1, 1, 11),
            arrival_time=datetime(2026, 1, 1, 13),
            duration_minutes=120, price=100_000,
            seat_class=None, available_seats=None, rating=None,
        )
        combo = RouteCombo(
            id="C", segments=[seg1, seg2], total_price=200_000,
            total_duration_minutes=300, waiting_time_minutes=60,
        )
        assert combo.modes_used == ["train"]  # tetap satu, bukan ["train", "train"]

    def test_route_label_chains_cities(self, sample_segment_train, sample_segment_flight):
        combo = RouteCombo(
            id="C", segments=[sample_segment_train, sample_segment_flight],
            total_price=0, total_duration_minutes=0, waiting_time_minutes=0,
        )
        # train: Jakarta→Surabaya, flight: Jakarta→Bali (intentionally mismatched untuk test pure logic)
        assert combo.route_label == "Jakarta → Surabaya → Bali"

    def test_badges_when_cheapest_and_fastest(self, sample_segment_train):
        combo = RouteCombo(
            id="C", segments=[sample_segment_train],
            total_price=350_000, total_duration_minutes=510,
            waiting_time_minutes=0, is_cheapest=True, is_fastest=True,
        )
        assert "💰 Terhemat" in combo.badges
        assert "⚡ Tercepat" in combo.badges
        assert "🔀 Multi-Modal" not in combo.badges

    def test_badges_door_to_door_when_local_legs_present(
        self, sample_segment_train, sample_local_first, sample_local_last,
    ):
        combo = RouteCombo(
            id="C", segments=[sample_segment_train],
            total_price=350_000, total_duration_minutes=510,
            waiting_time_minutes=0,
            first_mile=sample_local_first, last_mile=sample_local_last,
        )
        assert combo.has_local_legs is True
        assert "🛵 Door-to-Door" in combo.badges

    def test_has_local_legs_false_by_default(self, sample_segment_train):
        combo = RouteCombo(
            id="C", segments=[sample_segment_train],
            total_price=350_000, total_duration_minutes=510,
            waiting_time_minutes=0,
        )
        assert combo.has_local_legs is False

    def test_total_duration_str(self, sample_segment_train):
        combo = RouteCombo(
            id="C", segments=[sample_segment_train],
            total_price=350_000, total_duration_minutes=510,
            waiting_time_minutes=0,
        )
        assert combo.total_duration_str == "8j 30m"


# ─────────────────────────────────────────────────────────────────────────────
#  SearchCriteria
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchCriteria:
    def test_normalizes_origin_and_destination(self):
        sc = SearchCriteria(origin="  jakarta  ", destination="surabaya",
                            departure_date="2026-05-15")
        assert sc.origin == "Jakarta"
        assert sc.destination == "Surabaya"

    def test_invalid_passengers_raises(self):
        with pytest.raises(ValueError):
            SearchCriteria(origin="Jakarta", destination="Surabaya",
                           departure_date="2026-05-15", passengers=0)

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            SearchCriteria(origin="Jakarta", destination="Surabaya",
                           departure_date="2026-05-15",
                           transport_modes=["flight", "submarine"])

    def test_include_local_legs_defaults_false(self):
        sc = SearchCriteria(origin="Jakarta", destination="Surabaya",
                            departure_date="2026-05-15")
        assert sc.include_local_legs is False


# ─────────────────────────────────────────────────────────────────────────────
#  OptimizerResult
# ─────────────────────────────────────────────────────────────────────────────

class TestOptimizerResult:
    def test_empty_result(self):
        sc = SearchCriteria(origin="Jakarta", destination="Surabaya",
                            departure_date="2026-05-15")
        result = OptimizerResult(criteria=sc, all_combos=[])
        assert result.total_options == 0
        assert result.direct_options == []
        assert result.multimodal_options == []

    def test_split_direct_vs_multimodal(self, sample_segment_train, sample_segment_flight):
        sc = SearchCriteria(origin="Jakarta", destination="Surabaya",
                            departure_date="2026-05-15")
        c1 = RouteCombo(id="C1", segments=[sample_segment_train],
                        total_price=350_000, total_duration_minutes=510,
                        waiting_time_minutes=0)
        c2 = RouteCombo(id="C2", segments=[sample_segment_train, sample_segment_flight],
                        total_price=1_250_000, total_duration_minutes=700,
                        waiting_time_minutes=85)
        result = OptimizerResult(criteria=sc, all_combos=[c1, c2])
        assert result.total_options == 2
        assert len(result.direct_options) == 1
        assert len(result.multimodal_options) == 1
