import _auto_run_with_pytest

from endra.message import (
    Message,
    MessagePart,
    encode_message,
    decode_message,
)


def test_encode_decode_message():
    message = Message(
        {"version": 1},
        [],
    )

    message.add_part("Part1", {}, "Hello there!".encode())
    message.add_part("Part2", {"scale": 1.1}, "IMAGE_PLACEHOLDER".encode())
    message.add_part_reference("laskfjasfd", 3)
    assert decode_message(encode_message(message)) == message
    print(len(encode_message(message)))
