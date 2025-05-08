from typing import Callable
from walytis_identities.generics import GroupDidManagerWrapper
from walytis_identities.did_manager_blocks import get_info_blocks
from walytis_beta_embedded import Blockchain, join_blockchain, JoinFailureError
from walytis_identities.did_manager import did_from_blockchain_id
from threading import Lock, Event
from walytis_identities.did_manager import blockchain_id_from_did
import os
from walytis_beta_embedded import decode_short_id
from brenthy_tools_beta.utils import bytes_to_string
from walytis_offchain import PrivateBlockchain, DataBlock
from walytis_identities.did_objects import Key
from walytis_identities.did_manager_blocks import InfoBlock
from walytis_identities.group_did_manager import GroupDidManager
from walytis_mutability import MutaBlockchain, MutaBlock
from walytis_identities import DidManager
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import walytis_mutability
import json
from walytis_identities.key_store import KeyStore
from walytis_beta_embedded import Block
from walytis_identities.utils import logger
from walytis_identities import DidManagerWithSupers

WALYTIS_BLOCK_TOPIC = "Endra"


@dataclass_json
@dataclass
class MessageContent:
    text: str | None
    file_data: bytearray | None

    def to_dict(self):
        return {
            "text": self.text,
            "file_data": self.file_data
        }

    def to_bytes(self) -> bytes:
        return str.encode(json.dumps({
            "text": self.text,
            "file_data": bytes_to_string(self.file_data) if self.file_data
            else None
        }))

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> 'MessageContent':
        return cls(**json.loads(data.decode()))

    @classmethod
    def from_dict(cls, data: dict) -> 'MessageContent':
        return cls(**data)

    def __dict__(self):
        return self.to_dict()


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


class CorrespondenceDidManager(GroupDidManagerWrapper):
    def __init__(self, did_manager: GroupDidManager):
        self._org_did_manager = did_manager
        self._did_manager = MutaBlockchain(
            PrivateBlockchain(
                did_manager
            )
        )

    @property
    def did_manager(self):
        return self._did_manager

    @property
    def org_did_manager(self):
        return self._org_did_manager


class Correspondence():
    def __init__(self, did_manager: CorrespondenceDidManager):
        self._did_manager = did_manager

    def add_message(self, message_content: MessageContent):
        self._did_manager.add_block(message_content.to_bytes())

    def get_messages(self):
        return [
            Message.from_block(block)
            for block in self._did_manager.get_blocks()
        ]

    def create_invitation(self) -> dict:
        return self._did_manager.did_manager.base_blockchain.group_blockchain.invite_member()

    @property
    def id(self):
        return self._did_manager.did

    @property
    def block_received_handler(self) -> Callable[[Block], None] | None:
        return self._did_manager.block_received_handler

    @block_received_handler.setter
    def block_received_handler(
        self, block_received_handler: Callable[Block, None]
    ) -> None:
        self._did_manager.block_received_handler = block_received_handler

    def clear_block_received_handler(self) -> None:
        self._did_manager.clear_block_received_handler()


CRYPTO_FAMILY = "EC-secp256k1"


class Device:
    def __init__(self, did_manager_id: str):
        self.id = did_manager_id


class Profile:
    avatar: None
    did_manager: GroupDidManager

    def __init__(
        self,
        did_manager: DidManagerWithSupers,
            auto_run=True,
            on_correspondence_event=None

    ):
        self.did_manager = did_manager
        self.did_manager.block_received_handler = self._on_block_received
        if auto_run:
            self.run()
    def _on_block_received(self, block):
        pass
    def run(self)->None:
        self.did_manager.load_missed_blocks()
    
    @classmethod
    def create(cls, config_dir: str, key: Key, auto_run) -> 'Profile':

        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")

        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        
        
        logger.debug("Endra: creating DM...")
        device_did_manager = DidManager.create(device_did_keystore)
        
        logger.debug("Endra: creating GDM...")
        profile_did_manager = GroupDidManager.create(
            profile_did_keystore, device_did_manager
        )
        logger.debug("Endra: terminating...")
        profile_did_manager.terminate()
        logger.debug("Endra: reloading...")
        group_did_manager = GroupDidManager(
            profile_did_keystore,
            device_did_manager,
            auto_load_missed_blocks=False
        )
        dmws = DidManagerWithSupers(
            did_manager=group_did_manager,
            super_type=CorrespondenceDidManager,
            auto_load_missed_blocks=auto_run
        )
        return cls(
            did_manager=dmws,
            auto_run=auto_run,
        )

    @classmethod
    def load(cls, config_dir: str, key: Key, auto_run=True) -> 'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")

        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        group_did_manager = GroupDidManager(
            profile_did_keystore,
            device_did_keystore,
            auto_load_missed_blocks=False
        )
        dmws = DidManagerWithSupers(
            did_manager=group_did_manager,
            super_type=CorrespondenceDidManager,
            auto_load_missed_blocks=auto_run
        )
        return cls(
            did_manager=dmws,
            auto_run=auto_run,

        )

    def invite(self) -> dict:
        return self.did_manager.did_manager.invite_member()

    @classmethod
    def join(cls,
             invitation: str | dict, config_dir: str, key: Key, auto_run=True
             ) -> 'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")
        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        device_did_manager = DidManager.create(device_did_keystore)
        logger.debug("EndraProtocol: joining profile...")
        profile_did_manager = GroupDidManager.join(
            invitation,
            profile_did_keystore,
            device_did_manager
        )

        logger.debug("EndraProtocol: loading DMWS...")
        dmws = DidManagerWithSupers(
            did_manager=profile_did_manager,
            super_type=CorrespondenceDidManager,
            auto_load_missed_blocks=auto_run
        )
        logger.debug("EndraProtocol: Joined Profile!")
        return cls(
            did_manager=dmws,
            auto_run=auto_run,

        )

    def create_correspondence(self) -> Correspondence:
        return Correspondence(self.did_manager.create_super())

    def join_correspondence(self, invitation: dict) -> Correspondence:
        return Correspondence(self.did_manager.join_super(invitation))

    def archive_correspondence(self, corresp_id: str):
        self.did_manager.archive_super(corresp_id)

    def get_correspondence(self, corresp_id: str) -> Correspondence:
        return Correspondence(self.did_manager.get_super(corresp_id))

    def get_active_correspondences(self) -> set[str]:
        return self.did_manager.get_active_supers()

    def get_archived_correspondences(self):
        return self.did_manager.get_archived_supers()

    def get_devices(self) -> set[str]:
        return set(self.did_manager.did_manager.get_members_dids())

    def get_device(self, device_id: str) -> Device:
        return Device(device_id)

    @property
    def did(self) -> str:
        return self.did_manager.did

    def delete(self):
        self.did_manager.delete()

    def terminate(self):
        self.did_manager.terminate()

    def __del__(self):
        self.terminate()
    
profiles: list[Profile]
