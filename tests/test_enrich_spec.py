import pytest

from decoda.sae_spec_converter.enrich_spec import (
    update_datarange,
    update_offset,
)


@pytest.mark.parametrize(
    ["units", "data_range", "expected"],
    [
        ("", "", ""),
        ("abcs", "12 to 23 abcs", {"min": 12, "max": 23}),
        ("abcs", "1.0 to 9.0 abcs", {"min": 1.0, "max": 9.0}),
        ("abcs", "1 234 to 9 999 abcs", {"min": 1234, "max": 9999}),
        (
            "don't care",
            "0 to 125.498 046 875 km/L",
            {"min": 0, "max": 125.498046875},
        ),
    ],
)
def test_update_datarange_converts_as_expected(units, data_range, expected):
    assert (
        update_datarange({"units": units, "data_range": data_range})[
            "data_range"
        ]
        == expected
    )


@pytest.mark.parametrize(
    ["offset", "expected"],
    [
        ("", ""),
        ("-1234", -1234),
        ("-1 234", -1234),
        ("-1,234 mm", -1234),
        ("0 Watt-hour", 0),
    ],
)
def test_it_updates_offet(offset, expected):
    assert update_offset({"offset": offset})["offset"] == expected
