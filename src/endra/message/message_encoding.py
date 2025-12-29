"""API for encoding and decoding MessageContent and MessageAttachment.

Uses versioned encoding, encoding using the set default codec,
and automatically determining the correct codec for decoding.
"""

from .message_encoding_versions import message_encoding_v1, attachment_encoding_v1
from .message_content import MessageContent, MessageAttachment
from codec_versioning import (
    encode_versioned,
    decode_versioned,
    load_codec_modules,
)


# ADD NEW ENCODING MODULE VERSIONS HERE
MESSAGE_CODECS = load_codec_modules([message_encoding_v1])
ATTACHMENT_CODECS = load_codec_modules([attachment_encoding_v1])

# SET DEFAULT ENCODING VERSION HERE
DEFAULT_MESSAGE_CODEC = MESSAGE_CODECS[message_encoding_v1.CODEC_VERSION]
DEFAULT_ATTACHMENT_CODEC = ATTACHMENT_CODECS[attachment_encoding_v1.CODEC_VERSION]


def encode_message(content: MessageContent) -> bytes:
    """Encode a MessageContent object with encoding versioning."""
    return encode_versioned(content, DEFAULT_MESSAGE_CODEC)


def encode_attachment(attachment: MessageAttachment) -> bytes:
    """Encode a MessageAttachment object with encoding versioning."""
    return encode_versioned(attachment, DEFAULT_ATTACHMENT_CODEC)


def decode_message(data: bytes) -> MessageContent:
    """Decode a MessageContent object with encoding versioning."""
    return decode_versioned(data, MESSAGE_CODECS)


def decode_attachment(data: bytes) -> MessageAttachment:
    """Decode a MessageAttachment object with encoding versioning."""
    return decode_versioned(data, ATTACHMENT_CODECS)
