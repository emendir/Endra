from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class MessagePart:
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
class Message:
    metadata: dict
    message_parts: list[MessagePart | MessagePartReference]

    def add_part(self, media_type, metadata, payload) -> MessagePart:
        message_part = MessagePart(
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
                [mp.part_id for mp in self.message_parts if isinstance(mp, MessagePart)]
                + [0]
            )
            + 1
        )
