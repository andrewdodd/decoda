from unittest.mock import patch, sentinel

import pytest

from decoda import *

BL8 = BitLength(8)


class TestScalarValue:
    def test_it_decodes_without_anything(self):
        sv = scalar_value_from_dict({"bit_length": 8})
        result, _ = sv.decode_from_raw(b"\0", "1", False, -1)
        assert result == {"value": 0, "raw": 0, "display_value": "0"}
        result, _ = sv.decode_from_raw(b"\x7b", "1", False, -1)
        assert result == {"value": 123, "raw": 123, "display_value": "123"}

    def test_it_includes_units_in_display(self):
        sv = scalar_value_from_dict({"units": "XYZs", "bit_length": 8})
        result, _ = sv.decode_from_raw(b"\x7b", "1", False, -1)
        assert result["display_value"] == "123 XYZs"

    def test_it_scales_if_included(self):
        sv = scalar_value_from_dict({"resolution": 5, "bit_length": 8})
        result, _ = sv.decode_from_raw(b"\x0a", "1", False, -1)
        assert result["raw"] == 10
        assert result["value"] == 50

    def test_it_scales_and_offsets(self):
        sv = scalar_value_from_dict(
            {
                "resolution": 0.125,
                "offset": -123,
                "bit_length": 16,
            }
        )  # yapf: disable
        result, _ = sv.decode_from_raw(b"\x0a\0", "1", False, -1)
        assert result["value"] == (-123 + 10 * 0.125)
        result, _ = sv.decode_from_raw(b"\x64\0", "1", False, -1)
        assert result["value"] == (-123 + 100 * 0.125)
        result, _ = sv.decode_from_raw(b"\xe7\x03", "1", False, -1)
        assert result["value"] == (-123 + 999 * 0.125)

    def test_it_clips_to_min_after_scaling_and_offset(self):
        sv = scalar_value_from_dict(
            {
                "units": "XYZs",
                "data_range": {"min": 10},
                "resolution": 2,
                "offset": 5,
                "bit_length": 8,
            }
        )  # yapf: disable
        result, _ = sv.decode_from_raw(b"\2", "1", False, -1)
        assert result == {
            "value": 10,
            "raw": 2,
            "display_value": "10 XYZs (encoded value 9 XYZs was clipped to min)",
        }

    def test_it_clips_to_max_after_scaling_and_offset(self):
        sv = scalar_value_from_dict(
            {
                "units": "XYZs",
                "data_range": {"max": 10},
                "resolution": 3.3,
                "offset": 5,
                "bit_length": 8,
            }
        )  # yapf: disable
        result, _ = sv.decode_from_raw(b"\2", "1", False, -1)
        assert result == {
            "value": 10,
            "raw": 2,
            "display_value": "10 XYZs (encoded value 11.6 XYZs was clipped to max)",
        }  # yapf: disable

    def test_it_raises_error_if_min_and_max_not_correct(self):
        with pytest.raises(ValueError) as e:
            scalar_value_from_dict(
                {"data_range": {"min": 10, "max": 10}, "bit_length": 8}
            )
        assert str(e.value) == "min must be less than max"

    def test_it_ignores_min_and_max_if_requested(self):
        sv = scalar_value_from_dict(
            {
                "units": "XYZs",
                "data_range": {"min": 1, "max": 10},
                "resolution": 1,
                "offset": -5,
                "bit_length": 8,
            }
        )  # yapf: disable
        result, _ = sv.decode_from_raw(
            b"\0", "1", False, -1, ignore_range=True
        )
        assert result["value"] == -5
        result, _ = sv.decode_from_raw(
            b"\x14", "1", False, -1, ignore_range=True
        )
        assert result["value"] == 15

    @pytest.mark.parametrize(
        ["bit_length", "byte_stream", "display_value_suffix"],
        [
            (8, b"\xff", ""),
            (16, b"\x00\xff", " (0)"),
            (16, b"\x05\xff", " (5)"),
            (32, b"\x00\x00\x00\xff", " (0)"),
            (32, b"\x05\x00\x00\xff", " (5)"),
        ],
    )
    def test_it_reports_not_available_when_in_FF_range(
        self, bit_length, byte_stream, display_value_suffix
    ):
        sut = scalar_value_from_dict(
            {
                "units": "XYZs",
                "bit_length": bit_length,
            }
        )
        result, _ = sut.decode_from_raw(
            byte_stream, "1", False, -1, ignore_range=True
        )
        assert result["value"] == "Not available"
        assert (
            result["display_value"] == "Not available" + display_value_suffix
        )

    @pytest.mark.parametrize(
        ["bit_length", "byte_stream", "display_value_suffix"],
        [
            (8, b"\xfe", ""),
            (16, b"\x00\xfe", " (0)"),
            (16, b"\x05\xfe", " (5)"),
            (32, b"\x00\x00\x00\xfe", " (0)"),
            (32, b"\x05\x00\x00\xfe", " (5)"),
        ],
    )
    def test_it_reports_error_indicator_when_in_FE_range(
        self, bit_length, byte_stream, display_value_suffix
    ):
        sut = scalar_value_from_dict(
            {
                "units": "XYZs",
                "bit_length": bit_length,
            }
        )
        result, _ = sut.decode_from_raw(
            byte_stream, "1", False, -1, ignore_range=True
        )
        assert result["value"] == "Error indicator"
        assert (
            result["display_value"] == "Error indicator" + display_value_suffix
        )

    @pytest.mark.parametrize(
        ["bit_length", "byte_stream", "display_value_suffix"],
        [
            (8, b"\xfb", ""),
            (16, b"\x00\xfb", " (0)"),
            (16, b"\x05\xfb", " (5)"),
            (16, b"\xff\xfd", " (767)"),
            (32, b"\x00\x00\x00\xfb", " (0)"),
            (32, b"\x05\x00\x00\xfb", " (5)"),
            (32, b"\xff\xff\xff\xfd", " (50331647)"),
        ],
    )
    def test_it_reports_parameter_indicator_when_in_FB_to_FE_range(
        self, bit_length, byte_stream, display_value_suffix
    ):
        sut = scalar_value_from_dict(
            {
                "units": "XYZs",
                "bit_length": bit_length,
            }
        )
        result, _ = sut.decode_from_raw(
            byte_stream, "1", False, -1, ignore_range=True
        )
        assert result["value"] == "Parameter specific indicator"
        assert (
            result["display_value"]
            == "Parameter specific indicator" + display_value_suffix
        )

    def test_it_requires_positive_max_len(self):
        with pytest.raises(ValueError) as e:
            scalar_value_from_dict({"bit_length": -1})
        assert str(e.value) == "must have positive bit length"


class TestEncodedValue:
    def test_it_decodes_to_available_encodings(self):
        ev = EncodedValue({0: "Off", 1: "On"}, BitLength(1))
        result, _ = ev.decode_from_raw(b"\0", "1", False, -1)
        assert result == {"value": "Off", "raw": 0, "display_value": "Off (0)"}
        result, _ = ev.decode_from_raw(b"\1", "1", False, -1)
        assert result == {"value": "On", "raw": 1, "display_value": "On (1)"}

    def test_it_decodes_unknown_encodings_to_something(self):
        ev = EncodedValue({0: "Off", 1: "On"}, BitLength(2))
        result, _ = ev.decode_from_raw(b"\2", "1", False, -1)
        assert result == {
            "value": None,
            "raw": 2,
            "display_value": "No encoding (2)",
        }

    def test_it_raises_error_if_there_are_no_encodings(self):
        with pytest.raises(ValueError) as e:
            EncodedValue({}, None)
        assert str(e.value) == "must have at least 1 encoding"

    def test_it_handles_ints_and_strings_in_encoding_keys(self):
        ev = EncodedValue({"0": "Off", 1: "On"}, BitLength(1))
        result, _ = ev.decode_from_raw(b"\0", "1", False, -1)
        assert result == {"value": "Off", "raw": 0, "display_value": "Off (0)"}
        result, _ = ev.decode_from_raw(b"\1", "1", False, -1)
        assert result == {"value": "On", "raw": 1, "display_value": "On (1)"}

    def test_it_handles_ranges_in_encoding_keys(self):
        ev = EncodedValue(
            {
                "0": "North",
                "1": "South",
                "2": "East",
                "3": "West",
                "4": "In",
                "5": "Out",
                "6-15": "Agency defined",
            },
            BitLength(4),
        )

        result, _ = ev.decode_from_raw(b"\0", "1", False, -1)
        assert result == {
            "value": "North",
            "raw": 0,
            "display_value": "North (0)",
        }
        result, _ = ev.decode_from_raw(b"\x0a", "1", False, -1)
        assert result == {
            "value": "Agency defined",
            "raw": 10,
            "display_value": "Agency defined (10)",
        }
        result, _ = ev.decode_from_raw(b"\x0e", "1", False, -1)
        assert result == {
            "value": "Agency defined",
            "raw": 14,
            "display_value": "Agency defined (14)",
        }

    def test_it_requires_positive_max_len(self):
        encodings = {"0": "Don't care"}
        with pytest.raises(ValueError) as e:
            EncodedValue(encodings, BitLength(None))
        assert str(e.value) == "must have positive bit length"

        with pytest.raises(ValueError) as e:
            EncodedValue(encodings, BitLength(-1))
        assert str(e.value) == "must have positive bit length"


class TestBitLength:
    @pytest.mark.parametrize("bit_length", [1, 7, 9])
    def test_it_cannot_be_constructed_with_non_byte_boundary_length(
        self, bit_length
    ):
        with pytest.raises(ValueError) as e:
            BitLength(bit_length, True)
        assert str(
            e.value
        ) == "bit_length ({}) must be an 8-bit multiple".format(bit_length)


class TestTextValue:
    def test_it_decodes(self):
        tv = TextValue(BitLength(None, True), "*")
        result, _ = tv.decode_from_raw(bytes("hello", "ascii"), "1", False, -1)
        assert result == {
            "value": "hello",
            "raw": "hello",
            "display_value": "hello",
        }

    def test_it_raises_error_if_not_variable_and_insufficient_bytes(self):
        tv = TextValue(BitLength(5 * 8))

        with pytest.raises(ValueError) as e:
            tv.decode_from_raw(b"\1", "1", False, -1)

        assert str(e.value) == "insufficent bytes"

    def test_it_raises_error_if_variable_and_neither_delimiter_or_length_spn_supplied(
        self,
    ):
        with pytest.raises(ValueError) as e:
            TextValue(BitLength(None, True))

        assert (
            str(e.value)
            == "Variable length SPN must specify delimiter or length SPN"
        )

    @pytest.mark.parametrize("delimiter", ["0x00", "0x2a", "0xa"])
    def test_it_uses_provided_delimiter(self, delimiter):
        tv = TextValue(BitLength(None, True), delimiter)
        inp = (
            bytes("hello", "ascii")
            + bytes([int(delimiter, 16)])
            + bytes("world", "ascii")
        )
        result, end_byte_idx = tv.decode_from_raw(inp, "1", False, -1)
        assert result == {
            "value": "hello",
            "raw": "hello",
            "display_value": "hello",
        }
        assert end_byte_idx == 5

    @pytest.mark.parametrize(
        ["length", "expected", "expected_idx"],
        [
            (4, "hell", 3),
            (5, "hello", 4),
        ],
    )
    def test_it_decodes_using_already_decoded_length(
        self, length, expected, expected_idx
    ):
        tv = TextValue(BitLength(None, True), None, 1234)
        mockOneTwoThreeFourResult = DecodedSPN.build(
            spn=SPN(id=1234, name=None, description=None, value_decoder=None),
            value=length,
            raw=None,
            display_value=None,
        )
        result, end_byte_idx = tv.decode_from_raw(
            bytes("helloworld", "ascii"),
            "1",
            False,
            -1,
            already_decoded=[mockOneTwoThreeFourResult],
        )
        assert result["value"] == expected
        assert end_byte_idx == expected_idx


class TestByteArrayValue:
    def test_it_decode_fixed_bit_length(self):
        # SPN 2550 - Manufacturer Specific Information (PropA_PDU1)
        # Bitlength - 14280
        bv = ByteArrayValue(BitLength(14280))
        val = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
        result, _ = bv.decode_from_raw(val, "1", False, -1)
        assert result["value"] == val
        assert result["raw"] == val
        assert result["display_value"] == "0102030405060708090a"

    def test_it_decode_variable_length(self):
        bv = ByteArrayValue(BitLength(14280, True))
        val = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a"
        result, _ = bv.decode_from_raw(val, "1", False, -1)
        assert result["value"] == val
        assert result["raw"] == val
        assert result["display_value"] == "0102030405060708090a"


class TestSPNDecoding:
    def test_it_decodes_scalar_values(self):
        spn = SPN(1, "Name", "Desc", scalar_value_from_dict({"bit_length": 8}))
        result, _ = spn.decode(bytes([0]), "1", False, -1)
        assert result == DecodedSPN.build(spn, 0, 0, "0")
        result, _ = spn.decode(bytes([123]), "1", False, -1)
        assert result == DecodedSPN.build(spn, 123, 123, "123")

    def test_it_decodes_encoded_values(self):
        spn = SPN(1, "Name", "Desc", EncodedValue({1: "On", 0: "Off"}, BL8))

        result, _ = spn.decode(bytes([0]), "1", False, -1)
        assert result == DecodedSPN.build(spn, 0, "Off", "Off (0)")
        result, _ = spn.decode(bytes([1]), "1", False, -1)
        assert result == DecodedSPN.build(spn, 1, "On", "On (1)")

    def test_it_decodes_text_values(self):
        bitLen40 = BitLength(40)
        spn = SPN(1, "Name", "Desc", TextValue(bitLen40))

        result, _ = spn.decode(bytes("hello", "ascii"), "1", False, -1)
        assert result == DecodedSPN.build(spn, "hello", "hello", "hello")

    def test_it_raises_an_error_if_value_does_not_have_enough_bits(self):
        spn = SPN(
            1, "Name", "Desc", scalar_value_from_dict({"bit_length": 16})
        )

        with pytest.raises(ValueError) as e:
            spn.decode(bytes([0]), "1", False, -1)

        assert (
            str(e.value)
            == "not enough bits for SPN - need 16, from 0.0 in payload[b'00']"
        )


class TestSPNConstruction:
    @patch("decoda.spec_loader.scalar_value_from_dict")
    def test_it_builds_a_scalar_decoding_spn(self, scalar_value_from_dict):
        d = {
            "id": 4151,
            "name": "A name of an SPN",
            "bit_length": 16,
            "data_range": {"min": -273, "max": 1734.96875},
            "offset": -273,
            "resolution": 0.03125,
            "units": "deg C",
        }  # yapf: disable
        result = spn_from_dict(d)
        assert result.id == 4151
        assert result.name == "A name of an SPN"
        assert result.description == ""
        assert result.value_decoder == scalar_value_from_dict.return_value
        scalar_value_from_dict.assert_called_with(d)

    @patch("decoda.spec_loader.EncodedValue")
    def test_it_builds_an_encoding_decoding_spn(self, EncodedValue):
        spn = spn_from_dict(
            {
                "id": 4309,
                "name": "A name of an SPN",
                "description": "",
                "bit_length": 2,
                "offset": "",
                "encodings": {
                    "0": "Reverse",
                    "1": "Forward",
                    "2": "Error indication",
                    "3": "Not available",
                },
            }
        )
        assert spn.id == 4309
        assert spn.name == "A name of an SPN"
        assert spn.description == ""
        assert spn.value_decoder == EncodedValue.return_value
        EncodedValue.assert_called_with(
            {
                "0": "Reverse",
                "1": "Forward",
                "2": "Error indication",
                "3": "Not available",
            },
            BitLength(2),
        )

    @patch("decoda.spec_loader.TextValue")
    def test_it_builds_a_text_decoding_spn(self, TextValue):
        spn = spn_from_dict(
            {
                "id": 4254,
                "name": "A name of an SPN",
                "description": "",
                "bit_length": 200,
                "offset": "",
                "data_range": {"min": 0, "max": 255},
                "units": "ASCII",  # THIS IS IMPORTANT
            }
        )  # yapf: disable
        assert spn.id == 4254
        assert spn.name == "A name of an SPN"
        assert spn.description == ""
        assert spn.value_decoder == TextValue.return_value
        TextValue.assert_called_with(
            BitLength(200), delimiter=None, length_spn=None
        )

    @patch("decoda.spec_loader.TextValue")
    def test_it_builds_a_text_decoding_spn_with_variable_length(
        self, TextValue
    ):
        spn = spn_from_dict(
            {
                "id": 4254,
                "name": "A name of an SPN",
                "bit_length": 200,
                "units": "ASCII",  # THIS IS IMPORTANT
                "variable": True,
                "delimiter": "*",
            }
        )  # yapf: disable
        assert spn.value_decoder == TextValue.return_value
        TextValue.assert_called_with(
            BitLength(200, True), delimiter="*", length_spn=None
        )

    @patch("decoda.spec_loader.TextValue")
    def test_it_builds_a_text_decoding_spn_with_length_spn(self, TextValue):
        spn = spn_from_dict(
            {
                "id": 4254,
                "name": "A name of an SPN",
                "bit_length": 200,
                "units": "ASCII",  # THIS IS IMPORTANT
                "variable": True,
                "length_spn": 1234,
            }
        )  # yapf: disable
        assert spn.value_decoder == TextValue.return_value
        TextValue.assert_called_with(
            BitLength(200, True), delimiter=None, length_spn=1234
        )
