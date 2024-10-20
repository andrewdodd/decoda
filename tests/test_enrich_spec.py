import pytest

from decoda.sae_spec_converter.enrich_spec import (
    update_datarange,
    update_offset,
    update_well_known,
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


@pytest.mark.parametrize(
    ["name", "description", "expected_well_known"],
    [
        ("Fault Mode Indicator", "", "decoda.well_known.fmi_ce"),
        ("Anything FMI", "", "decoda.well_known.fmi_ce"),
        (
            "Anything FMI",
            "A value of 31 is sent to indicate that no failure has been detected or this parameter is not supported",
            "decoda.well_known.fmi_na",
        ),  # 3222
        (
            "Anything FMI",
            "31 is sent to indicate that no failure",
            "decoda.well_known.fmi_na",
        ),  # 3222
        (
            "Anything FMI",
            "parameter will be set to 0",
            "decoda.well_known.fmi_zero",
        ),  # 23566
        (
            "Anything FMI",
            "parameter shall be set to 0",
            "decoda.well_known.fmi_zero",
        ),  # 23387,
    ],
)
def test_it_updates_well_known_fmi_function(
    name, description, expected_well_known
):
    assert (
        update_well_known({"name": name, "description": description}).get(
            "custom"
        )
        == expected_well_known
    )
