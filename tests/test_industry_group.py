import pytest

from decoda import *


def test_it_has_all_industry_groups(spec):
    for idx, description in enumerate(
        [
            "Global, applies to all",
            "On-Highway Equipment",
            "Agricultural and Forestry Equipment",
            "Construction Equipment",
            "Marine",
            "Industrial-Process Control-Stationary (Gen-Sets)",
            "Reserved for future assignment by SAE",
            "Reserved for future assignment by SAE",
        ]
    ):
        assert spec.IndustryGroups.get_by_id(idx).description == description


def test_global_preferred_addresses(spec):
    assert spec.preferred_address_name(0) == "Engine #1"
    assert spec.preferred_address_name(251) == "On-Board Data Logger"
    assert spec.preferred_address_name(252) == "Reserved for Experimental Use"
    assert spec.preferred_address_name(253) == "Reserved for OEM"
    assert spec.preferred_address_name(254) == "Null Address"
    assert spec.preferred_address_name(255) == "GLOBAL (All-Any Node)"


def test_on_highway_equipment_preferred_addresses(spec):
    # test it works for ranges
    assert (
        spec.preferred_address_name(128, 1)
        == "Reserved for future assignment by SAE but available for use by self configurable ECUs"
    )
    assert (
        spec.preferred_address_name(129, 1)
        == "Reserved for future assignment by SAE but available for use by self configurable ECUs"
    )

    # test it works for specific
    assert spec.preferred_address_name(162, 1) == "Slope Sensor"

    # test it falls back to the global spec for addesses below 128
    assert spec.preferred_address_name(0, 1) == "Engine #1"


def test_it_returns_broadcast_address_for_neg_one(spec):
    assert spec.preferred_address_name(-1) == "Broadcast address"
    assert spec.preferred_address_name(-1, 1) == "Broadcast address"


def test_it_falls_back_to_global_address_if_not_specified_in_insdustry_group(
    spec,
):
    assert spec.preferred_address_name(251, 1) == "On-Board Data Logger"
    assert spec.preferred_address_name(251, 2) == "On-Board Data Logger"
    assert spec.preferred_address_name(251, 3) == "On-Board Data Logger"
