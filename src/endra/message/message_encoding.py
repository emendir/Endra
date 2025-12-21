from .message import MessageContent, MessageContentPart, MessagePartReference

from google.protobuf.json_format import MessageToDict, ParseDict
from .message_pb2 import (
    MessageContent as PbMessage,
    MessageContentPart as PbMessagePart,
    MessagePartReference as PbMessagePartReference,
    MessagePartEntry,
)
from google.protobuf.struct_pb2 import Struct


def dict_to_struct(d: dict) -> Struct:
    s = Struct()
    s.update(d)
    return s


def struct_to_dict(s: Struct) -> dict:
    return dict(s)


# Encode Python MessageContent object to protobuf


def encode_message(msg: MessageContent) -> bytes:
    pb_msg = PbMessage()
    pb_msg.metadata.CopyFrom(dict_to_struct(msg.metadata))

    for part in msg.message_parts:
        entry = pb_msg.message_parts.add()
        if isinstance(part, MessageContentPart):
            entry.part_data.part_id = part.part_id
            entry.part_data.media_type = part.media_type
            entry.part_data.metadata.CopyFrom(dict_to_struct(part.metadata))
            entry.part_data.payload = part.payload
        elif isinstance(part, MessagePartReference):
            entry.part_ref.part_id = part.part_id
            entry.part_ref.ref_message_id = part.ref_message_id
            entry.part_ref.ref_part_id = part.ref_part_id
        else:
            raise TypeError(f"Unknown part type: {type(part)}")
    return pb_msg.SerializeToString()


# Decode protobuf MessageContent to Python MessageContent object


def decode_message(data: bytes) -> MessageContent:
    pb_msg = PbMessage()
    pb_msg.ParseFromString(data)
    parts = []
    for entry in pb_msg.message_parts:
        if entry.HasField("part_data"):
            part_data = entry.part_data
            parts.append(
                MessageContentPart(
                    part_id=part_data.part_id,
                    media_type=part_data.media_type,
                    metadata=struct_to_dict(part_data.metadata),
                    payload=part_data.payload,
                )
            )
        elif entry.HasField("part_ref"):
            part_ref = entry.part_ref
            parts.append(
                MessagePartReference(
                    part_id=part_ref.part_id,
                    ref_message_id=part_ref.ref_message_id,
                    ref_part_id=part_ref.ref_part_id,
                )
            )
    return MessageContent(metadata=struct_to_dict(pb_msg.metadata), message_parts=parts)
