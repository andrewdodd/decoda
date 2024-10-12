import argparse
import json
import re
import sys

from decoda.sae_spec_converter.create_j1939db_json import J1939daConverter


def update_resolution(d):
    d = d.copy()

    resolution = d.get("resolution", "").lower()
    units = d.get("units", "").lower()
    if not resolution:
        return d
    if resolution in {"variant determined", "ascii"}:
        return d
    if units in {"ascii", "binary", "bit", "bit-mapped"}:
        return d

    # Try using "per" for splitting, this appears to be the new way
    parts = resolution.split(f"{units} per ")
    try:
        d["resolution"] = eval(parts[0].replace(" ", ""))
        return d
    except Exception:
        if units == "" and "/" not in resolution:
            return d
        pass

    # Fall-back to old mappings
    # map known mismatches
    # NB: units are lower case from above!
    units = {
        "ratio": "/",
        "weeks": "week",  # SPN 915
        "months": "month",  # SPN 963
        "years": "year",  # SPN 964
        "": "/",  # SPN 1255
        "sa": "source address",  # SPN 1480
        "turns": "turn",  # SPN 1811
        "ohm/v": "ohm per",  # SPN 8431
    }.get(units, units)

    if units not in resolution:
        raise ValueError(f"missing units in resolution: {d}")

    parts = resolution.split(units)
    try:
        d["resolution"] = eval(parts[0].replace(" ", ""))
    except Exception:
        print(d)
        raise

    return d


# Remove all characters that are not likely to be part of a number
def _strip_not_likely_numericals(value):
    return re.sub(r"[^\d\.\-]", "", value)


def update_offset(d):
    d = d.copy()
    if d["offset"] not in {
        "",
        "Variant",
        "Variant Determined",
        "Data Specific",
    }:
        try:
            offset = _strip_not_likely_numericals(d["offset"])
            d["offset"] = eval(offset.split()[0])
        except:
            print(d)
            raise
    return d


def update_datarange(d):
    d = d.copy()
    try:
        if d["units"] == "ASCII":
            pass
        elif " to " in d["data_range"]:
            data_range = d["data_range"]
            if d["units"]:
                data_range = data_range.split(d["units"])[0].strip()
            low, high = data_range.split(" to ")
            # Remove all characters that are not likely to be part of a number
            low = _strip_not_likely_numericals(low)
            high = _strip_not_likely_numericals(high)
            d["data_range"] = {
                "min": float(low.replace(",", "").replace(" ", "")),
                "max": float(high.replace(",", "").replace(" ", "")),
            }
    except:
        print(d)
        raise

    return d


#      "length": "Variable - up to 100 bytes",
#      "length": "Variable - up to 1728 bytes followed by an \"*\" delimiter",
#      "length": "Variable - up to 200 bytes followed by an NULL delimiter",
#      "length": "Variable - up to 200 bytes followed by an \"*\" delimiter",
#      "length": "Variable - up to 200 characters",
#      "length": "Variable - up to 25 bytes followed by an \"*\" delimiter",
#      "length": "Variable - up to 32 bytes followed by an \"*\" delimiter",
#      "length": "Variable - up to 5 bytes followed by an \"*\" delimiter",
#      "length": "Variable",
def append_bitlength(d):
    d = d.copy()
    length = d["length"]
    if length == "":
        return d

    parts = length.split(" ")

    if "Variable" in length:
        d["variable"] = True
        d["bit_length"] = int(parts[4]) * 8
        if parts[-1] == "delimiter":
            d["delimiter"] = hex(ord("*")) if "*" in parts[-2] else hex(0)
        length_spn = re.search(
            "The length.*must be reported using SPN (\\d+) ", d["description"]
        )
        if length_spn:
            d["length_spn"] = int(length_spn.group(1))

        return d

    if parts[1] in {"byte", "bytes"}:
        d["bit_length"] = int(parts[0]) * 8
    elif parts[1] in {"bit", "bits"}:
        d["bit_length"] = int(parts[0])
    else:
        raise ValueError(f"Unhandled length for SPN: {d}")
    return d


def extract_encodings(d):
    # We really only want the first encounter of an encoding, as that is the
    # shortest. This works around what I consider to be a bug in
    # J1939daConverter.
    class OnlyTakeFirst:
        encodings = {}
        extras = {}

        def update(self, d):
            for key, val in d.items():
                update_dict = (
                    self.encodings
                    if key not in self.encodings
                    else self.extras
                )
                update_dict[key] = val

    take_first = OnlyTakeFirst()
    try:
        J1939daConverter.create_bit_object_from_description(
            d["description"], take_first
        )
    except Exception:
        print(d)
        raise

    if not take_first.encodings:
        return d

    d = d.copy()

    description = d["description"]
    # Apply the same replacement treatments
    description = re.sub(r"[ ]+", " ", description)
    description = re.sub(r"[ ]?\-\-[ ]?", " = ", description)
    description = re.sub(
        r"^(\d+)\s*-\s*(?!\=)", r"\1 = ", description
    )  # replace hyphen with = when in form "123 - "
    description_lower = description.lower()
    encodings = {}
    for key, value in take_first.encodings.items():
        # The create_bit_object_from_description uses a .lower() in part of its
        # cleaning of the strings. I don't like that, so do some tricks to get
        # the properly capitalised strings back
        start_idx = description_lower.index(value.lower())
        encodings[key] = description[start_idx : start_idx + len(value)]

    d["encodings"] = encodings

    return d


def enrich_spns(spns):
    result = []
    for spn in spns:
        spn = update_resolution(spn)
        spn = update_offset(spn)
        spn = update_datarange(spn)
        spn = append_bitlength(spn)
        spn = extract_encodings(spn)
        result.append(spn)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdout,
        help="the json file to use as input",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="the json file to use as output",
    )
    parser.add_argument("--pretty", default=False, action="store_true")
    args = parser.parse_args()

    spec = json.load(args.input_file)
    spec["SPNs"] = enrich_spns(spec["SPNs"])
    json.dump(spec, args.output_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
