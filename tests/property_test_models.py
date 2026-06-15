"""Property-based tests for utils.models — AppSettings roundtrip and validation."""

from hypothesis import given, assume

from utils.models import AppSettings
from tests.property_strategies import app_settings, non_negative_ints


class TestAppSettingsRoundtrip:
    @given(app_settings)
    def test_to_dict_from_dict_roundtrip(self, settings):
        d = settings.to_dict()
        restored = AppSettings.from_dict(d)
        assert settings == restored

    @given(app_settings)
    def test_updated_returns_equivalent(self, settings):
        modified = settings.updated()
        assert modified == settings

    @given(app_settings)
    def test_updated_does_not_mutate_original(self, settings):
        original = settings
        settings.updated(show_legal_moves=not settings.show_legal_moves)
        assert settings == original

    @given(app_settings)
    def test_from_dict_ignores_unknown_keys(self, settings):
        d = settings.to_dict()
        d["nonexistent_key"] = "should_be_ignored"
        restored = AppSettings.from_dict(d)
        assert settings == restored
