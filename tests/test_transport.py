from decoda import *


def bytes_from_payload(payload):
    payload_len = len(payload)
    if payload_len % 2 != 0:
        raise Exception("incorrect length")
    if (payload_len // 2) < 8:
        raise Exception("insufficient bytes in payload")
    if payload_len // 2 > 1785:
        raise Exception("too many bytes in payload")
    ints = []
    while len(payload) > 0:
        ints.append(int(payload[:2], 16))
        payload = payload[2:]
    return bytes(ints)


def test_embeddeduse_peer_to_peer_example(spec: J1939Spec):
    # https://www.embeddeduse.com/2020/01/17/introduction-to-the-sae-j1939-standard/
    pgn = spec.PGNs.get_by_id(61184)
    payload = "0203029103000000"
    byte_payload = bytes_from_payload(payload)
    decoded = pgn.decode(byte_payload)

    spn_val = decoded[0]

    assert spn_val.value == bytes(
        [0x02, 0x03, 0x02, 0x91, 0x03, 0x00, 0x00, 0x00]
    )
    assert spn_val.display_value == payload


# TODO - Test the defragmentation
