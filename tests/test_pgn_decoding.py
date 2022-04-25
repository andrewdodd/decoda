import pytest

from decoda import *

BL8 = BitLength(8)


def test_it_decodes_single_byte_spns(pgn_1792: PGN):
    results = pgn_1792.decode((0x0).to_bytes(8, "big"))
    result_4087 = results[1]
    assert result_4087.raw == 0
    assert result_4087.value == 0
    assert result_4087.display_value == "0 kPa"

    results = pgn_1792.decode((0x0000010000000000).to_bytes(8, "big"))
    result_4087 = results[1]
    assert result_4087.raw == 1
    assert result_4087.value == 16
    assert result_4087.display_value == "16 kPa"

    results = pgn_1792.decode((0x0000FA0000000000).to_bytes(8, "big"))
    result_4087 = results[1]
    assert result_4087.value == 4000
    assert result_4087.display_value == "4000 kPa"


def test_it_decodes_multi_byte_spns(pgn_1792: PGN):
    results = pgn_1792.decode((0x0).to_bytes(8, "big"))
    result_4086 = results[0]
    assert result_4086.raw == 0
    assert result_4086.display_value == "0 kPa"

    results = pgn_1792.decode((0x0100000000000000).to_bytes(8, "big"))
    result_4087 = results[0]
    assert result_4087.value == 5
    assert result_4087.display_value == "5 kPa"

    results = pgn_1792.decode((64255).to_bytes(8, "little"))
    result_4087 = results[0]
    assert result_4087.value == 321275
    assert result_4087.display_value == "321275 kPa"

    results = pgn_1792.decode(0x1000000.to_bytes(8, "little"))
    result_4088 = results[2]
    assert result_4088.value == 5
    assert result_4088.display_value == "5 kPa"


class TestStartPositionValueExtractions:
    def test_it_extracts_whole_bytes(self):
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")

        #  0x12 0x34 0x56 0x78 0x9a 0xbc 0xde 0xf0
        assert (0x12, 0) == extract_value_at_location(inp, "1", BL8)
        assert (0x34, 1) == extract_value_at_location(inp, "2", BL8)
        assert (0x56, 2) == extract_value_at_location(inp, "3", BL8)
        assert (0xDE, 6) == extract_value_at_location(inp, "7", BL8)
        assert (0xF0, 7) == extract_value_at_location(inp, "8", BL8)

        assert (0x3412, 1) == extract_value_at_location(
            inp, "1", BitLength(16)
        )
        assert (0x5634, 2) == extract_value_at_location(
            inp, "2", BitLength(16)
        )

        assert (0xF0DEBC9A78563412, 7) == extract_value_at_location(
            inp, "1", BitLength(64)
        )

    def test_it_extracts_fractions_of_a_byte(self):
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")

        # 0xf0 0xde 0xbc 0x9a 0x78 0x56 0x34 0x12
        assert (0x2, 0) == extract_value_at_location(inp, "1", BitLength(4))
        assert (0x2, 0) == extract_value_at_location(inp, "1.1", BitLength(4))
        assert (0x1, 0) == extract_value_at_location(inp, "1.5", BitLength(4))
        assert (0xE, 6) == extract_value_at_location(inp, "7", BitLength(4))
        assert (0xD, 6) == extract_value_at_location(inp, "7.5", BitLength(4))

        # Within byte 0x12 => 0b00010010
        assert (0b1001, 0) == extract_value_at_location(
            inp, "1.2", BitLength(4)
        )
        assert (0b0100, 0) == extract_value_at_location(
            inp, "1.3", BitLength(4)
        )
        assert (0b010, 0) == extract_value_at_location(
            inp, "1.4", BitLength(3)
        )

    def test_it_extracts_across_byte_boundaries(self):
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")
        # across byte 0x34 0x12 => 0b00110100 0b00010010
        assert (0b001101000001001, 1) == extract_value_at_location(
            inp, "1.2", BitLength(15)
        )
        assert (0b00110100000100, 1) == extract_value_at_location(
            inp, "1.3", BitLength(14)
        )
        assert (0b0011010000010, 1) == extract_value_at_location(
            inp, "1.4", BitLength(13)
        )
        assert (0b001101000001, 1) == extract_value_at_location(
            inp, "1.5", BitLength(12)
        )
        assert (0b00110100000, 1) == extract_value_at_location(
            inp, "1.6", BitLength(11)
        )
        assert (0b0011010000, 1) == extract_value_at_location(
            inp, "1.7", BitLength(10)
        )
        assert (0b001101000, 1) == extract_value_at_location(
            inp, "1.8", BitLength(9)
        )

    def test_it_extracts_across_bytes_where_last_position_is_on_bit_1(self):
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")

        # Example PGN 39680, SPN 4181 start pos: 2.4-4
        # across byte 0x78 0x56 0x34 0x12 => 0b01111000 0b01010110 0b00110100 0b00010010
        #                                      X-------------------------X
        #         123456789012345678901
        assert (0b011110000101011000110, 3) == extract_value_at_location(
            inp, "2.4-4", BitLength(21)
        )

        # Examlpe PGN 64881, SPN 3795 start_pos: 4.7-5.1
        # Byte :     5    4    3    2    1
        #         0x9a 0x78 0x56 0x34 0x12 => 0b10011010 0b01111000 ...
        #                                              X----X
        assert (0b001, 4) == extract_value_at_location(
            inp, "4.7-5.1", BitLength(3)
        )

    def test_it_extracts_when_non_contiguous(self):
        """
        Non contigous specs mostly seem to have a comma in them, which separates
        the contiguous section from the "last few bits".

        For example:

        SPN 1214 is 19-bit and commonly has a spec that looks like:
        - "3-4, 5.6" in PGN 65226 ; or
        - "2-3, 4.6" in PGN 65229

        OR

        SPN 1596 is 12 bits, and has a spec like:
        - '1, 2.5' in PGN 54272

        SPN 1640 is 11 bits, and has a spec like:
        - '1, 2.6' in PGN 55552

        """
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")

        # Example PGN 65226, SPN 1214,  19-bits, start_pos: '3-4, 5.6'
        # Byte :     5    4    3    2    1             5          4          3 ...
        #         0x9a 0x78 0x56 0x34 0x12 => 0b10011010 0b01111000 0b01010110 ...
        #                                       X-X        X-----------------X
        assert (0b1000111100001010110, 4) == extract_value_at_location(
            inp, "3-4, 5.6", BitLength(19)
        )

        # Example PGN 65229, SPN 1214,  19-bits, start_pos: '2-3, 4.6'
        # Byte :     4    3    2    1             4          3          2
        #         0x78 0x56 0x34 0x12 => 0b01111000 0b01010110 0b00110100 ...
        #                                  X-X        X-----------------X
        assert (0b0110101011000110100, 3) == extract_value_at_location(
            inp, "2-3, 4.6", BitLength(19)
        )

        # Example PGN 54272, SPN 1596,  12-bits, start_pos: '1, 2.5'
        # Byte :     2    1
        #         0x34 0x12 =>  0b00110100 0b00010010
        #                         X--X       X------X
        assert (0x312, 1) == extract_value_at_location(
            inp, "1, 2.5", BitLength(12)
        )

        # Example PGN 5552, SPN 1640,  12-bits, start_pos: '1, 2.6'
        # Byte :     2    1
        #         0x34 0x12 =>  0b00110100 0b00010010
        #                         X-X        X------X
        assert (0x112, 1) == extract_value_at_location(
            inp, "1, 2.6", BitLength(11)
        )

    def test_only_2_sections_are_allowed(self):
        with pytest.raises(UnsupportedLocationSpec) as e:
            extract_value_at_location(None, "1,2,3", None)
        assert (
            str(e.value)
            == "Should not have more than 2 sections in location spec"
        )

    def test_second_section_does_not_have_a_byte_range_spec(self):
        with pytest.raises(UnsupportedLocationSpec) as e:
            extract_value_at_location(None, "1,2-3", None)
        assert (
            str(e.value)
            == "Should not have a range specified in non-continuous part of location spec"
        )

    def test_wholly_contiguous_multi_byte_specs_should_have_the_second_addr_start_on_bit_1(
        self,
    ):
        with pytest.raises(UnsupportedLocationSpec) as e:
            extract_value_at_location(None, "1-2.3", BitLength(None, True))
        assert (
            str(e.value)
            == "Should not have a non-first-bit aligned location spec for contiguous bytes"
        )

    def test_fractional_bits_in_first_part(self):
        # Example PGN 10240, SPN 10786,  12-bits, start_pos: '2.5, 3'
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")
        assert (0x0563, 2) == extract_value_at_location(
            inp, "2.5, 3", BitLength(12)
        )

        # Example PGN 10240, SPN 10787,  12-bits, start_pos: '4, 5.1'
        inp = (0x123456789ABCDEF0).to_bytes(8, "big")
        assert (0x0A78, 4) == extract_value_at_location(
            inp, "4, 5.1", BitLength(12)
        )


class TestStarDelimitedPGNs:
    @pytest.mark.parametrize(
        ["inp", "expected"],
        [
            ("hello*", "hello"),
            ("hello, world*", "hello, world"),
            ("x" * 1000, "x" * 200),
        ],
    )
    def test_it_decodes_pgn_65260(
        self, inp: str, expected: str, pgn_65260: PGN
    ):
        results = pgn_65260.decode(bytes(inp, "ascii"))
        assert results[0].value == expected


class TestPGNDecodesTextSPNs:
    def test_it_decodes_pgn_61445(self, pgn_61445):
        inp = [
            126,  # 1st gear
            0x31,
            0xD4,  # 54.321 .. 54321 = 0xD431
            129,  # 4th gear
            ord("D"),
            ord("1"),  # Requested D1
            ord("D"),
            ord("4"),  # Current D4
        ]  # yapf: disable
        results = pgn_61445.decode(bytes(inp))
        assert results[0].value == 1
        assert results[1].value == 54.321
        assert results[2].value == 4
        assert results[3].value == "D1"
        assert results[4].value == "D4"

    def test_it_decodes_pgn_43008(self, pgn_43008):
        # PGN 43008 Text Display -  has a "4 to N"
        inp = (
            bytes([3, 9, 0x12])
            + bytes("Abc123", "ascii")
            + bytes([0])
            + bytes("xyz", "ascii")
        )
        decoded = pgn_43008.decode(inp)

        assert decoded[0].raw == 3
        assert (
            decoded[0].value
            == "Overwrite display - The presently displayed information is to be overwritten with the transmitted information"
        )
        assert decoded[1].value == 0x12
        assert decoded[2].value == "Abc123"

    def test_it_others(self, pgn_1792: PGN):
        # PGN 64958 Transit Route - has a number of "X to Y" spns
        # PGN 64959 Transit Milepost - has a "2 to n" SPN
        # PGN 64792 - Collision Sensor Information -  has a bunch of packed strings
        results = pgn_1792.decode((0x0).to_bytes(8, "big"))
        result_4086 = results[0]
        assert result_4086.raw == 0
        assert result_4086.display_value == "0 kPa"


class TestStartPosition:
    def test_is_orders_basic_ints(self):
        a = OrderingRecord("1", None)
        b = OrderingRecord("2", None)
        assert sorted([b, a]) == [a, b]

    def test_it_orders_with_bit_offsets(self):
        a = OrderingRecord("1.1", None)
        b = OrderingRecord("1.2", None)
        c = OrderingRecord("2.1", None)
        assert sorted([b, c, a]) == [a, b, c]

    def test_it_orders_with_byte_range_hyphen(self):
        a = OrderingRecord("1-2", None)
        b = OrderingRecord("3-4", None)
        assert sorted([b, a]) == [a, b]

    def test_it_orders_with_byte_range_semicolon(self):
        a = OrderingRecord("1;2", None)
        b = OrderingRecord("3;4", None)
        assert sorted([b, a]) == [a, b]

    def test_it_orders_ints_by_numeric_value_not_string_ordering(self):
        a = OrderingRecord("1", None)
        b = OrderingRecord("02", None)
        assert sorted([b, a]) == [a, b]

    def test_it_orders_characters_with_without_case(self):
        a = OrderingRecord("a", None)
        b = OrderingRecord("B", None)
        assert sorted([b, a]) == [a, b]

    def test_it_orders_numbers_first(self):
        a = OrderingRecord("99", None)
        b = OrderingRecord("a", None)
        assert sorted([b, a]) == [a, b]


class TestTransportProtocol:
    @pytest.mark.parametrize(
        "control_byte", [0, 1, 2, 15, 18, 20, 31, 33, 254]
    )
    def test_it_decodes_pgn_60416_with_illegal_control_byte(
        self, control_byte: int, pgn_60416: PGN
    ):
        inp = control_byte.to_bytes(8, "little")
        results = pgn_60416.decode(inp)
        assert results[0].raw == control_byte
        assert results[0].value is None
        assert results[0].display_value == f"No encoding ({control_byte})"
        assert len(results) == 1

    def test_it_decodes_pgn_60416_CTS(self, pgn_60416: PGN):
        inp = (0x10F1F2F3F4F5F6F7).to_bytes(8, "big")
        results = pgn_60416.decode(inp)
        assert results[0].value == "Request to Send"
        assert len(results) == 5
        assert (
            str(results[1])
            == "SPN:2557: Total Message Size (TP.CM_RTS) = 62193"
        )
        assert (
            str(results[2])
            == "SPN:2558: Total Number of Packets (TP.CM_RTS) = 243"
        )
        assert (
            str(results[3])
            == "SPN:2559: Maximum Number of Packets (TP.CM_RTS) = 244"
        )
        assert (
            str(results[4])
            == "SPN:2560: Parameter Group Number of the packeted message (TP.CM_RTS) = 16250613"
        )

    def test_it_decodes_pgn_60416_RTS(self, pgn_60416: PGN):
        inp = (0x11F1F2F3F4F5F6F7).to_bytes(8, "big")
        results = pgn_60416.decode(inp)
        assert results[0].value == "Clear to Send"
        assert len(results) == 4
        assert (
            str(results[1])
            == "SPN:2561: Number of Packets that can be sent (TP.CM_CTS) = 241"
        )
        assert (
            str(results[2])
            == "SPN:2562: Next Packet Number to be sent (TP.CM_CTS) = 242"
        )
        assert (
            str(results[3])
            == "SPN:2563: Parameter Group Number of the packeted message (TP.CM_CTS) = 16250613"
        )

    def test_it_decodes_pgn_60416_EOM(self, pgn_60416: PGN):
        inp = (0x13F1F2F3F4F5F6F8).to_bytes(8, "big")
        results = pgn_60416.decode(inp)
        assert results[0].value == "End of Message ACK"
        assert len(results) == 4
        assert (
            str(results[1])
            == "SPN:2564: Total Message Size (TP.CM_EndofMsgACK) = 62193"
        )
        assert (
            str(results[2])
            == "SPN:2565: Total Number of Packets (TP.CM_EndofMsgACK) = 243"
        )
        assert (
            str(results[3])
            == "SPN:2566: Parameter Group Number of the packeted message (TP.CM_EndofMsgACK) = 16316149"
        )

    def test_it_decodes_pgn_60416_BAM(self, pgn_60416: PGN):
        inp = (0x20F1F2F3F4F5F6F8).to_bytes(8, "big")
        results = pgn_60416.decode(inp)
        assert results[0].value == "Broadcast Announce Message"
        assert len(results) == 4
        assert (
            str(results[1])
            == "SPN:2567: Total Message Size (TP.CM_BAM) = 62193"
        )
        assert (
            str(results[2])
            == "SPN:2568: Total Number of Packets (TP.CM_BAM) = 243"
        )
        assert (
            str(results[3])
            == "SPN:2569: Parameter Group Number of the packeted message (TP.CM_BAM) = 16316149"
        )

    def test_it_decodes_pgn_60416_ConnectionAbort(self, pgn_60416: PGN):
        inp = (0xFF01F2F3F4F5F6F8).to_bytes(8, "big")
        results = pgn_60416.decode(inp)
        assert results[0].value == "Connection Abort"
        assert len(results) == 3
        assert (
            str(results[1])
            == "SPN:2570: Connection Abort Reason = Already in one or more connection managed sessions and cannot support another."
        )
        assert (
            str(results[2])
            == "SPN:2571: Parameter Group Number of packeted message (TP.CM_Conn_Abort) = 16316149"
        )
