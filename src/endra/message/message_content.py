from dataclasses import dataclass
from dataclasses_json import dataclass_json

from abc import ABC


class GenericContentPart(ABC):
    """A subsection of a message content."""

    part_id: int


@dataclass_json
@dataclass
class EmbeddedContentPart(GenericContentPart):
    """A message content part that embeds its payload."""

    part_id: int
    media_type: str
    rendering_metadata: dict
    payload: bytes


@dataclass_json
@dataclass
class ReferencedContentPart(GenericContentPart):
    """A message content part that refers to another message content part."""

    part_id: int
    ref_content_id: bytes
    ref_part_id: int


@dataclass_json
@dataclass
class AttachedContentPart(GenericContentPart):
    """A message content part that references a MessageAttachment."""

    part_id: int
    rendering_metadata: dict
    attachment_id: bytes


@dataclass_json
@dataclass
class MessageAttachment:
    """Message Content Part Attachment


    Data and non-rendering metadata of a file outsourced from a ContentPart
    of a MessageContent.
    The MessageAttachment is stored in a separate block from the MessageContent
    block.
    """

    # media type is MIME-compatible
    media_type: str
    # hash includes algorithm and hash
    payload_hash: str
    # size is the number of bytes
    size: int

    # metadata extracted from payload depending on media type,
    # e.g. image width & height, audio or video length, embedded title
    derived_properties: dict
    # metadata defined by user, e.g. filename, title-override
    user_attributes: dict

    # raw file data
    payload: bytes

    def _calculate_hash(self) -> str:
        return ""

    def verify_hash(self) -> bool:
        return self.hash == self._calculate_hash()

    def _calculate_size(self) -> None:
        return len(self.payload)

    @classmethod
    def create(
        cls,
        media_type: str,
        derived_properties: dict,
        user_attributes: dict,
        payload: bytes,
    ):
        attachment = cls(
            media_type=media_type,
            payload_hash=None,
            size=None,
            derived_properties=derived_properties,
            user_attributes=user_attributes,
            payload=payload,
        )
        attachment.size = attachment._calculate_size()
        attachment.payload_hash = attachment._calculate_hash()
        return attachment

    # @classmethod
    # def from_bytes(cls, data: bytes):
    #     return decode_attachment(data)
    #
    # def to_bytes(
    #     self,
    # ) -> bytes:
    #     return encode_attachment(self)


@dataclass_json
@dataclass
class MessageContent:
    """The multi-part structure for a single version of a message's content."""

    message_metadata: dict
    message_parts: list[EmbeddedContentPart | ReferencedContentPart]

    def __init__(
        self,
        message_metadata: dict = {},
        message_parts: list[EmbeddedContentPart | ReferencedContentPart] = None,
    ):
        self.message_metadata = message_metadata
        self.message_parts = []
        if message_parts:
            for message_part in message_parts:
                if message_part.part_id:
                    self.message_parts.append(message_part)
            for message_part in message_parts:
                if not message_part.part_id:
                    if isinstance(message_part, ReferencedContentPart):
                        self.add_referenced_part(
                            ref_content_id=message_part.ref_content_id,
                            ref_part_id=message_part.ref_part_id,
                        )
                    elif isinstance(message_part, EmbeddedContentPart):
                        self.add_embedded_part(
                            media_type=message_part.media_type,
                            rendering_metadata=message_part.rendering_metadata,
                            payload=message_part.payload,
                        )
                    elif isinstance(message_part, AttachedContentPart):
                        self.add_attached_part(
                            rendering_metadata=message_part.rendering_metadata,
                            attachment_id=message_part.attachment_id,
                        )
                    else:
                        raise ValueError(
                            f"Unexpected object type in list: {type(message_part)}"
                        )

    def add_embedded_part(
        self, media_type, rendering_metadata, payload
    ) -> EmbeddedContentPart:
        """Create and add and EmbeddedContentPart to this MessageContent."""
        message_part = EmbeddedContentPart(
            part_id=self.get_next_part_id(),
            media_type=media_type,
            rendering_metadata=rendering_metadata,
            payload=payload,
        )
        self.message_parts.append(message_part)
        return message_part

    def add_referenced_part(self, ref_content_id: str, ref_part_id: int):
        """Create and add a ReferencedContentPart to this MessageContent."""
        message_part_reference = ReferencedContentPart(
            part_id=self.get_next_part_id(),
            ref_content_id=ref_content_id,
            ref_part_id=ref_part_id,
        )
        return message_part_reference

    def add_attached_part(
        self,
        rendering_metadata: dict,
        attachment_id: bytes,
    ):
        """Create and add an AttachedContentPart to this MessageContent."""
        message_part_attachment = AttachedContentPart(
            part_id=self.get_next_part_id(),
            rendering_metadata=rendering_metadata,
            attachment_id=attachment_id,
        )
        self.message_parts.append(message_part_attachment)
        return message_part_attachment

    def get_next_part_id(self) -> int:
        """Get the next free part ID for the next content part to be created."""
        return (
            max(
                [
                    mp.part_id
                    for mp in self.message_parts
                    if isinstance(mp, EmbeddedContentPart)
                ]
                + [0]
            )
            + 1
        )

    def get_message_part(self, part_id) -> GenericContentPart:
        for part in self.message_parts:
            if part.part_id == part_id:
                return part
        raise Exception(f"Part {part_id} not found in this message content.")

    # @classmethod
    # def from_bytes(cls, data: bytes):
    #     return decode_message(data)
    #
    # def to_bytes(
    #     self,
    # ) -> bytes:
    #     return encode_message(self)
