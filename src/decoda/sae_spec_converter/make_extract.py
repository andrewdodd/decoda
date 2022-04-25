import argparse
import json
import re
import sys

from decoda.spec_loader import spn_from_dict


def remove_description(item):
    if "description" in item:
        item["description"] = ""
    return item


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
    spec["PGNs"] = [
        remove_description(pgn)
        for pgn in spec["PGNs"]
        if pgn["id"] in {0, 65226, 60160, 60416}
    ]
    spns = {spn["id"] for pgn in spec["PGNs"] for spn in pgn["spns"]}
    spec["SPNs"] = [
        remove_description(spn) for spn in spec["SPNs"] if spn["id"] in spns
    ]
    spec["Manufacturers"] = []
    spec["SourceAddresses"] = {
        "Global": {
            k: v
            for k, v in spec["SourceAddresses"]["Global"].items()
            if int(k) < 5
        }
    }
    json.dump(spec, args.output_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
