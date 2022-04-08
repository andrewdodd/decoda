import argparse
import json
import pathlib
import sys


def load_corrections(path, key):
    result = []
    for filename in path.glob("*.json"):
        with open(filename) as f:
            corrections_list = json.load(f)[key]
            result.append({obj["id"]: obj for obj in corrections_list})
    return result


# items is a list of dicts, where each item is an SPN or PGN dict
# updates is a list of dicts, where each update is a dictionary of "id" to the
# modifications needed
def treat_list_with_updates(items, updates):
    result = []

    for item in items:
        # Apply updates from all update dicts in order
        for update in updates:
            if item["id"] in update:
                item.update(update.get(item["id"], {}))
                del update[item["id"]]

        result.append(item)

    # Add any "updates" that were not applied. This allows the corrections
    # files to specify new items entirely
    for update in updates:
        result.extend(update.values())

    result = sorted(result, key=lambda obj: obj["id"])
    return result


def replace_bad_resolutions(spns):
    result = []
    for spn in spns:
        resolution = spn.get("resolution")
        if resolution and type(resolution) is str:
            print(
                f"Converting resolution for SPN: {spn['id']} to 1, from: {spn['resolution']}"
            )
            spn["resolution"] = 1
        result.append(spn)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corrections_path",
        type=pathlib.Path,
        default="./corrections",
        help="the path to corrections to apply",
    )
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

    pgn_corrections = load_corrections(args.corrections_path, "PGNs")
    spn_corrections = load_corrections(args.corrections_path, "SPNs")

    spec = json.load(args.input_file)
    spec["PGNs"] = treat_list_with_updates(spec["PGNs"], pgn_corrections)
    spec["SPNs"] = treat_list_with_updates(spec["SPNs"], spn_corrections)
    spec["SPNs"] = replace_bad_resolutions(spec["SPNs"])

    json.dump(spec, args.output_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
