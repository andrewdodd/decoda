import argparse
import json
import sys

import xlrd2 as xlrd

from .json_from_da import extract_pgns, extract_spns, secure_open_workbook


def filter_source_doc(item):
    return "11783" in item.get("source_document")


def spec_from_workbook(wb: xlrd.Book):
    return {
        "PGNs": [pgn for pgn in extract_pgns(wb) if filter_source_doc(pgn)],
        "SPNs": [spn for spn in extract_spns(wb) if filter_source_doc(spn)],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "isobus_pgns_spns_xlsx",
        type=str,
        help="The SPGs and PGNs XLSX workbook from isobus.net",
    )
    parser.add_argument(
        "json_file",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="the json file to use as output",
    )
    parser.add_argument("--pretty", default=False, action="store_true")
    args = parser.parse_args()

    print(args.isobus_pgns_spns_xlsx)
    wb = secure_open_workbook(
        filename=args.isobus_pgns_spns_xlsx, on_demand=True
    )
    spec = spec_from_workbook(wb)
    json.dump(spec, args.json_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
