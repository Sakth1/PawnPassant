"""Property-based tests for ui.home_page — categorization, preset ordering."""

from hypothesis import given, strategies as st

from ui.home_page import HomeView
from utils.constants import CATEGORY_ORDER


class TestCategorizationInvariants:
    @given(st.integers(min_value=0, max_value=300))
    def test_categorization_always_returns_valid_category(self, minutes):
        cat = HomeView._categorize_time_control(minutes)
        assert cat in CATEGORY_ORDER

    def test_categorization_monotonic(self):
        """Higher minutes never produce a faster category."""
        for low_min, high_min in [(1, 3), (2, 6), (5, 21), (20, 60)]:
            low_cat = HomeView._categorize_time_control(low_min)
            high_cat = HomeView._categorize_time_control(high_min)
            low_idx = CATEGORY_ORDER.index(low_cat)
            high_idx = CATEGORY_ORDER.index(high_cat)
            assert low_idx <= high_idx


class TestPresetsInvariants:
    def test_all_presets_have_required_keys(self):
        view = HomeView()
        for preset in view.presets:
            assert "key" in preset
            assert "label" in preset
            assert "minutes" in preset
            assert "increment" in preset
            assert "value" in preset
            assert "category" in preset

    def test_presets_sorted_by_category_order(self):
        view = HomeView()
        categories = [p["category"] for p in view.presets]
        indices = [CATEGORY_ORDER.index(str(c)) for c in categories]
        assert indices == sorted(indices)

    def test_select_preset_updates_key(self):
        view = HomeView()
        for preset in view.presets:
            key = preset["key"]
            view._select_preset(key)
            assert view.selected_preset_key == key
