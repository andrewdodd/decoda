# Copyright Andrew Dodd
import attr

from .main import Address


def parts_from_pgn(pgn):
    edp = pgn >> 17
    dp = pgn >> 16
    pf = 0xFF & (pgn >> 8)
    ps = 0xFF & (pgn)
    return edp, dp, pf, ps


def parts_from_can_id(can_id):
    sa = 0xFF & can_id
    pgn = 0x3FFFF & (can_id >> 8)

    edp, dp, pf, ps = parts_from_pgn(pgn)
    da = Address.from_pf_and_ps(pf, ps)

    if pgn < 0xF000:
        pgn &= 0xFF00

    priority = 0x7 & (can_id >> (8 + 18))
    return priority, pgn, Address(sa), da


@attr.s(frozen=True)
class Message:
    priority = attr.ib()
    src_address = attr.ib()
    dst_address = attr.ib()
    pgn = attr.ib()
    decoded = attr.ib()


class Decoda:
    def __init__(self, spec, callback=None, error_handler=None):
        self.__spec__ = spec
        self._callback = callback if callback else lambda x: print(x)
        self._handle_error = (
            error_handler if error_handler else lambda x: print(x)
        )

    def get_callback(self):
        return self._callback

    def set_callback(self, callback):
        if not callback:
            raise ValueError("Callback must be valid")
        self._callback = callback

    def set_error_handler(self, error_handler):
        if not error_handler:
            raise ValueError("Error handler must be valid")
        self._handle_error = error_handler

    def handle_frame(self, can_id, payload):
        try:
            priority, pgn_id, sa, da = parts_from_can_id(can_id)
            pgn = self.__spec__.PGNs.get_by_id(pgn_id)
            decoded = pgn.decode(payload)

            self._callback(Message(priority, sa, da, pgn, decoded))
        except ValueError as e:
            self._handle_error(e)

    def handle_message(self, priority, sa, da, pgn_id, payload):
        try:
            pgn = self.__spec__.PGNs.get_by_id(pgn_id)
            decoded = pgn.decode(payload)
            self._callback(Message(priority, sa, da, pgn, decoded))
        except ValueError as e:
            self._handle_error(e)


class ConnectionManager:
    def __init__(self, decoda, defragmenting_error_callback):
        self._active_defrags = {}
        self._decoda = decoda
        self._callback = decoda.get_callback()
        self._handle_error = defragmenting_error_callback
        decoda.set_callback(self.handle_message)

    def handle_message(self, message):
        # First publish the message outwards
        self._callback(message)

        try:
            # Next, attempt to look for reassembly opportunities
            if message.pgn.id == 60416:  # TP - Connection Management
                control_spn = next(
                    value for value in message.decoded if value.id == 2556
                )

                if control_spn.value == "Clear to Send":
                    self._start_new_defragmenting(message)
                if control_spn.value == "Broadcast Announce Message":
                    self._start_new_defragmenting(message)

            if message.pgn.id == 60160:  # TP - Data Transfer
                self._handle_fragment(message)

        except Exception as e:
            print(e)
            raise

    def _start_new_defragmenting(self, message):
        to_from_pair = (message.src_address, message.dst_address)
        if to_from_pair in self._active_defrags:
            progress = self._active_defrags[to_from_pair]
            self._handle_error("incomplete defragmentation", progress)

        packet_count = next(
            value for value in message.decoded if value.id == 2561
        ).value
        next_packet_number = next(
            value for value in message.decoded if value.id == 2562
        ).value
        pgn = next(
            value for value in message.decoded if value.id == 2563
        ).value
        self._active_defrags[to_from_pair] = {
            "pgn": pgn,
            "packet_count": packet_count,
            "next_packet_number": next_packet_number,
            "fragments": [],
            "original_message": message,
        }

    def _handle_fragment(self, message):
        to_from_pair = (message.src_address, message.dst_address)
        if to_from_pair not in self._active_defrags:
            self._handle_error("fragment received without control", message)
            return

        pair_state = self._active_defrags[to_from_pair]
        seq_no = next(
            value for value in message.decoded if value.id == 2572
        ).value

        if seq_no != pair_state["next_packet_number"]:
            self._handle_error("fragment received out of order", message)
            return

        pair_state["next_packet_number"] = seq_no + 1
        fragment = next(
            value for value in message.decoded if value.id == 2573
        ).value
        pair_state["fragments"].append(fragment)

        if pair_state["next_packet_number"] > pair_state["packet_count"]:
            reassembled = bytes()
            for fragment in pair_state["fragments"]:
                reassembled += fragment
            original_msg = pair_state["original_message"]
            priority = original_msg.priority
            sa = original_msg.src_address
            da = original_msg.dst_address
            self._decoda.handle_message(
                priority, sa, da, pair_state["pgn"], reassembled
            )
            del self._active_defrags[to_from_pair]
