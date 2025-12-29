from walytis_mutability import MutaBlock
from dataclasses import dataclass
from .message_content import MessageContent

BLOCK_TOPIC_MESSAGES = "EndraMessage"
BLOCK_TOPIC_ATTACHMENTS = "EndraAttachments"


@dataclass
class Message:
    block: MutaBlock

    @classmethod
    def from_block(cls, block: MutaBlock):
        return cls(block)

    @property
    def content(self):
        if self.block.content is None:
            breakpoint()
        return MessageContent.from_bytes(self.block.content)

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
