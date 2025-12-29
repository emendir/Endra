from ..message_content import (
    MessageContent,
    EmbeddedContentPart,
    ReferencedContentPart,
    AttachedContentPart,
)
from .message_encoding_utils import (
    dict_to_struct,
    struct_to_dict,
)
from .message_v1_pb2 import (
    MessageContent as PbMessage,
)

CODEC_VERSION = 1
CODEC_OBJ_TYPE = MessageContent


def encode(msg: CODEC_OBJ_TYPE) -> bytes:
    pb_msg = PbMessage()
    pb_msg.message_metadata.CopyFrom(dict_to_struct(msg.message_metadata))

    for part in msg.message_parts:
        entry = pb_msg.message_parts.add()
        if isinstance(part, EmbeddedContentPart):
            entry.part_data.part_id = part.part_id
            entry.part_data.media_type = part.media_type
            entry.part_data.rendering_metadata.CopyFrom(
                dict_to_struct(part.rendering_metadata)
            )
            entry.part_data.payload = part.payload
        elif isinstance(part, ReferencedContentPart):
            entry.part_ref.part_id = part.part_id
            entry.part_ref.ref_content_id = part.ref_content_id
            entry.part_ref.ref_part_id = part.ref_part_id
        elif isinstance(part, AttachedContentPart):
            entry.part_attach.part_id = part.part_id
            entry.part_attach.rendering_metadata.CopyFrom(
                dict_to_struct(part.rendering_metadata)
            )
            entry.part_attach.attachment_id = part.attachment_id
        else:
            raise TypeError(f"Unknown part type: {type(part)}")
    return pb_msg.SerializeToString()


# Decode protobuf MessageContent to Python MessageContent object


def decode(data: bytes) -> CODEC_OBJ_TYPE:
    pb_msg = PbMessage()
    pb_msg.ParseFromString(data)
    parts = []
    for entry in pb_msg.message_parts:
        if entry.HasField("part_data"):
            part_data = entry.part_data
            parts.append(
                EmbeddedContentPart(
                    part_id=part_data.part_id,
                    media_type=part_data.media_type,
                    rendering_metadata=struct_to_dict(part_data.rendering_metadata),
                    payload=part_data.payload,
                )
            )
        elif entry.HasField("part_ref"):
            part_ref = entry.part_ref
            parts.append(
                ReferencedContentPart(
                    part_id=part_ref.part_id,
                    ref_content_id=part_ref.ref_content_id,
                    ref_part_id=part_ref.ref_part_id,
                )
            )
        elif entry.HasField("part_attach"):
            part_attach = entry.part_attach
            parts.append(
                AttachedContentPart(
                    part_id=part_attach.part_id,
                    rendering_metadata=part_attach.rendering_metadata,
                    attachment_id=part_attach.attachment_id,
                )
            )
    return MessageContent(
        message_metadata=struct_to_dict(pb_msg.message_metadata), message_parts=parts
    )
