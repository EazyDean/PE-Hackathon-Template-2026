from app.seed.loader import _parse_bool
from app.seed.loader import _parse_timestamp


def test_parse_bool_handles_seed_style_values():
    assert _parse_bool("True") is True
    assert _parse_bool("false") is False


def test_parse_timestamp_reads_seed_format():
    parsed = _parse_timestamp("2025-08-13 02:22:32")

    assert parsed.year == 2025
    assert parsed.month == 8
    assert parsed.day == 13
