from ..message_content import (
    MessageAttachment,
)
from .message_encoding_utils import (
    dict_to_struct,
    struct_to_dict,
)
from .message_v1_pb2 import (
    MessageAttachment as PbMessageAttachment,
)

CODEC_VERSION = 1
CODEC_OBJ_TYPE = MessageAttachment


def encode(att: CODEC_OBJ_TYPE) -> bytes:
    pb_msg = PbMessageAttachment()
    pb_msg.media_type = att.media_type
    pb_msg.payload_hash = att.payload_hash
    pb_msg.size = att.size
    pb_msg.payload = att.payload
    pb_msg.derived_properties.CopyFrom(dict_to_struct(att.derived_properties))
    pb_msg.user_attributes.CopyFrom(dict_to_struct(att.user_attributes))

    return pb_msg.SerializeToString()


def decode(data: bytes) -> CODEC_OBJ_TYPE:
    pb_msg = PbMessageAttachment()
    pb_msg.ParseFromString(data)
    media_type = pb_msg.media_type
    payload_hash = pb_msg.payload_hash
    size = pb_msg.size
    payload = pb_msg.payload
    derived_properties = struct_to_dict(pb_msg.derived_properties)
    user_attributes = struct_to_dict(pb_msg.user_attributes)

    return MessageAttachment(
        media_type=media_type,
        payload_hash=payload_hash,
        size=size,
        payload=payload,
        derived_properties=derived_properties,
        user_attributes=user_attributes,
    )
