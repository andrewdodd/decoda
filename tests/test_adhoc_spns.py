import pytest

from decoda import *


def test_spn899(spec):
    sut = spec.SPNs.get_by_id(899)
    test_input = {
        b"\x00": "Low idle governor/no request (default mode)",
        b"\x01": "Accelerator pedal/operator selection",
        b"\x02": "Cruise control",
        b"\x03": "PTO governor",
        b"\x04": "Road speed governor ",
        b"\x05": "ASR control ",
        b"\x06": "Transmission control ",
        b"\x07": "ABS control",
        b"\x08": "Torque limiting",
        b"\x09": "High speed governor ",
        b"\x0a": "Braking system ",
        b"\x0b": "Remote accelerator ",
        b"\x0c": "Service procedure ",
        b"\x0d": "Not defined",
        b"\x0e": "Other",
        b"\x0f": "Not available",
    }
    for encoded, expected in test_input.items():
        decoded, _ = sut.decode(encoded, "1", False, -1)
        assert decoded.value == expected


def test_location_spns(spec):
    for spn in range(927, 929):
        sut = spec.SPNs.get_by_id(spn)
        decoded, _ = sut.decode(b"\x23", "1", False, -1)
        assert decoded.value == "3rd axle, 4th tire"


def custom_fmt_func(value, *args, **kwargs):
    return {0: "ZERO", 1: "Een", 2: "Deux"}.get(value, value)


# yapf: disable
@pytest.mark.parametrize(
    ['input_value', 'raw', 'value', 'display_value'], [
    [      b"\x00",    0,   "ZERO", "ZERO (0)"],
    [      b"\x01",    1,    "Een", "Een (1)"],
    [      b"\x02",    2,   "Deux", "Deux (2)"],
    [      b"\x03",    3,        3, "3 (3)"],
])
# yapf: enable
def test_any_function_can_be_defined(input_value, value, raw, display_value):
    sut = make_decoder_from_spn_dict(
        {"bit_length": 8, "custom": "tests.test_adhoc_spns.custom_fmt_func"}
    )
    decoded, _ = sut.decode_from_raw(input_value, "1", False, -1)
    assert decoded["value"] == value
    assert decoded["raw"] == raw
    assert decoded["display_value"] == display_value


def test_it_falls_back_if_custom_function_not_found():
    sut = make_decoder_from_spn_dict(
        {
            "bit_length": 8,
            "custom": "does_not_exist",
            "encodings": {"0": "Zilch", "1-255": "Better than nothing"},
        }
    )
    decoded, _ = sut.decode_from_raw(b"\x00", "1", False, -1)
    assert decoded["value"] == "Zilch"
    decoded, _ = sut.decode_from_raw(b"\x1d", "1", False, -1)
    assert decoded["value"] == "Better than nothing"


@pytest.mark.parametrize(
    "spn", [4307, 5150, 5151, 5155, 5227] + list(range(5159, 5194))
)
def test_tractor_limit_statuses(spn, spec):
    sut = spec.SPNs.get_by_id(spn)
    decoded, _ = sut.decode(b"\x00", "1", False, -1)
    assert decoded.value == "Not limited"
    decoded, _ = sut.decode(b"\x03", "1", False, -1)
    assert (
        decoded.value
        == "Limited low (only higher command values result in a change)"
    )


@pytest.mark.parametrize("spn", [5152, 5153, 5154, 5156, 5157, 5158])
def test_tractor_request_status(spn, spec):
    sut = spec.SPNs.get_by_id(spn)
    decoded, _ = sut.decode(b"\x00", "1", False, -1)
    assert (
        decoded.value
        == "External request accepted. No subsequent operator intervention"
    )
    decoded, _ = sut.decode(b"\x03", "1", False, -1)
    assert decoded.value == "Not available (parameter not supported)"


def test_failure_mode_identifier(spec):
    sut = spec.SPNs.get_by_id(1215)
    decoded, _ = sut.decode(b"\x00", "1", False, -1)
    assert (
        decoded.value
        == "Data Valid But Above Normal Operational Range - Most Severe Level"
    )
    decoded, _ = sut.decode(b"\x03", "1", False, -1)
    assert decoded.value == "Voltage Above Normal, Or Shorted To High Source"
    decoded, _ = sut.decode(b"\x16", "1", False, -1)
    assert decoded.value == "Reserved For SAE Assignment"
    decoded, _ = sut.decode(b"\x1e", "1", False, -1)
    assert decoded.value == "Reserved For SAE Assignment"
    decoded, _ = sut.decode(b"\x1f", "1", False, -1)
    assert decoded.value == "Condition Exists"
