"""Property-based tests for utils.settings — backend decode/encode stability."""

import json
from hypothesis import given, strategies as st

from utils.settings import (
    JsonFileSettingsBackend,
    SharedPreferencesSettingsBackend,
)

json_dict_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(
        st.text(), st.integers(), st.booleans(), st.floats(allow_nan=False)
    ),
    min_size=1,
    max_size=20,
)


class TestSharedPreferencesDecodeRoundtrip:
    @given(json_dict_strategy)
    def test_encode_decode_dict(self, data):
        # Dict input pass-through
        decoded = SharedPreferencesSettingsBackend._decode_payload(data)
        assert decoded == data

    @given(json_dict_strategy)
    def test_encode_decode_json_string(self, data):
        encoded = json.dumps(data)
        decoded = SharedPreferencesSettingsBackend._decode_payload(encoded)
        assert decoded == data


class TestJsonSettingsBackendRoundtrip:
    @given(json_dict_strategy)
    def test_dict_stable_through_json(self, data):
        encoded = json.dumps(data)
        decoded = json.loads(encoded)
        assert decoded == data
