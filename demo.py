#!python3
from binascii import hexlify

from decoda import ConnectionManager, Decoda, parts_from_can_id, spec_provider


def demo_parts_functions():
    print("Handle CAN IDs")
    print("=" * 50)
    for can_id in [
        0x0CF004FE,
        0x98FEF4FE,
        0x18F00930,
        0x18F00131,
        0x00DEAA50,
        0x00000102,
    ]:
        priority, pgn, sa, da = parts_from_can_id(can_id)
        print(
            f"CAN ID:{can_id:x} gives Priority:{priority}  PGN:{pgn}  SA:{sa} DA:{da}"
        )


def demo_lookup_pgns(pgn_repo):
    print("LOOKUP PGN INFO")
    print("=" * 50)
    for id in [0, 65226]:
        pgn = pgn_repo.get_by_id(id)
        print(f"{pgn.id}: {pgn.name}")
        print(
            " -- TransmissionRate:{}".format(
                " ".join((pgn.transmission_rate or "").split("\n"))
            )
        )
        print(f" -- Length:{pgn.length}")
        print()


def demo_lookup_spns(spn_repo):
    print("LOOKUP SPN INFO")
    print("=" * 50)
    for id in [695, 1215]:
        spn = spn_repo.get_by_id(id)
        print(f"{spn.id}: {spn.name}")
        print(f" -- ValueDecoder: {spn.value_decoder}")
        print()


def demo_industry_groups(repo):
    print("INDUSTRY GROUP INFO")
    ig_repo = repo.IndustryGroups
    print("=" * 50)
    for id in [0, 1, 2]:
        ig = ig_repo.get_by_id(id)
        print(f"{ig.id}: {ig.description}")
        for address in [0, 1, 239, 240, 251]:
            print(f" - Address: {address} = {repo.preferred_address_name(address, id)}")


def print_decoding_for_payload(payload, pgn):
    print(f"Decoding: {hexlify(payload)}")
    decoded_spns = pgn.decode(payload)
    for decoded in decoded_spns:
        print(f" - {decoded}")


def demo_pgn(pgn):
    print("=" * 50)
    print(f"PGN {pgn.id} - {pgn.name}")
    print()
    payload = (0x123456789ABCDEF0).to_bytes(8, "big")
    print_decoding_for_payload(payload, pgn)
    print()
    payload = (0x123456789ABCDEF0).to_bytes(8, "little")
    print_decoding_for_payload(payload, pgn)


def demo_decoding(pgn_repo):
    print("=" * 50)
    print("Demo decoding regular PGNs")
    print("=" * 50)
    demo_pgn(pgn_repo.get_by_id(0))

    pgn = pgn_repo.get_by_id(65226)
    print("=" * 50)
    print(f"PGN {pgn.id} - {pgn.name}")
    print()
    payload = bytes(
        [0x12, 0x34]  # Lamps
        + [0x10, 0x00, 0x01, 0x05]  # SPN 16 - FMI 1 - Count 5
        + [0x2E, 0x00, 0x02, 0x09]  # SPN 46 - FMI 2 - Count 9
        + [0xB5, 0x0D, 0x03, 0x01]  # SPN 3509 - FMI 1 - Count 1
    )
    print_decoding_for_payload(payload, pgn)
    print("=" * 50)


def demo_live_decoding(spec):
    def handle_defrag_error(error_reason, info):
        print("*" * 30)
        print(error_reason, info)
        print("*" * 30)

    def print_defragged(msg):
        src = f"{msg.src_address}: {spec.preferred_address_name(msg.src_address)}"
        dst = f"{msg.dst_address}: {spec.preferred_address_name(msg.dst_address)}"
        print(f"RECV: {msg.pgn.id} - {msg.pgn.name} - {src} => {dst}")
        for decoded in msg.decoded:
            print(f" - {decoded}")

    decoda = Decoda(spec, print_defragged)

    cm = ConnectionManager(decoda, handle_defrag_error)

    clear_to_send_pgn_65526 = bytes(
        [
            17,  # Clear to send
            3,  # Num packes
            1,  # Next packet seq no
            0xFF,  # RFU
            0xFF,  # RFU
            0xCA,  # LSB PGN
            0xFE,  # PGN
            0x00,  # MSB PGN
        ]
    )

    decoda.handle_message(1, 1, 1, 60416, clear_to_send_pgn_65526)

    payload = bytes(
        [0x12, 0x34]  # Lamps
        + [0x10, 0x00, 0x01, 0x05]  # SPN 16 - FMI 1 - Count 5
        + [0x2E, 0x00, 0x01, 0x09]  # SPN 46 - FMI 1 - Count 9
        + [0x2E, 0x00, 0x02, 0x09]  # SPN 46 - FMI 2 - Count 9
        + [0xB5, 0x0D, 0x03, 0x01]  # SPN 3509 - FMI 1 - Count 1
    )
    decoda.handle_message(1, 1, 1, 60160, bytes([1]) + payload[:7])
    decoda.handle_message(1, 1, 1, 60160, bytes([2]) + payload[7:14])
    # Double up will be ignored and show up as error
    decoda.handle_message(1, 1, 1, 60160, bytes([2]) + payload[7:14])
    decoda.handle_message(1, 1, 1, 60160, bytes([3]) + payload[14:])
    # Double up will be ignored and show up as error
    decoda.handle_message(1, 1, 1, 60160, bytes([3]) + payload[14:])

    # Demo that it works with multiple active transfers
    decoda.handle_message(1, 2, 1, 60416, clear_to_send_pgn_65526)
    decoda.handle_message(1, 1, 2, 60416, clear_to_send_pgn_65526)

    decoda.handle_message(1, 2, 1, 60160, bytes([1]) + payload[:7])
    decoda.handle_message(1, 1, 2, 60160, bytes([1]) + payload[:7])
    decoda.handle_message(1, 1, 2, 60160, bytes([2]) + payload[7:14])
    decoda.handle_message(1, 2, 1, 60160, bytes([2]) + payload[7:14])
    print(
        f"ConnectionManager should have 2 active items atm: {len(cm._active_defrags)}"
    )
    decoda.handle_message(1, 2, 1, 60160, bytes([3]) + payload[14:])
    decoda.handle_message(1, 1, 2, 60160, bytes([3]) + payload[14:])


def run():
    try:
        spec = spec_provider.provide()
    except FileNotFoundError:
        print(
            """UNABLE TO RUN DEMO!!!

This demo expects that you provide a spec file, but one has not been
found.

You can produce a spec file using the SAE Digital Annex and the helper
scripts that are provided with this library, or you can produce one by
hand.

You should either place the spec file in the same directory you are
executing from and title it "decoda_spec.json", or provide an
environment variable "J1939_SPEC_PATH" to the file.
        """
        )
        return

    demo_parts_functions()
    demo_lookup_pgns(spec.PGNs)
    demo_lookup_spns(spec.SPNs)
    demo_industry_groups(spec)
    demo_decoding(spec.PGNs)
    demo_live_decoding(spec)


if __name__ == "__main__":
    run()
