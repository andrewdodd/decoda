from unittest.mock import Mock

import pytest

from decoda.well_known import *


def test_location_fmt():
    assert location_fmt(0x00) == "1st axle, 1st tire"
    assert location_fmt(0xFF) == "Not available"
    assert location_fmt(0x23) == "3rd axle, 4th tire"
    assert location_fmt(0x11) == "2nd axle, 2nd tire"


def test_refers_to_spn():
    try:
        assert refers_to_spn(0) == "SPN 0"
        assert (
            refers_to_spn(22)
            == "SPN 22 - Engine Extended Crankcase Blow-by Pressure"
        )
    except FileNotFoundError:
        pytest.skip("Unable to find a spec file")


class TestConditionallyApplies:
    def test_it_raises_error_if_conditional_on_spn_not_decoded(self):
        with pytest.raises(ValueError) as e:
            conditionally_applies(
                0x00,
                already_decoded=[Mock(id=9999)],
                custom_args={"conditional_on_spn": 1234, "applies_if": 4321},
            )
        assert str(e.value) == "conditional on SPN 1234, but not found"

    @pytest.mark.parametrize(
        "custom_args",
        [
            {},
            {"conditional_on_spn": 1234},
            {"applies_if": 9999},
        ],
    )
    def test_it_raises_bad_config_if_missing_config(self, custom_args):
        with pytest.raises(ValueError) as e:
            conditionally_applies(
                0x00, already_decoded=[Mock(id=9999)], custom_args=custom_args
            )
        assert str(e.value) == "bad config"

    def test_it_raises_error_if_no_decoded_values_provided(self):
        with pytest.raises(ValueError) as e:
            conditionally_applies(
                0x00,
                already_decoded=[],
                custom_args={"conditional_on_spn": 1234, "applies_if": 4321},
            )
        assert str(e.value) == "no values decoded"

    def test_it_returns_none_if_decoded_value_does_not_match_applies_if(self):
        value = conditionally_applies(
            0x00,
            already_decoded=[Mock(id=9999)],
            custom_args={"conditional_on_spn": 9999, "applies_if": 4321},
        )
        assert value is None

    def test_it_returns_value_from_non_custom_alternative_if_matches_applies_if(
        self,
    ):
        non_custom_alternative = Mock()
        non_custom_alternative.decode_from_raw.return_value = [
            {"value": "the return value"}
        ]
        value = conditionally_applies(
            0x00,
            already_decoded=[Mock(id=9999, value="decoded value")],
            custom_args={
                "conditional_on_spn": 9999,
                "applies_if": "decoded value",
            },
            non_custom_alternative=non_custom_alternative,
        )
        assert value == "the return value"


def test_fmi():
    # yapf:disable
    assert (
        fmi(0)
        == "Data Valid But Above Normal Operational Range - Most Severe Level"
    )
    assert (
        fmi(1)
        == "Data Valid But Below Normal Operational Range - Most Severe Level"
    )
    assert fmi(2) == "Data Erratic, Intermittent Or Incorrect"
    assert fmi(3) == "Voltage Above Normal, Or Shorted To High Source"
    assert fmi(4) == "Voltage Below Normal, Or Shorted To Low Source"
    assert fmi(5) == "Current Below Normal Or Open Circuit"
    assert fmi(6) == "Current Above Normal Or Grounded Circuit"
    assert fmi(7) == "Mechanical System Not Responding Or Out Of Adjustment"
    assert fmi(8) == "Abnormal Frequency Or Pulse Width Or Period"
    assert fmi(9) == "Abnormal Update Rate"
    assert fmi(10) == "Abnormal Rate Of Change"
    assert fmi(12) == "Bad Intelligent Device Or Component"
    assert fmi(13) == "Out Of Calibration"
    assert fmi(14) == "Special Instructions"
    assert (
        fmi(15)
        == "Data Valid But Above Normal Operating Range - Least Severe Level"
    )
    assert (
        fmi(16)
        == "Data Valid But Above Normal Operating Range - Moderately Severe Level"
    )
    assert (
        fmi(17)
        == "Data Valid But Below Normal Operating Range - Least Severe Level"
    )
    assert (
        fmi(18)
        == "Data Valid But Below Normal Operating Range - Moderately Severe Level"
    )
    assert fmi(19) == "Received Network Data In Error"
    assert fmi(20) == "Data Drifted High"
    assert fmi(21) == "Data Drifted Low"
    assert fmi(22) == "Reserved For SAE Assignment"
    assert fmi(30) == "Reserved For SAE Assignment"
    assert fmi(31) == "Condition Exists"
    # yapf:enable
    with pytest.raises(ValueError) as e:
        fmi(32)
    assert str(e.value) == "Only 5-bit value allowed"
    with pytest.raises(ValueError) as e:
        fmi(-1)
    assert str(e.value) == "Only 5-bit value allowed"


def test_fmi_not_available_variant():
    assert fmi_na(31) == "Not available"


def test_fmi_zero_variant():
    assert fmi_zero(0) == "No fault active"
    assert fmi_zero(1) == "Fault present"
    assert fmi_zero(31) == "Fault present"
