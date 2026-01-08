from .message_encoding import decode_attachment
from .message_content import (
    EmbeddedContentPart,
    ReferencedContentPart,
    AttachedContentPart,
)
from walytis_mutability import MutaBlock
from dataclasses import dataclass
from .message_content import MessageContent
from .message_encoding import decode_message

BLOCK_TOPIC_MESSAGES = "EndraMessage"
BLOCK_TOPIC_ATTACHMENTS = "EndraAttachments"


@dataclass
class Message:
    block: MutaBlock

    def __post_init__(self):
        self._content = None

    @classmethod
    def from_block(cls, block: MutaBlock):
        return cls(block)

    @property
    def content(self) -> MessageContent:
        if not self._content:
            self._content = decode_message(self.block.content)
        return self._content

    def edit(self, message_content: MessageContent) -> None:
        self.block.edit(message_content.to_bytes())

    def delete(self) -> None:
        self.block.delete()

    def get_content_versions(self) -> list[MessageContent]:
        return [
            MessageContent.from_bytes(cv.content)
            for cv in self.block.get_content_versions()
        ]

    def get_author_did(self):
        # TODO: get the author DID from the WalytisAuth block metadata
        pass

    def get_recipient_did(self):
        # TODO: get the recipient's DID from the block's GroupDidManager blockchain
        pass


def get_message_content_parts(
    blockchain, message_content: MessageContent
) -> list[EmbeddedContentPart]:
    content_parts = []
    for content_part in message_content.message_parts:
        if isinstance(content_part, EmbeddedContentPart):
            content_parts.append(content_part)
        elif isinstance(content_part, AttachedContentPart):
            attachment = decode_attachment(
                blockchain.get_block(content_part.attachment_id).content
            )
            content_parts.append(attachment)
        elif isinstance(content_part, ReferencedContentPart):
            block = blockchain.get_block(content_part.ref_content_id)
            ref_content = decode_message(block.content)
            ref_content_part = ref_content.get_message_part(content_part.ref_part_id)
            if not isinstance(ref_content_part, EmbeddedContentPart):
                raise Exception(
                    "The referenced content part is not an "
                    f"EmbeddedContentPart, but a {type(ref_content_part)}"
                )
            content_parts.append(ref_content_part)
    return content_parts
