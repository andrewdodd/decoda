import argparse
import json
import re
import sys

from decoda.spec_loader import spn_from_dict


def remove_pgns(pgns):
    result = []
    for pgn in pgns:
        spns_list = pgn["spns"]
        if len(spns_list) > 0 and all(
            bool(spn.get("start_pos")) for spn in spns_list
        ):
            # we want this, even if it appears to be invalid....we should fix
            # it
            result.append(pgn)
        elif pgn.get("length") != "":
            result.append(pgn)

    return result


def remove_spns(spns):
    result = []
    for spn in spns:
        try:
            spn_from_dict(spn)
            result.append(spn)
        except (ValueError, KeyError):
            pass
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
    spec["PGNs"] = remove_pgns(spec["PGNs"])
    spec["SPNs"] = remove_spns(spec["SPNs"])
    json.dump(spec, args.output_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
