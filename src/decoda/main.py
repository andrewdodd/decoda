# Copyright Andrew Dodd
import math
from binascii import hexlify
from numbers import Number
from typing import Any, Dict, Optional, Union

import attr

from decoda.exceptions import (
    CouldBeAnyLength,
    ErrorIndicatorRangeError,
    NotAvaiableRangeError,
    ParameterSpecificIndicatorError,
    UnknownReferenceError,
    UnsupportedLocationSpec,
)


@attr.s(frozen=True)
class Manufacturer:
    id = attr.ib()
    name = attr.ib()
    location = attr.ib()
    status = attr.ib()


@attr.s(frozen=True)
class BitLength:
    max_len = attr.ib()
    variable = attr.ib(default=False)

    def __attrs_post_init__(self):
        if (
            self.variable
            and self.max_len is not None
            and self.max_len % 8 != 0
        ):
            raise ValueError(
                "bit_length ({}) must be an 8-bit multiple".format(
                    self.max_len
                )
            )

    def could_fit_in_bytes(self, value):
        if self.variable:
            return True
        return self.max_len // 8 <= len(value)

    def expected_length(self, variable_pgn):
        if self.variable and variable_pgn:
            raise CouldBeAnyLength()
        return self

    def trim_to_length(self, val):
        if self.max_len is not None and val:
            max_bytes = self.max_len // 8
            val = val[:max_bytes]
        return val

    def is_equivalent_to(self, bits):
        return not self.variable and self.max_len == bits


def convert_to_int(i: Any) -> int:
    if isinstance(i, int):
        return i
    if isinstance(i, str) and i.startswith("0x"):
        return int(i[2:], 16)
    if isinstance(i, str) and i.startswith("0b"):
        return int(i[2:], 2)
    return int(i, 10)


def convert_encodings(value: Dict) -> Dict:
    encodings = {}
    for k, v in value.items():
        if isinstance(k, str) and "-" in k:
            start, end = k.split("-")
        else:
            start = k
            end = k

        start_int = convert_to_int(start)
        end_int = convert_to_int(end) + 1

        for k in range(start_int, end_int):
            encodings[k] = v
    return encodings


@attr.s(frozen=True)
class EncodedValue:
    encodings: Dict = attr.ib(converter=convert_encodings)
    bit_length = attr.ib()

    @encodings.validator
    def _check_encodings(self, attribute, value):
        if len(value) == 0:
            raise ValueError("must have at least 1 encoding")

    @bit_length.validator
    def _check_bit_length(self, attribute, value):
        if value.max_len is None or value.max_len < 1:
            raise ValueError("must have positive bit length")

    def decode_from_raw(
        self, value, start_spec, variable_pgn, prev_spn_ended, *args, **kwargs
    ):
        bit_len = self.bit_length.expected_length(variable_pgn)
        raw, end_byte_idx = extract_value_at_location(
            value, start_spec, bit_len
        )
        value = self.encodings.get(raw)
        if value:
            display_value = "{} ({})".format(value, raw)
        else:
            display_value = "No encoding ({})".format(raw)

        return {
            "raw": raw,
            "value": value,
            "display_value": display_value,
        }, end_byte_idx


@attr.s(frozen=True)
class ScalarValue:
    units = attr.ib()
    min = attr.ib()
    max = attr.ib()
    offset = attr.ib()
    scale = attr.ib()
    bit_length = attr.ib()

    @bit_length.validator
    def _check_bit_length(self, attribute, value):
        if value.max_len is None or value.max_len < 1:
            raise ValueError("must have positive bit length")

    def __attrs_post_init__(self):
        if self.min and self.max and not self.min < self.max:
            raise ValueError("min must be less than max")

    def as_display_value(self, value):
        return "{} {}".format(value, self.units) if self.units else str(value)

    def check_in_valid_range(self, raw):
        not_available_thres = 0xFF
        error_ind_thres = 0xFE
        param_specific_thres = 0xFB
        format_offset = lambda val, thres: val - thres

        if self.bit_length.is_equivalent_to(8):
            format_offset = lambda val, thres: None
        elif self.bit_length.is_equivalent_to(16):
            not_available_thres <<= 8
            error_ind_thres <<= 8
            param_specific_thres <<= 8
        elif self.bit_length.is_equivalent_to(32):
            not_available_thres <<= 24
            error_ind_thres <<= 24
            param_specific_thres <<= 24
        else:
            return

        if raw >= not_available_thres:
            raise NotAvaiableRangeError(
                format_offset(raw, not_available_thres)
            )
        if raw >= error_ind_thres:
            raise ErrorIndicatorRangeError(format_offset(raw, error_ind_thres))
        if raw >= param_specific_thres:
            raise ParameterSpecificIndicatorError(
                format_offset(raw, param_specific_thres)
            )

    def decode_from_raw(
        self,
        value,
        start_spec,
        variable_pgn,
        prev_spn_ended,
        ignore_range=False,
        **kwargs,
    ):
        bit_len = self.bit_length.expected_length(variable_pgn)
        raw, end_byte_idx = extract_value_at_location(
            value, start_spec, bit_len
        )

        try:
            self.check_in_valid_range(raw)

            value = raw
            if self.scale:
                value *= self.scale

            if self.offset:
                value += self.offset

            display_value = self.as_display_value(value)

            if not ignore_range:
                if self.min and value < self.min:
                    display_value = (
                        "{} (encoded value {} was clipped to min)".format(
                            self.as_display_value(self.min),
                            self.as_display_value(value),
                        )
                    )
                    value = self.min
                if self.max and value > self.max:
                    display_value = (
                        "{} (encoded value {} was clipped to max)".format(
                            self.as_display_value(self.max),
                            self.as_display_value(value),
                        )
                    )
                    value = self.max

        except (
            NotAvaiableRangeError,
            ErrorIndicatorRangeError,
            ParameterSpecificIndicatorError,
        ) as e:
            value = e.value()
            display_value = e.display_value()

        return {
            "raw": raw,
            "value": value,
            "display_value": display_value,
        }, end_byte_idx


def convert_if_hex(value: str) -> Optional[str]:
    if value is None:
        return value
    if value.startswith("0x"):
        return chr(int(value, 16))
    return value


@attr.s(frozen=True)
class TextValue:
    bit_length = attr.ib()
    delimiter: Optional[str] = attr.ib(default=None, converter=convert_if_hex)
    # I.e. another SPN that specifies its length
    length_spn = attr.ib(default=None)

    def __attrs_post_init__(self):
        if (
            self.bit_length.variable
            and self.delimiter is None
            and self.length_spn is None
        ):
            raise ValueError(
                "Variable length SPN must specify delimiter or length SPN"
            )

    def decode_from_raw(
        self,
        value,
        start_spec,
        variable_pgn,
        prev_spn_ended,
        already_decoded=None,
        **kwargs,
    ):
        start_idx = self._get_start(start_spec, prev_spn_ended)
        val = str(value[start_idx:], "ascii")

        # Hmm... should deal with not variable length?
        if not variable_pgn and not self.bit_length.could_fit_in_bytes(value):
            raise ValueError("insufficent bytes")

        tightly_packed_strings = False
        encoded_length = None
        if self.length_spn:
            try:
                decoded_spn = next(
                    decoded
                    for decoded in already_decoded
                    if decoded.id == self.length_spn
                )
            except StopIteration:
                raise ValueError(
                    f"Length SPN: {self.length_spn} not found in already_decoded"
                )
            encoded_length = decoded_spn.value
            tightly_packed_strings = True

        if encoded_length:
            val = val[:encoded_length]
        elif self.delimiter:
            val = val.split(self.delimiter)[0]

        val = self.bit_length.trim_to_length(val)
        end_byte_idx = start_idx + len(val)

        if tightly_packed_strings:
            end_byte_idx -= 1

        return {"raw": val, "value": val, "display_value": val}, end_byte_idx

    def _get_start(self, start_spec, prev_spn_ended):
        start = start_spec.split()[0].split("-")[0]
        try:
            return int(start) - 1
        except ValueError:
            return prev_spn_ended + 1


@attr.s(frozen=True)
class ByteArrayValue:
    bit_length = attr.ib()

    def decode_from_raw(
        self, value, start_spec, variable_pgn, prev_spn_ended, *args, **kwargs
    ):
        start = start_spec.split()[0].split("-")[0]
        try:
            start_idx = int(start) - 1
        except ValueError:
            start_idx = prev_spn_ended + 1

        val = value[start_idx:]
        end_byte_idx = start_idx + len(val)

        return {
            "raw": val,
            "value": val,
            "display_value": val.hex(),
        }, end_byte_idx


@attr.s(frozen=True)
class CustomFunctionValue:
    custom = attr.ib()
    bit_length = attr.ib()
    non_custom_alternative = attr.ib()
    custom_args = attr.ib(default=None)

    def decode_from_raw(
        self,
        value,
        start_spec,
        variable_pgn,
        prev_spn_ended,
        *args,
        already_decoded=None,
        **kwargs,
    ):
        bit_len = self.bit_length.expected_length(variable_pgn)
        raw, end_byte_idx = extract_value_at_location(
            value, start_spec, bit_len
        )

        val = self.custom(
            value=raw,
            already_decoded=already_decoded,
            custom_args=self.custom_args,
            non_custom_alternative=self.non_custom_alternative,
            start_spec=start_spec,
            variable_pgn=variable_pgn,
            prev_spn_ended=prev_spn_ended,
            original_value=value,
        )
        if val is None:
            return None, prev_spn_ended

        return {
            "raw": raw,
            "value": val,
            "display_value": f"{val} ({raw})",
        }, end_byte_idx


@attr.s(frozen=True)
class SPNFields:
    id = attr.ib()
    name = attr.ib()
    description = attr.ib()


@attr.s(frozen=True)
class SPN(SPNFields):
    value_decoder = attr.ib()

    def decode(
        self,
        value,
        start_spec,
        variable_pgn,
        prev_spn_ended_idx,
        *args,
        **kwargs,
    ):
        decoded, end_byte_idx = self.value_decoder.decode_from_raw(
            value,
            start_spec,
            variable_pgn,
            prev_spn_ended_idx,
            *args,
            **kwargs,
        )
        if decoded is None:
            return None, prev_spn_ended_idx
        return DecodedSPN.build(self, **decoded), end_byte_idx


@attr.s(frozen=True)
class DecodedSPN(SPNFields):
    raw: Number = attr.ib()
    value: Union[Number, str] = attr.ib()
    display_value: str = attr.ib()

    @classmethod
    def build(
        cls,
        spn: SPN,
        raw: Number,
        value: Union[Number, str],
        display_value: str,
    ):
        return cls(
            id=spn.id,
            name=spn.name,
            description=spn.description,
            raw=raw,
            value=value,
            display_value=display_value,
        )

    def __str__(self):
        return f"SPN:{self.id}: {self.name} = {self.value}"


def order_start_positions(start_pos_spec):
    if "to" in start_pos_spec:
        first = start_pos_spec.split("to")[0]
    elif "," in start_pos_spec:
        return order_start_positions(start_pos_spec.split(",")[0])
    else:
        first = start_pos_spec.split("-")[0]

    if first.startswith("0x"):
        raise UnsupportedLocationSpec("We don't support this yet")
    try:
        return float(first)
    except ValueError:
        return first.lower()


# We need this because our decoding relies on the order of the records
class OrderingRecord:
    def __init__(self, start, spn):
        self.start = start
        self.spn = spn

    def __repr__(self):
        return "OrderingRecord({}, {})".format(self.start, self.spn)

    def __lt__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented

        own_start = self.__first_element_of_start_position()
        other_start = other.__first_element_of_start_position()

        # If the they are comparable, order them
        if type(own_start) == type(other_start):
            return own_start < other_start

        # if they are not...then order "floats" first
        return isinstance(own_start, float)

    def __first_element_of_start_position(self):
        return order_start_positions(self.start)


def byte_and_bit_from_num(num):
    parts = num.split(".")
    byte = parts[0]
    bit = parts[1] if len(parts) > 1 else 1
    return int(byte), int(bit)


def mask(length):
    return (1 << length) - 1


def extract_value_at_location(payload, location, bit_length):
    """
    Extract a "numeric" payload from the byte array at the provided location

    Returns: (value, last_byte_idx)

    where
     - value: the "bit_length" at "location" from the payload, and
     - last_byte_idx: is the index of the last byte that the value was in.
    """
    sections = [s.strip() for s in location.split(",")]
    if len(sections) > 1:
        if len(sections) > 2:
            raise UnsupportedLocationSpec(
                "Should not have more than 2 sections in location spec"
            )
        contiguous, extra = sections
        if "-" in extra:
            raise UnsupportedLocationSpec(
                "Should not have a range specified in non-continuous part of location spec"
            )

        # assume that the contigous section is multiple bytes in length
        contiguous_length = 8
        if "-" in contiguous:
            # we have a multi byte contiguous section
            contiguous_start, contiguous_end = (
                int(x) for x in contiguous.split("-")
            )
            contiguous_length = (1 + contiguous_end - contiguous_start) * 8
        elif "." in contiguous:
            # It appears to be a new spec?
            contiguous_length = 9 - int(contiguous.split(".")[1])

        contiguous_value, _ = extract_value_at_location(
            payload, contiguous, BitLength(contiguous_length)
        )
        extra_value, last_byte_idx = extract_value_at_location(
            payload, extra, BitLength(bit_length.max_len - contiguous_length)
        )
        extra_value <<= contiguous_length

        return extra_value + contiguous_value, last_byte_idx

    section = sections[0]
    if "-" not in section:
        # single byte
        byte, bit = byte_and_bit_from_num(section)
        byte -= 1
        bit -= 1
        payload = payload[byte:]

        if not bit_length.could_fit_in_bytes(payload):
            raise ValueError(
                "not enough bits for SPN - need {}, from {}.{} in payload[{}]".format(
                    bit_length.max_len, byte, byte, hexlify(payload)
                )
            )

        v = int.from_bytes(payload, byteorder="little")
        v >>= bit
        v &= mask(bit_length.max_len)

        additional_bytes = math.ceil((bit + bit_length.max_len) / 8.0) - 1
        last_byte_idx = byte + additional_bytes
        return v, last_byte_idx

    # multi byte section
    first, last = section.split("-")
    f_byte, f_bit = byte_and_bit_from_num(first)
    l_byte, l_bit = byte_and_bit_from_num(last)

    if l_bit != 1:
        raise UnsupportedLocationSpec(
            "Should not have a non-first-bit aligned location spec for contiguous bytes"
        )

    # last address starts on a byte boundary...so everything should be
    # contiguous???
    return extract_value_at_location(payload, first, bit_length)


@attr.s(frozen=True)
class PGN:
    id = attr.ib()
    name = attr.ib()
    description = attr.ib()
    transmission_rate = attr.ib()
    length = attr.ib()
    ordering_records = attr.ib()
    repeatable_spns = attr.ib(factory=list)
    acronym = attr.ib(default=None)

    def is_repeatable(self, spn):
        return spn.id in self.repeatable_spns

    def decode(self, value):
        decoded = []
        pgn_is_variable = self.length.variable
        ended_in_byte_idx = -1
        repeatable_spn_idx = None

        for idx, record in enumerate(self.ordering_records):
            start, spn = record.start, record.spn

            if self.is_repeatable(spn):
                repeatable_spn_idx = idx
                break
            else:
                # need to get the byte that the result came from???
                result, ended_in_byte_idx = spn.decode(
                    value,
                    start,
                    pgn_is_variable,
                    ended_in_byte_idx,
                    already_decoded=decoded,
                )
                if result is not None:
                    decoded.append(result)

        if repeatable_spn_idx:
            # we found the first repeatable spn above, so came here
            # The remaining are the repeatable ones
            # we assume they will all be the same length...(I hope!)
            repeatables = self.ordering_records[repeatable_spn_idx:]

            # Do the first set of repeatable SPNs
            start_idx = ended_in_byte_idx
            for record in repeatables:
                start, spn = record.start, record.spn
                result, ended_in_byte_idx = spn.decode(
                    value,
                    start,
                    pgn_is_variable,
                    ended_in_byte_idx,
                    already_decoded=decoded,
                )
                decoded.append(result)
            end_idx = ended_in_byte_idx

            # Now we have the length of the repeatable section in bytes
            # trim the value from the front and keep doing it until we
            # run out of bytes
            bytes_in_repeat = end_idx - start_idx
            while len(value) > end_idx + bytes_in_repeat:
                value = value[bytes_in_repeat:]
                for record in repeatables:
                    start, spn = record.start, record.spn
                    result, ended_in_byte_idx = spn.decode(
                        value,
                        start,
                        pgn_is_variable,
                        ended_in_byte_idx,
                        already_decoded=decoded,
                    )
                    decoded.append(result)

        return decoded


@attr.s(frozen=True)
class Address:
    num = attr.ib()

    def is_broadcast(self):
        return self.num == -1

    @num.validator
    def _check_num(self, attribute, value):
        if not -1 <= value <= 255:
            raise ValueError("address out of range")

    @staticmethod
    def from_pf_and_ps(pf, ps):
        if pf >= 0xF0:
            return BroadcastAddress

        return Address(ps)


BroadcastAddress = Address(-1)


@attr.s(frozen=True)
class IndustryGroup:
    id = attr.ib()
    description = attr.ib()
    preferred_addresses = attr.ib()

    def preferred_address_name(self, id):
        return self.preferred_addresses.get(id)
