import _auto_run_with_pytest

from endra.message import (
    MessageAttachment,
    MessageContent,
    EmbeddedContentPart,
    encode_message,
    decode_message,
    encode_attachment,
    decode_attachment,
)


def test_encode_decode_message():
    message = MessageContent(
        {"version": 1},
        [],
    )

    message.add_embedded_part("Part1", {}, "Hello there!".encode())
    message.add_embedded_part("Part2", {"scale": 1.1}, "IMAGE_PLACEHOLDER".encode())
    message.add_referenced_part("laskfjasfd", 3)
    message.add_attached_part(
        rendering_metadata={"image": {"height": 800}},
        attachment_id="as;ldkfjsd".encode(),
    )
    assert decode_message(encode_message(message)) == message
    print(len(encode_message(message)))


def test_attachment_encoding():
    attachment = MessageAttachment.create(
        media_type="text/markdown",
        derived_properties={},
        user_attributes={"language": "English"},
        payload="*Hello there!*".encode(),
    )

    assert decode_attachment(encode_attachment(attachment)) == attachment
