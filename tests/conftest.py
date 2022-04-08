import json
from typing import Dict

import pytest

from decoda.main import PGN
from decoda.spec_loader import repo_provider


@pytest.fixture(scope="session")
def spec():
    try:
        return repo_provider.provide()
    except FileNotFoundError:
        pytest.skip("Unable to find a spec file")


@pytest.fixture()
def pgn_0(spec) -> PGN:
    return spec.PGNs.get_by_id(0)


@pytest.fixture()
def pgn_10240(spec) -> PGN:
    return spec.PGNs.get_by_id(10240)


@pytest.fixture()
def pgn_65226(spec) -> PGN:
    return spec.PGNs.get_by_id(65226)


@pytest.fixture()
def pgn_61444(spec) -> PGN:
    return spec.PGNs.get_by_id(61444)


@pytest.fixture()
def pgn_43008(spec) -> PGN:
    return spec.PGNs.get_by_id(43008)


@pytest.fixture()
def pgn_55552(spec) -> PGN:
    return spec.PGNs.get_by_id(55552)


@pytest.fixture()
def pgn_64965(spec) -> PGN:
    return spec.PGNs.get_by_id(64965)


@pytest.fixture()
def pgn_64958(spec) -> PGN:
    return spec.PGNs.get_by_id(64958)


@pytest.fixture()
def pgn_64912(spec) -> PGN:
    return spec.PGNs.get_by_id(64912)


@pytest.fixture()
def pgn_1792(spec) -> PGN:
    return spec.PGNs.get_by_id(1792)


@pytest.fixture()
def pgn_61445(spec) -> PGN:
    return spec.PGNs.get_by_id(61445)


@pytest.fixture()
def pgn_65260(spec) -> PGN:
    return spec.PGNs.get_by_id(65260)


@pytest.fixture()
def pgn_60416(spec) -> PGN:
    return spec.PGNs.get_by_id(60416)
