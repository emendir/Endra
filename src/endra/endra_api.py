from walidentity.did_manager_blocks import get_info_blocks
from walytis_beta_api import Blockchain, join_blockchain, JoinFailureError
from walidentity.did_manager import did_from_blockchain_id
from threading import Lock, Event
from walidentity.did_manager import blockchain_id_from_did
import os
from walytis_beta_api import decode_short_id
from brenthy_tools_beta.utils import bytes_to_string
from private_blocks import PrivateBlockchain, DataBlock
from walidentity.did_objects import Key
from walidentity.did_manager_blocks import InfoBlock
from walidentity.group_did_manager import GroupDidManager
from mutablockchain import MutaBlockchain, MutaBlock
from waly_contacts import ContactsChain
from walidentity import DidManager
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import mutablockchain
import json
from walidentity.key_store import KeyStore
from walytis_beta_api import Block
from walidentity.utils import logger
from walidentity import DidManagerWithSupers

WALYTIS_BLOCK_TOPIC = "Endra"


@dataclass_json
@dataclass
class MessageContent:
    # sender: str    # DID
    # recipient: str  # DID
    text: str | None
    file_data: bytearray | None
    # _base_block_cv: MutaBlock

    # @classmethod
    # def create(cls, text, file_data) -> 'MessageContent':
    #     pass

    # @classmethod
    # def from_mutablock_cv(cls, mutablock_cv: mutablockchain.ContentVersion):
    #     data = json.loads(mutablock_cv.content.decode())
    #     return cls(
    #         _base_block_cv=mutablock_cv,
    #         text=data["text"],
    #         file_data=data["file_data"],
    #     )
    #
    # @property
    # def cv_id(self) -> bytearray:    # same as MutaBlock.cv_id
    #     return self.base_block_cv.cv_id

    def to_dict(self):
        return {
            "text": self.text,
            "file_data": self.file_data
        }

    # @staticmethod
    # def _encode_message_content(text: str, file_data: bytearray) -> bytes:
    #     return str.encode(json.dumps({
    #         "text": text,
    #         "file_data": bytes_to_string(file_data)
    #     }))
    def to_bytes(self) -> bytes:
        return str.encode(json.dumps({
            "text": self.text,
            "file_data": bytes_to_string(self.file_data) if self.file_data
            else None
        }))

    def __dict__(self):
        return self.to_dict()


class Correspondence():
    def __init__(self, did_manager: GroupDidManager):
        self._did_manager = did_manager

    def add_message(self, message: MessageContent):
        pass

    @property
    def id(self):
        return self._did_manager.did


@dataclass
class Message:
    block: MutaBlock

    @classmethod
    def create(
        cls,
        correspondence: GroupDidManager,
        message_content: MessageContent,
    ) -> 'Message':
        block = correspondence.blockchain.add_block(message_content.to_bytes())
        return cls(
            block,
        )

    def edit(self, message_content: MessageContent) -> None:
        self.block.edit(message_content.to_bytes())

    def delete(self) -> None:
        self.block.delete()

    def get_content_versions(self) -> list[MessageContent]:
        return [
            MessageContent.from_mutablock_cv(cv)
            for cv in self.block.get_content_versions()
        ]

    def get_author_did(self):
        # TODO: get the author DID from the WalytisAuth block metadata
        pass

    def get_recipient_did(self):
        # TODO: get the recipient's DID from the block's GroupDidManager blockchain
        pass


CRYPTO_FAMILY = "EC-secp256k1"


class Profile:
    avatar: None
    did_manager: GroupDidManager

    def __init__(
        self,
        did_manager: DidManagerWithSupers,
    ):

        self.did_manager = did_manager

    @classmethod
    def create(cls, config_dir: str, key: Key) -> 'Profile':
        return cls(
            did_manager=DidManagerWithSupers.create(
                config_dir=config_dir,
                key=key,
            ),
        )

    @classmethod
    def load(cls, config_dir: str, key: Key) -> 'Profile':
        return cls(
            did_manager=DidManagerWithSupers.load(
                config_dir=config_dir,
                key=key,
            ),
        )

    def invite(self) -> dict:
        return self.did_manager.invite_member()

    @classmethod
    def join(cls,
             invitation: str | dict, config_dir: str, key: Key
             ) -> 'Profile':
        return cls(
            did_manager=DidManagerWithSupers.load(
                invitation=invitation,
                config_dir=config_dir,
                key=key,
            ),
        )

    def create_correspondence(self) -> Correspondence:
        return Correspondence(self.did_manager.create_super())

    def archive_correspondence(self, corresp_id: str):
        self.did_manager.archive_super(corresp_id)

    def get_correspondence(self, corresp_id: str) -> Correspondence:
        return Correspondence(self.did_manager.get_super(corresp_id))

    def get_active_correspondences(self):
        return self.did_manager.get_active_supers()

    def get_archived_correspondences(self):
        return self.did_manager.get_archived_supers()

    def delete(self):
        self.did_manager.delete()

    def terminate(self):
        self.did_manager.terminate()

    def __del__(self):
        self.terminate()


profiles: list[Profile]
