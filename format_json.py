import argparse
import json


def format_json(f):
    with open(f, "r") as source:
        content = json.load(source)

    with open(f, "w") as dest:
        json.dump(content, dest, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("FILE", help="the file to parse")
    args = parser.parse_args()
    format_json(args.FILE)
