import argparse
import datetime
import json
import sys

import defusedxml
import xlrd2 as xlrd
from defusedxml.common import EntitiesForbidden
import pandas as pd


class XlrdAdapter:
    def __init__(self, wb):
        self._wb = wb

    def find_first_sheet_by_name(self, sheet_names):
        if not isinstance(sheet_names, list):
            sheet_names = [sheet_names]
        for sheet_name in sheet_names:
            if sheet_name in self._wb.sheet_names():
                sheet = self._wb.sheet_by_name(sheet_name)
                return sheet
        return None

    def get_header_row(self, sheet):
        row_num = 3 if sheet.row_values(0)[3].strip() == "" else 0

        header_row = sheet.row_values(row_num)
        normalised_headers = [
            header.upper().replace(" ", "_") for header in header_row
        ]
        return normalised_headers, row_num

    def convert_to_datetime(self, value):
        return datetime.datetime(
            *xlrd.xldate_as_tuple(value, self._wb.datemode)
        )

    def number_rows(self, sheet):
        return sheet.nrows

    def row_values(self, sheet, row_index):
        return sheet.row_values(row_index)


class PandasAdapter:
    def __init__(self, filename):
        self._filename = filename

    @staticmethod
    def create(filename, **kwargs):
        return PandasAdapter(filename)

    def find_first_sheet_by_name(self, sheet_names):
        if not isinstance(sheet_names, list):
            sheet_names = [sheet_names]
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(
                    self._filename,
                    sheet_name=sheet_name,
                    index_col=None,
                    header=None,
                )
                df = df.where(pd.notnull(df), "")
                # Replace occurrences of _x000D_ with an empty string (i.e. pandas' version of \r
                df = df.replace("_x000D_", "", regex=True)
                return df
            except Exception:
                pass
        return None

    def get_header_row(self, sheet):
        indicator_cell_value = sheet.values[0, 3]
        row_num = 0 if indicator_cell_value else 3

        header_row = sheet.values[row_num]
        normalised_headers = [
            (header or "").upper().replace(" ", "_") for header in header_row
        ]
        return normalised_headers, row_num

    def convert_to_datetime(self, value):
        return value

    def number_rows(self, sheet):
        return len(sheet)

    def row_values(self, sheet, row_index):
        return sheet.iloc[row_index]


def secure_open_workbook(filename, **kwargs):
    if filename.lower().endswith("xlsx"):
        return PandasAdapter.create(filename, read_only=True)

    defusedxml.defuse_stdlib()
    try:
        return XlrdAdapter(xlrd.open_workbook(filename=filename, **kwargs))
    except EntitiesForbidden:
        raise ValueError("Please use an excel file without XEE")


def get_header_index_any_match(headers, names):
    if not isinstance(names, list):
        names = [names]
    for n in names:
        try:
            return headers.index(n)
        except ValueError:
            continue
    raise ValueError(f"Unabled to find column named one of: {names}")


def dedup_and_flag_discrepancies(items, key="id"):
    by_key = {}
    identical_dups = 0
    for item in items:
        k = item[key]
        if k in by_key:
            if by_key[k] != item:
                print(f"Warning, mismatch found for {item}")
            else:
                identical_dups += 1
        else:
            by_key[k] = item
    print(f"Removed {identical_dups} identical duplicates")
    return [by_key[k] for k in sorted(by_key.keys())]


def extract_manfacturers(wb):
    sheet = wb.find_first_sheet_by_name(["Manufacturer IDs (B10)"])

    headers, row_num = wb.get_header_row(sheet)
    id_col = get_header_index_any_match(headers, "MFR_ID")
    name_col = get_header_index_any_match(headers, "MANUFACTURER")
    location_col = get_header_index_any_match(headers, "LOCATION")
    last_modified_col = get_header_index_any_match(
        headers, "DATE_CREATED_OR_LAST_MODIFIED"
    )

    result = []
    for i in range(row_num + 1, wb.number_rows(sheet)):
        row = wb.row_values(sheet, i)
        last_modified = row[last_modified_col]

        if not isinstance(last_modified, str):
            last_modified = wb.convert_to_datetime(last_modified)

        if last_modified:
            last_modified = last_modified.date().isoformat()

        result.append(
            {
                "id": int(row[id_col]),
                "name": str(row[name_col]),
                "location": str(row[location_col]),
                "created_or_last_modified": last_modified,
            }
        )
    return result


def extract_spns(wb):
    sheet = wb.find_first_sheet_by_name(["SPNs & PGNs", "SPs & PGs"])
    headers, row_num = wb.get_header_row(sheet)

    id_col = get_header_index_any_match(headers, "SPN")
    name_col = get_header_index_any_match(headers, ["SPN_NAME", "SP_LABEL"])
    description_col = get_header_index_any_match(
        headers, ["SPN_DESCRIPTION", "SP_DESCRIPTION"]
    )
    length_col = get_header_index_any_match(
        headers, ["SPN_LENGTH", "SP_LENGTH"]
    )
    resolution_col = get_header_index_any_match(
        headers, ["RESOLUTION", "SCALING"]
    )
    offset_col = get_header_index_any_match(headers, "OFFSET")
    data_range_col = get_header_index_any_match(headers, "DATA_RANGE")
    operational_range_col = get_header_index_any_match(
        headers, "OPERATIONAL_RANGE"
    )
    units_col = get_header_index_any_match(headers, ["UNITS", "UNIT"])
    document_col = get_header_index_any_match(
        headers, ["SPN_DOCUMENT", "SP_DOCUMENT"]
    )

    result = []
    for i in range(row_num + 1, wb.number_rows(sheet)):
        row = wb.row_values(sheet, i)
        spn_id = row[id_col]
        if spn_id == "" or spn_id is None:
            continue

        result.append(
            {
                "id": int(spn_id),
                "name": str(row[name_col]),
                "description": str(row[description_col]),
                "length": str(row[length_col]),
                "resolution": str(row[resolution_col]),
                "offset": str(row[offset_col]),
                "data_range": str(row[data_range_col]),
                "operational_range": str(row[operational_range_col]),
                "units": str(row[units_col]),
                "source_document": str(row[document_col]),
            }
        )

    return dedup_and_flag_discrepancies(result)


def int_or_str(s):
    try:
        return int(s)
    except:
        return s


def extract_pgns(wb):
    sheet = wb.find_first_sheet_by_name(["SPNs & PGNs", "SPs & PGs"])
    headers, row_num = wb.get_header_row(sheet)

    id_col = get_header_index_any_match(headers, "PGN")
    name_col = get_header_index_any_match(
        headers, ["PARAMETER_GROUP_LABEL", "PG_LABEL"]
    )
    acronym_col = get_header_index_any_match(
        headers, ["ACRONYM", "PG_ACRONYM"]
    )
    description_col = get_header_index_any_match(
        headers, ["PGN_DESCRIPTION", "PG_DESCRIPTION"]
    )
    length_col = get_header_index_any_match(
        headers,
        ["PGN_DATA_LENGTH", "PG_DATA_LENGTH", "PG_DATA_MINIMUM_LENGTH"],
    )
    rate_col = get_header_index_any_match(headers, "TRANSMISSION_RATE")

    spn_id_col = get_header_index_any_match(headers, "SPN")
    spn_position_col = get_header_index_any_match(
        headers, ["SPN_POSITION_IN_PGN", "SP_POSITION_IN_PG"]
    )
    document_col = get_header_index_any_match(
        headers, ["PGN_DOCUMENT", "PG_DOCUMENT"]
    )

    result = []
    current_pgn = {"id": "bogus"}
    for i in range(row_num + 1, wb.number_rows(sheet)):
        row = wb.row_values(sheet, i)
        pgn_id = row[id_col]
        if pgn_id == "" or pgn_id is None:
            continue

        pgn_id = int(pgn_id)
        if pgn_id != current_pgn["id"]:
            # new record found
            current_pgn = {
                "id": pgn_id,
                "name": str(row[name_col]),
                "acronym": str(row[acronym_col]),
                "description": str(row[description_col]),
                "length": int_or_str(row[length_col]),
                "rate": str(row[rate_col]),
                "source_document": str(row[document_col]),
                "spns": [],
            }
            result.append(current_pgn)

        # Only append SPNs that are valid
        spn_id = row[spn_id_col] or ""
        if spn_id != "":
            # TODO - check for consistency?
            current_pgn["spns"].append(
                {"id": int(spn_id), "start_pos": str(row[spn_position_col])}
            )

    return dedup_and_flag_discrepancies(result)


def extract_industry_groups(wb):
    sheet = wb.find_first_sheet_by_name(["Industry Groups (B1)"])
    headers, row_num = wb.get_header_row(sheet)

    id_col = get_header_index_any_match(headers, "INDUSTRY_GROUP_ID")
    name_col = get_header_index_any_match(
        headers, "INDUSTRY_GROUP_DESCRIPTION"
    )

    result = []
    for i in range(row_num + 1, wb.number_rows(sheet)):
        row = wb.row_values(sheet, i)
        result.append(
            {
                "id": int(row[id_col]),
                "name": str(row[name_col]),
            }
        )
    return result


def extract_source_addresses(wb):
    result = {}

    for sa_type, sheet_names in [
        ("Global", ["Global Source Addresses (B2)"]),
        ("IG1", ["IG1 Source Addresses (B3)"]),
        ("IG2", ["IG2 Source Addresses (B4)"]),
        ("IG3", ["IG3 Source Addresses (B5)"]),
        ("IG4", ["IG4 Source Addresses (B6)"]),
        ("IG5", ["IG5 Source Addresses (B7)"]),
    ]:

        sheet = wb.find_first_sheet_by_name(sheet_names)
        headers, row_num = wb.get_header_row(sheet)

        id_col = get_header_index_any_match(headers, "SOURCE_ADDRESS_ID")
        name_col = get_header_index_any_match(headers, ["NAME", "FUNCTION"])

        addresses = {}
        for i in range(row_num + 1, wb.number_rows(sheet)):
            row = wb.row_values(sheet, i)
            id_val = int(row[id_col])
            name_val = str(row[name_col])

            if name_val.startswith("thru "):
                parts = name_val.split(" ")
                until = int(parts[1]) + 1
                name_val = " ".join(["Reserved"] + parts[4:])
            else:
                until = id_val + 1

            for id in range(id_val, until):
                addresses[id] = name_val

        result[sa_type] = addresses
    return result


def spec_from_workbook(wb: xlrd.Book):
    return {
        "Manufacturers": extract_manfacturers(wb),
        "PGNs": extract_pgns(wb),
        "SPNs": extract_spns(wb),
        "IndustryGroups": extract_industry_groups(wb),
        "SourceAddresses": extract_source_addresses(wb),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "digital_annex_xls",
        type=str,
        help="the J1939 Digital Annex .xls excel file used as input",
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

    print(args.digital_annex_xls)
    defusedxml.defuse_stdlib()
    wb = secure_open_workbook(filename=args.digital_annex_xls, on_demand=True)
    spec = spec_from_workbook(wb)
    json.dump(spec, args.json_file, indent=2 if args.pretty else None)


if __name__ == "__main__":
    main()
