from enum import Enum
from google.protobuf.struct_pb2 import Struct
from .message_pb2 import (
    MessageContent as PbMessage,
    MessageContentPart as PbMessagePart,
    MessagePartReference as PbMessagePartReference,
    MessagePartEntry,
)
from google.protobuf.json_format import MessageToDict, ParseDict
from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class MessageContentPart:
    part_id: int
    media_type: str
    metadata: dict
    payload: bytes


@dataclass_json
@dataclass
class MessagePartReference:
    part_id: int
    ref_message_id: str
    ref_part_id: int


@dataclass_json
@dataclass
class MessageContent:
    metadata: dict
    message_parts: list[MessageContentPart | MessagePartReference]

    def __init__(
        self,
        metadata: dict = {},
        message_parts: list[MessageContentPart | MessagePartReference] = None,
    ):
        self.metadata = metadata
        self.message_parts = []
        if message_parts:
            for message_part in message_parts:
                if message_part.part_id:
                    self.message_parts.append(message_part)
            for message_part in message_parts:
                if not message_part.part_id:
                    if isinstance(message_part, MessagePartReference):
                        self.add_part_reference(
                            message_part.ref_message_id, message_part.ref_part_id
                        )
                    elif isinstance(message_part, MessageContentPart):
                        self.add_part(
                            message_part.media_type,
                            message_part.metadata,
                            message_part.payload,
                        )
                    else:
                        raise ValueError(
                            f"Unexpected object type in list: {type(message_part)}"
                        )

    def add_part(self, media_type, metadata, payload) -> MessageContentPart:
        message_part = MessageContentPart(
            part_id=self.get_next_part_id(),
            media_type=media_type,
            metadata=metadata,
            payload=payload,
        )
        self.message_parts.append(message_part)
        return message_part

    def add_part_reference(self, ref_message_id: str, ref_part_id: int):
        message_part_reference = MessagePartReference(
            part_id=self.get_next_part_id(),
            ref_message_id=ref_message_id,
            ref_part_id=ref_part_id,
        )
        return message_part_reference

    def get_next_part_id(self) -> int:
        return (
            max(
                [
                    mp.part_id
                    for mp in self.message_parts
                    if isinstance(mp, MessageContentPart)
                ]
                + [0]
            )
            + 1
        )

    @classmethod
    def from_bytes(cls, data: bytes):
        return decode_message(data)

    def to_bytes(
        self,
    ) -> bytes:
        return encode_message(self)


def dict_to_struct(d: dict) -> Struct:
    s = Struct()
    s.update(d)
    return s


def struct_to_dict(s: Struct) -> dict:
    return dict(s)


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
