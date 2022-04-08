import pytest

from decoda import *


@pytest.mark.parametrize(
    ["can_id", "priority", "pgn", "sa", "da"],
    [
        (0x0CF004FE, 3, 61444, Address(254), BroadcastAddress),
        (0x98FEF4FE, 6, 65268, Address(254), BroadcastAddress),
        (0x18F00930, 6, 61449, Address(48), BroadcastAddress),
        (0x18F00131, 6, 61441, Address(49), BroadcastAddress),
        (0x00DEAA50, 0, 0xDE00, Address(0x50), Address(0xAA)),
        (0x00000102, 0, 0, Address(2), Address(1)),
    ],
)
def test_it_unpacks_can_id(can_id, priority, pgn, sa, da):
    assert (priority, pgn, sa, da) == parts_from_can_id(can_id), hex(pgn)


@pytest.mark.parametrize(
    ["pf", "ps", "da"],
    [
        (0x01, 0x00, Address(0)),
        (0x01, 0x01, Address(1)),
        (0xEF, 0x09, Address(9)),
        (0xF0, 0x00, BroadcastAddress),
        (0xF1, 0x00, BroadcastAddress),
        (0xF2, 0x00, BroadcastAddress),
    ],
)
def test_it_can_get_destination_address_from_pf_and_ps(pf, ps, da):
    assert Address.from_pf_and_ps(pf, ps) == da
