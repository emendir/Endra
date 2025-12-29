from enum import Enum
from google.protobuf.struct_pb2 import Struct
from .message_v1_pb2 import (
    MessageContent as PbMessage,
    EmbeddedContentPart as PbMessagePart,
    MessageAttachment as PbMessageAttachment,
    ReferencedContentPart as PbReferencedContentPart,
    MessagePartEntry,
)
from google.protobuf.json_format import MessageToDict, ParseDict


def dict_to_struct(d: dict) -> Struct:
    s = Struct()
    s.update(d)
    return s


def struct_to_dict(s: Struct) -> dict:
    return dict(s)
