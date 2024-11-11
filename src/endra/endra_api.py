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


@dataclass
class Message:
    block: MutaBlock

    @classmethod
    def create(
        cls,
        correspondence: 'Correspondence',
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


class Correspondence:
    blockchain: MutaBlockchain

    def __init__(self, group_did_manager: GroupDidManager):
        self.blockchain = MutaBlockchain(
            PrivateBlockchain(
                group_did_manager,
                virtual_layer_name="PrivateBlockchain",
            )
        )

    @classmethod
    def create(
        cls, group_key_store: KeyStore, member: DidManager
    ) -> 'Correspondence':

        return cls(GroupDidManager.create(group_key_store, member))

    def get_messages(self) -> list[Message]:
        return [Message(block) for block in self.blockchain]

    def add_message(self, message_content: MessageContent) -> Message:
        return Message.create(self, message_content)

    def delete(self):
        self.blockchain.delete()

    def terminate(self):
        self.blockchain.terminate()

    def __del__(self):
        self.blockchain.terminate()
    @property
    def did(self):
        return self.blockchain.base_blockchain.group_blockchain.did


@dataclass
class CorrespondenceRegistration(InfoBlock):
    """Block in a Profile's blockchain registering a Correspondence."""
    walytis_block_topic = "endra_corresp_reg"
    info_content: dict

    @classmethod
    def create(
        cls, correspondence_id: str, active: bool
    ) -> 'CorrespondenceRegistration':
        info_content = {
            "correspondence_blockchain": correspondence_id,
            "active": active
        }
        return cls.new(info_content)

    @property
    def correspondence_blockchain(self):
        return self.info_content["correspondence_blockchain"]

    @property
    def active(self):
        return self.info_content["active"]

class CorrespondenceManager:
    def __init__(self,profile_did_manager:GroupDidManager):
        self.profile_did_manager=profile_did_manager
    def add(self) -> Correspondence:
        key_store_dir = os.path.dirname(
            self.profile_did_manager.key_store.key_store_path
        )
        correspondence = Correspondence.create(
            key_store_dir, member=self.profile_did_manager
        )
        self._register_correspondence(
            correspondence.did, True
        )
        return correspondence

    def archive(self, correspondence_id: str):
        self._register_correspondence(correspondence_id, False)

    def _register_correspondence(self, correspondence_id: str, active: bool):
        """Update a correspondence' registration, activating or archiving it.

        Args:
            correspondence_id: the ID of the correspondence to register
            active: whether the correspondence is being activated or archived 
        """
        correspondence_registration = CorrespondenceRegistration.create(
            correspondence_id,
            active
        )
        correspondence_registration.sign(
            self.profile_did_manager.get_control_key()
        )

        self.profile_did_manager.blockchain.add_block(
            correspondence_registration.generate_block_content(),
            topics=correspondence_registration.walytis_block_topic
        )

    def get_ids(self) -> set[str]:
        correspondence_ids = set()
        for block in self.profile_did_manager.blockchain.get_blocks():
            if (CorrespondenceRegistration.walytis_block_topic
                not in block.topics
                ):
                continue
            block = self.profile_did_manager.blockchain.get_block(block.long_id)
            crsp_registration = CorrespondenceRegistration.load_from_block_content(
                block.content
            )
            correspondence_bc_id = crsp_registration.correspondence_blockchain
            if crsp_registration.active:
                correspondence_ids.add(correspondence_bc_id)
            elif correspondence_bc_id in correspondence_ids:
                correspondence_ids.remove(correspondence_bc_id)
        return correspondence_ids
    def terminate(self):
        pass
    def delete(self):
        pass
CRYPTO_FAMILY = "EC-secp256k1"


class Profile:
    avatar: None
    profile_did_manager: GroupDidManager

    def __init__(
        self,
        profile_did_manager: GroupDidManager,
    ):
        self.profile_did_manager = profile_did_manager
        self.correspondences = CorrespondenceManager(
            profile_did_manager=self.profile_did_manager
        )

    @classmethod
    def create(cls, config_dir: str, key: Key) -> 'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")

        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        device_did_manager = DidManager.create(device_did_keystore)
        profile_did_manager = GroupDidManager.create(
            profile_did_keystore, device_did_manager
        )
        
        return cls(
            profile_did_manager=profile_did_manager,
        )

    def delete(self):
        self.profile_did_manager.delete()
        self.correspondences.delete()
    def terminate(self):
        self.profile_did_manager.terminate()
        self.correspondences.terminate()

    def __del__(self):
        self.terminate()


profiles: list[Profile]
