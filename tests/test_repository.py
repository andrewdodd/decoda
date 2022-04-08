import pytest

from decoda import *


def test_it_can_lookup_manufacturers():
    repo = Repo(
        Manufacturer,
        manufacturer_from_dict,
        [
            {"id": 0, "name": "First"},
            {"id": 1, "name": "Second"},
        ],
    )

    assert repo.get_by_id(0).name == "First"
    assert repo.get_by_id(1).name == "Second"


def test_it_raises_error_if_manufacturer_not_found():
    repo = Repo(Manufacturer, manufacturer_from_dict, [])
    with pytest.raises(UnknownReferenceError) as e:
        repo.get_by_id(0)
    assert str(e.value) == "Manufacturer not found for id: 0"


def test_it_can_lookup_spns():
    repo = Repo(
        SPN,
        spn_from_dict,
        [
            {
                "id": 0,
                "name": "First",
                "description": "Desc",
                "bit_length": "8",
                "units": "asocinasocin",
            },
            {
                "id": 1,
                "name": "Second",
                "description": "Desc",
                "bit_length": "8",
                "units": "asocinasocin",
            },
        ],
    )

    assert "First" == repo.get_by_id(0).name
    assert "Second" == repo.get_by_id(1).name


def test_it_raises_error_if_spn_not_found():
    repo = Repo(SPN, spn_from_dict, [])
    with pytest.raises(UnknownReferenceError) as e:
        repo.get_by_id(0)
    assert str(e.value) == "SPN not found for id: 0"


def test_it_can_lookup_pgns():
    spns = Repo(
        SPN,
        spn_from_dict,
        [
            {
                "id": 0,
                "name": "First",
                "description": "Desc",
                "bit_length": "8",
            },
            {
                "id": 1,
                "name": "Second",
                "description": "Desc",
                "bit_length": "8",
            },
        ],
    )

    repo = Repo(
        PGN,
        pgn_from_dict,
        [
            {
                "id": 0,
                "label": "First PGN",
                "description": "",
                "transmission_rate": "50 ms",
                "length": 8,
                "spns": [
                    {"id": 0, "start_pos": "1.1"},
                    {"id": 1, "start_pos": "1.3"},
                ],
            }
        ],
        spns,
    )

    assert "First PGN" == repo.get_by_id(0).name


def test_it_raises_error_if_pgn_not_found():
    repo = Repo(PGN, pgn_from_dict, [])
    with pytest.raises(UnknownReferenceError) as e:
        repo.get_by_id(0)
    assert str(e.value) == "PGN not found for id: 0"
