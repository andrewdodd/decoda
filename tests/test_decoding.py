import json

import pytest

from decoda import *


def test_mask():
    assert mask(0) == 0
    assert mask(1) == 0b1
    assert mask(2) == 0b11
    assert mask(3) == 0b111
    assert mask(9) == 0b111111111
    assert mask(50) == 0b11111111111111111111111111111111111111111111111111


class TestRegularPackedPGNs:
    def test_it_unpacks_PGN_0_Torque_Speed_Control_1(self, pgn_0):
        """This is the most basic PGN...which includes encoded values and regular values"""
        sut = pgn_0
        assert sut.id == 0
        assert sut.name == "Torque/Speed Control 1"

        inp = (0x123456781AB7DEF0).to_bytes(8, "big")
        decoded = sut.decode(inp)

        assert len(decoded) == 10
        # 0x12 - 0b00010010
        assert (
            decoded[0].value
            == 'Torque control - Control torque to the included "desired torque" value.'
        )
        assert (
            decoded[1].value
            == "Transient Optimized for driveline disengaged and non-lockup conditions"
        )  # yapf: disable
        assert decoded[2].value == "High priority"
        # 0x5634 - 22068 == 2758.5
        assert decoded[3].value == 2758.5
        # 0x78 = 120
        assert decoded[4].value == -5

        # 0x1a - 0b00011010
        assert decoded[5].value == "500 ms transmission rate"
        assert decoded[6].value == "P4 = Road Speed Governor"

        assert decoded[7].raw == 7
        assert decoded[7].value == "0.875 %"

        # 0xde - not decoded
        # 0xf0 -
        assert decoded[8].value == 0
        assert decoded[9].value == 15

        for d in decoded:
            print("{:<45}: {}".format(d.name, d.display_value))
        # assert False

    def test_it_unpacks_PGN_61444_Electronic_Engine_Controller_1(
        self, pgn_61444
    ):
        """This is a common PGN"""
        sut = pgn_61444
        assert sut.id == 61444
        assert sut.name == "Electronic Engine Controller 1"

        inp = (0x123456781ABCDEF0).to_bytes(8, "big")
        decoded = sut.decode(inp)

        assert len(decoded) == 8
        assert decoded[0].value == "Cruise control"
        assert decoded[1].value == "0.125 %"
        assert decoded[2].value == -73
        assert decoded[3].value == -39
        assert decoded[4].value == 847.0
        assert decoded[5].value == 188
        assert decoded[6].value == "error"
        assert decoded[7].value == 115

        for d in decoded:
            print("{:<45}: {}".format(d.name, d.display_value))

        inp = (0xFFFF9100FDFFFFFF).to_bytes(8, "big")
        decoded = sut.decode(inp)

        assert len(decoded) == 8
        assert decoded[0].value == "Not available"
        assert decoded[1].value == "Not available"
        assert decoded[2].value == "Not available"
        assert decoded[3].value == 20
        assert decoded[4].value == "Parameter specific indicator"
        assert decoded[5].value == "Not available"
        assert decoded[6].value == "not available"
        assert decoded[7].value == "Not available"
        for d in decoded:
            print("{:<45}: {}".format(d.name, d.display_value))

        # assert False

    def test_it_unpacks_PGN_55552_MemoryAccessRequest(self, pgn_55552):
        """This PGN has a non-contigious SPN 1640"""
        sut = pgn_55552
        assert sut.id == 55552
        assert sut.name == "Memory Access Request"

        inp = (0x123456789ABCDEF0).to_bytes(8, "big")
        decoded = sut.decode(inp)

        assert len(decoded) == 6
        # 0x3412 = 0b0011 0100 0001 0010
        #            iiix ^^^x iiii iiii
        #              >> 0b 00100010010
        assert decoded[0].value == 0b00100010010
        assert decoded[1].raw == 2
        assert str(decoded[1]) == "SPN:1642: Command = Write"

        assert decoded[2].value == "Direct Spatial Addressing"
        # 0x9a7856 = 10123350
        assert decoded[3].value == 10123350
        # 0xbc = 188
        assert decoded[4].value == 188
        # 0xf0de = 61662
        assert decoded[5].value == 61662


class TestPGNsWithVariableText:
    def test_it_unpacks_with_one_variable_length(self, pgn_43008):
        sut = pgn_43008
        assert sut.id == 43008
        # NB unused byte here -------+
        #                            V
        inp = (
            bytes([3, 9, 0x12])
            + bytes("Abc123", "ascii")
            + bytes([0])
            + bytes("xyz", "ascii")
        )
        decoded = sut.decode(inp)

        assert decoded[0].raw == 3
        assert (
            decoded[0].value
            == "Overwrite display - The presently displayed information is to be overwritten with the transmitted information"
        )
        assert decoded[1].value == 0x12
        assert decoded[2].value == "Abc123"

    def test_it_unpacks_multiple_variable_length(self, pgn_64965):
        sut = pgn_64965
        assert sut.id == 64965
        decoded = sut.decode(bytes("hi*how*are**you*", "ascii"))

        assert decoded[0].value == "hi"
        assert decoded[1].value == "how"
        assert decoded[2].value == "are"
        assert decoded[3].value == ""
        assert decoded[4].value == "you"

    def test_it_unpacks_with_variable_text_as_well_as_regular(self, pgn_64958):
        sut = pgn_64958
        assert sut.id == 64958
        # TODO - This data is incorrect. I don't think the strings should be
        # delimited...instead it should be based on the lengths in 3071, 3072,
        # 3073
        decoded = sut.decode(bytes("\1\6\4\5Route*Run*Block", "ascii"))

        assert decoded[0].value == 1
        assert decoded[1].value == 6
        assert decoded[2].value == 4
        assert decoded[3].value == 5
        assert decoded[4].value == "Route*"
        assert decoded[5].value == "Run*"
        assert decoded[6].value == "Block"

    def test_it_unpacks_with_comma_specs(self, pgn_10240):
        sut = pgn_10240
        assert sut.id == 10240

        inp = (0x123456781AB7DEF0).to_bytes(8, "big")
        decoded = sut.decode(inp)
        assert decoded[0].raw == 0x12
        assert decoded[1].raw == 0x04
        assert decoded[2].raw == 0x563
        assert decoded[3].raw == 0xA78


class TestPGNsWithRepeatableSPNs:
    def test_it_unpacks_PGN_65226_ActiveDiagnosticTroubleCodes(
        self, pgn_65226: PGN
    ):
        sut = pgn_65226
        assert sut.id == 65226
        assert sut.name == "Active Diagnostic Trouble Codes"

        #         1 2 3 4 5 6 7 8 9 10 ...
        inp = (0x5555B8041000BBBB6000).to_bytes(10, "big")
        decoded = sut.decode(inp)

        assert decoded[0].value == "Lamp On"
        assert decoded[1].value == "Lamp On"
        assert decoded[2].value == "Lamp On"
        assert decoded[3].value == "Lamp On"
        assert (
            decoded[4].value == "Fast Flash (2 Hz or faster, 50% duty cycle)"
        )
        assert (
            decoded[5].value == "Fast Flash (2 Hz or faster, 50% duty cycle)"
        )
        assert (
            decoded[6].value == "Fast Flash (2 Hz or faster, 50% duty cycle)"
        )
        assert (
            decoded[7].value == "Fast Flash (2 Hz or faster, 50% duty cycle)"
        )

        # First SPN
        assert decoded[8].raw == 0x004B8
        assert (
            decoded[8].value == "SPN 1208 - Engine Oil Filter Intake Pressure"
        )
        assert (
            decoded[8].display_value
            == "SPN 1208 - Engine Oil Filter Intake Pressure (1208)"
        )
        assert (
            decoded[9].value
            == "Data Valid But Above Normal Operating Range - Moderately Severe Level"
        )
        assert decoded[9].raw == 16
        assert decoded[10].value == 0
        assert (
            decoded[11].value
            == "means convert SPNs per the Version 4 definition below"
        )

        # Second SPN
        assert decoded[12].raw == 0x3BBBB
        assert decoded[12].value == "SPN 244667"
        assert decoded[12].display_value == "SPN 244667 (244667)"
        assert decoded[12].value == "SPN 244667"
        assert decoded[13].raw == 0
        assert (
            decoded[13].value
            == "Data Valid But Above Normal Operational Range - Most Severe Level"
        )
        assert decoded[14].value == 0
        assert (
            decoded[15].value
            == "means convert SPNs per the Version 4 definition below"
        )

    def test_it_unpacks_PGN_64912_AdvertisedEngineTorqueCurve(self, pgn_64912):
        sut = pgn_64912
        assert sut.id == 64912
        assert sut.name == "Advertised Engine Torque Curve"

        # First byte is standard and "point count"
        # following points are (speed, torque) pairs of 16-bit numbers
        inp = b"\x20\x12\x34\x56\x78\x9a\xbc\xde\xf0"
        decoded = sut.decode(inp)

        assert decoded[0].value == "SAE J1995"
        assert decoded[1].value == 2
        assert decoded[2].value == 0x3412 * 0.125
        assert str(decoded[2]) == "SPN:3560: AETC Speed Value = 1666.25"
        assert decoded[2].display_value == "1666.25 rpm"
        assert decoded[3].value == 0x7856
        assert str(decoded[3]) == "SPN:3561: AETC Torque value = 30806"
        assert decoded[3].display_value == "30806 Nm"
        assert decoded[4].value == 0xBC9A * 0.125
        assert str(decoded[4]) == "SPN:3560: AETC Speed Value = 6035.25"
        assert decoded[5].value == 0xF0DE
        assert str(decoded[5]) == "SPN:3561: AETC Torque value = 61662"


def test_all_SPNs():
    try:
        with open("./decoda_spec.json") as f:
            spec = json.load(f)
    except FileNotFoundError:
        pytest.skip("Unable to find a spec file")

    missing_bit_length = []
    errors = []
    for idx, spn in enumerate(spec["SPNs"]):
        try:
            spn_from_dict(spn)
        except MissingBitLength as e:
            missing_bit_length.append(e)
        except Exception as e:
            errors.append((idx, spn, e))

    assert len(errors) == 0
    assert len(missing_bit_length) < 1200


def test_all_PGNs():
    try:
        with open("./decoda_spec.json") as f:
            spec = json.load(f)
    except FileNotFoundError:
        pytest.skip("Unable to find a spec file")
    spn_specs = spec["SPNs"]
    spn_specs = [
        spn for spn in spn_specs if spn.get("bit_length") not in ("", None)
    ]
    spns = Repo(SPN, spn_from_dict, spn_specs)

    errors = []
    count = 0
    for idx, pgn in enumerate(spec["PGNs"]):
        try:
            pgn_from_dict(pgn, spns)
            count += 1
        except Exception as e:
            errors.append((idx, pgn, e))

    for _, pgn, error in errors:
        print("{} : {}".format(error, pgn))
    assert len(errors) == 0


@pytest.mark.parametrize(
    "pgn_id",
    [
        59392,
        60416,
        64793,
        64888,
        64889,
        64920,
        64921,
        65168,
        65208,
        65209,
        65251,
    ],
)
def test_pgns_can_decode(pgn_id, spec):
    pgn = spec.PGNs.get_by_id(pgn_id)
    inp = bytes([1] * 200)  # it's really long
    pgn.decode(inp)


def test_it_can_load_from_a_spec_file():
    try:
        spec = load_from_file("./decoda_spec.json")
    except FileNotFoundError:
        pytest.skip("Unable to find a spec file")
    assert spec.Manufacturers.get_by_id(2).name == "Allison Transmission, Inc."
    assert (
        spec.SPNs.get_by_id(22).name
        == "Engine Extended Crankcase Blow-by Pressure"
    )
    assert spec.PGNs.get_by_id(0).name == "Torque/Speed Control 1"
