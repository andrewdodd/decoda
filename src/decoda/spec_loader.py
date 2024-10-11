# Copyright Andrew Dodd
import importlib
import json
import math
import os
from binascii import hexlify
from numbers import Number
from typing import Callable, Dict, Generic, List, Type, TypeVar

import attr

from decoda.exceptions import MissingBitLength, UnknownReferenceError
from decoda.main import (
    PGN,
    SPN,
    BitLength,
    ByteArrayValue,
    CustomFunctionValue,
    EncodedValue,
    IndustryGroup,
    Manufacturer,
    OrderingRecord,
    ScalarValue,
    TextValue,
)

T = TypeVar("T", covariant=True)


class Repo(Generic[T]):
    # TODO - Replace the passed cls with typing info
    def __init__(
        self, cls: Type[T], from_dict: Callable[[Dict], T], l, *args, **kwargs
    ):
        self.__cls = cls
        self.__lookup: Dict[int, T] = {
            int(r["id"]): from_dict(r, *args, **kwargs) for r in l
        }

    def get_by_id(self, id) -> T:
        try:
            return self.__lookup[id]
        except KeyError:
            raise UnknownReferenceError(
                "{} not found for id: {}".format(self.__cls.__name__, id)
            )


@attr.s(frozen=True)
class J1939Spec:
    Manufacturers: Repo[Manufacturer] = attr.ib()
    SPNs: Repo[SPN] = attr.ib()
    PGNs: Repo[PGN] = attr.ib()
    IndustryGroups: Repo[IndustryGroup] = attr.ib()

    def preferred_address_name(self, id, industry_group=0):
        if id == -1:
            return "Broadcast address"
        global_ig = self.IndustryGroups.get_by_id(0)
        global_name = global_ig.preferred_address_name(id)
        if id < 128:
            return global_name
        else:
            ig = self.IndustryGroups.get_by_id(industry_group)
        return ig.preferred_address_name(id) or global_name


def manufacturer_from_dict(d: Dict) -> Manufacturer:
    return Manufacturer(
        d["id"],
        d["name"],
        d.get("location", "No location"),
        d.get("status", "Unknown status"),
    )


def scalar_value_from_dict(d: Dict) -> ScalarValue:
    # unpack from the storage format
    units = d.get("units")
    data_range = d.get("data_range", None) or {}
    offset = d.get("offset", None)
    resolution = d.get("resolution", None)
    try:
        bit_length = BitLength(int(d.get("bit_length")))  # type: ignore
    except ValueError:
        raise MissingBitLength("ScalarValue SPN: {}".format(d["id"]))

    return ScalarValue(
        units,
        data_range.get("min", None),
        data_range.get("max", None),
        offset,
        resolution,
        bit_length,
    )


# Nod to DRF's module loading a la: https://github.com/encode/django-rest-framework/blob/8385ae42c06b8e68a714cb67b7f0766afe316883/rest_framework/settings.py
def import_from_string(val):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split(".")
        module_path, name = ".".join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        return getattr(module, name)
    except (ImportError, AttributeError, ValueError) as e:
        msg = "Could not import '%s'. %s: %s." % (val, e.__class__.__name__, e)
        raise ImportError(msg)


def make_decoder_from_spn_dict(d):
    bl = d["bit_length"]
    variable = d.get("variable", False)

    try:
        # try to make an "integer" bit length
        bit_length = BitLength(int(bl), variable)
    except ValueError:
        # else just use what we found...downstream consumers will
        # check if this is ok for their needs
        bit_length = BitLength(bl, variable)

    if d.get("custom"):
        try:
            format_handler = import_from_string(d["custom"])
            non_custom = d.copy()
            del non_custom["custom"]
            alternative = make_decoder_from_spn_dict(non_custom)
            return CustomFunctionValue(
                format_handler, bit_length, alternative, d.get("custom_args")
            )
        except ImportError:
            pass

    if d.get("encodings"):
        return EncodedValue(d["encodings"], bit_length)
    elif (
        str(d.get("units", "")).lower() == "ascii"
        or d.get("delimiter", "")
        or d.get("length_spn")
    ):
        return TextValue(
            bit_length,
            delimiter=d.get("delimiter"),
            length_spn=d.get("length_spn"),
        )
    elif str(d.get("units", "")).lower() == "bytearray":
        return ByteArrayValue(bit_length)
    else:
        return scalar_value_from_dict(d)


def spn_from_dict(d: Dict) -> SPN:
    id = d["id"]
    name = d["name"]
    description = ""  # d.get("description", "")
    try:
        decoder = make_decoder_from_spn_dict(d)
    except ValueError as e:
        raise ValueError(f"Unable to make spn from {d}") from e
    return SPN(id, name, description, decoder)


def build_ordering_records(spn_list, spn_ref):
    spns = []
    for item in spn_list:
        start_pos = item["start_pos"]
        if not isinstance(start_pos, str):
            raise ValueError("Hmm...start pos is not a string")
        spns.append(OrderingRecord(start_pos, spn_ref.get_by_id(item["id"])))
    return sorted(spns)


def parse_length(v):
    try:
        return BitLength(int(v))
    except ValueError as ve:
        if "*" in v:
            return BitLength(None, True)
        if "variable" in v.lower():
            return BitLength(None, True)
        if v == "":
            return BitLength(8)
        print("Confusing length: {}".format(v))
        raise ve


def pgn_from_dict(d, spn_ref):
    return PGN(
        d["id"],
        d.get("name", d.get("label")),
        d["description"],
        d.get("transmission_rate"),
        parse_length(d["length"]),
        build_ordering_records(d["spns"], spn_ref),
        d.get("repeatable_spns", []),
        d.get("acronym"),
    )  # yapf: disable


def industry_group_from_dict(d, preferred_addresses):
    return IndustryGroup(
        d["id"], d["name"], preferred_addresses.get(d["id"], {})
    )


def convert_addresses(d):
    addresses = {}
    for k, v in d.items():
        if k == "Global":
            addresses[0] = {int(address): name for address, name in v.items()}
        else:
            k = int(k.replace("IG", ""))
            addresses[k] = {int(address): name for address, name in v.items()}
    return addresses


def load_from_file(filename, warn_of_errors=True):
    with open(filename) as f:
        spec = json.load(f)
    spns_in_error = []
    spn_specs = []
    for spn in spec["SPNs"]:
        try:
            spn_from_dict(spn)
            spn_specs.append(spn)
        except Exception as e:
            spns_in_error.append((spn, e))
            pass
    spns = Repo(SPN, spn_from_dict, spn_specs)

    pgns_in_error = []
    pgn_specs = []
    for pgn in spec["PGNs"]:
        try:
            pgn_from_dict(pgn, spns)
            pgn_specs.append(pgn)
        except Exception as e:
            pgns_in_error.append((pgn, e))
            pass

    pgns = Repo(PGN, pgn_from_dict, pgn_specs, spns)
    manufacturers = Repo(
        Manufacturer, manufacturer_from_dict, spec["Manufacturers"]
    )
    preferred_addresses = convert_addresses(spec["SourceAddresses"])
    industry_groups = Repo(
        IndustryGroup,
        industry_group_from_dict,
        spec["IndustryGroups"],
        preferred_addresses,
    )

    if warn_of_errors:
        if spns_in_error:
            spn_ids = sorted(
                list(set(spn.get("id") for spn, _ in spns_in_error))
            )
            print(f"SPN IDs with errors: {spn_ids}")
        if pgns_in_error:
            pgn_ids = sorted(
                list(set(pgn.get("id") for pgn, _ in pgns_in_error))
            )
            print(f"PGN IDs with errors: {pgn_ids}")

    return J1939Spec(manufacturers, spns, pgns, industry_groups)


# This is a rather ugly technique for now...just want to supply a lazy-loaded
# spec.
class LoadOnFirstAccess:
    def __init__(self):
        self.j1939 = None

    def provide(self):
        if not self.j1939:
            SPEC_PATH = os.environ.get("J1939_SPEC_PATH", "./decoda_spec.json")
            self.j1939 = load_from_file(SPEC_PATH)
        return self.j1939


spec_provider = LoadOnFirstAccess()
