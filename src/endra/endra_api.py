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
        cls, group_key_store: KeyStore | str, member: DidManager
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
    """Manages a collection of correspondences, managing adding archiving them.


    """

    def __init__(self, profile_did_manager: GroupDidManager):
        self.profile_did_manager = profile_did_manager
        self.key_store_dir = os.path.dirname(
            self.profile_did_manager.key_store.key_store_path
        )

        # cached list of archived  Correspondence IDs
        self._archived_corresp_ids: set[str] = set()
        self.correspondences: dict[str, Correspondence] = dict()
        self._load_correspondences()  # load Correspondence objects

    def add(self) -> Correspondence:
        # the GroupDidManager keystore file is located in self.key_store_dir
        # and named according to the created GroupDidManager's blockchain ID
        # and its KeyStore's key is automatically added to
        # self.profile_did_manager.key_store
        correspondence = Correspondence.create(
            self.key_store_dir, member=self.profile_did_manager
        )

        # register Correspondence on blockchain
        self._register_correspondence(
            correspondence.did, True
        )

        # add to internal collection of Correspondence objects
        self.correspondences.update({correspondence.did: correspondence})
        return correspondence

    def archive(self, correspondence_id: str):
        self.correspondences[correspondence_id].terminate()

        # register archiving on blockchain
        self._register_correspondence(correspondence_id, False)

        # manage internal lists of Correspondences
        self.correspondences.pop(correspondence_id)
        self._archived_corresp_ids.add(correspondence_id)

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

    def _read_correspondence_registry(self) -> tuple[set[str], set[str]]:
        """Get lists of active and archived Correspondences.

        Reads the profile_did_manager blockchain to get this information.

        Returns:
            tuple[set[str], set[str]]: list of active and list of archived
                                        Correspondence IDs
        """
        active_correspondences: set[str] = set()
        archived_correspondences: set[str] = set()
        for block in self.profile_did_manager.blockchain.get_blocks():
            # ignore blocks that aren't CorrespondenceRegistration
            if (
                CorrespondenceRegistration.walytis_block_topic
                not in block.topics
            ):
                continue

            # load CorrespondenceRegistration
            crsp_registration = CorrespondenceRegistration.load_from_block_content(
                self.profile_did_manager.blockchain.get_block(
                    block.long_id
                ).content
            )
            correspondence_bc_id = crsp_registration.correspondence_blockchain

            # update lists of active and archived Correspondences
            if crsp_registration.active:
                active_correspondences.add(correspondence_bc_id)
                if correspondence_bc_id in archived_correspondences:
                    archived_correspondences.remove(correspondence_bc_id)
            else:
                archived_correspondences.add(correspondence_bc_id)
                if correspondence_bc_id in active_correspondences:
                    active_correspondences.remove(correspondence_bc_id)

        return active_correspondences, archived_correspondences

    def get_active_ids(self) -> set[str]:
        return set(self.correspondences.keys())

    def get_archived_ids(self) -> set[str]:
        return self._archived_corresp_ids

    def get_from_id(self, corresp_id: str) -> Correspondence:
        return self.correspondences[corresp_id]

    def _load_correspondences(self) -> None:
        correspondences = []

        active_correspondence_ds, _archived_corresp_ids = self._read_correspondence_registry()
        for correspondence_id in active_correspondence_ds:
            # figure out the filepath of this correspondence' KeyStore
            key_store_path = os.path.join(
                self.key_store_dir,
                blockchain_id_from_did(correspondence_id) + ".json"
            )
            # get this correspondence' KeyStore Key ID
            keystore_key_id = KeyStore.get_keystore_pubkey(key_store_path)
            # get the Key from self.profile_did_manager's KeyStore
            key_store_key = self.profile_did_manager.key_store.get_key(
                keystore_key_id
            )
            # load the correspondence' KeyStore
            key_store = KeyStore(key_store_path, key_store_key)
            correspondence = Correspondence(
                group_did_manager=GroupDidManager(
                    key_store,
                    self.profile_did_manager
                )
            )
            correspondences.append(correspondence)
        self.correspondences = dict([
            (correspondence.did, correspondence)
            for correspondence in correspondences
        ])
        self._archived_corresp_ids = _archived_corresp_ids

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
        self.corresp_mngr = CorrespondenceManager(
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
        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)

        return cls(
            profile_did_manager=profile_did_manager,
        )
    @classmethod
    def load(cls, config_dir:str, key:Key)-> 'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(config_dir, "profile_keystore.json")
        
        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        
        profile_did_manager = GroupDidManager(
            profile_did_keystore, device_did_keystore
        )
        return cls(
            profile_did_manager=profile_did_manager,
        )
    
    def invite(self)->dict:
        return self.profile_did_manager.invite_member()
    @classmethod
    def join(cls, 
        invitation: str | dict, config_dir:str, key:Key
    )->'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")
        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)
        device_did_manager = DidManager.create(device_did_keystore)
        
        profile_did_manager = GroupDidManager.join(
            invitation,
            profile_did_keystore,
            device_did_manager
        )
        return cls(
            profile_did_manager=profile_did_manager,
        )
    def delete(self):
        self.profile_did_manager.delete()
        self.corresp_mngr.delete()

    def terminate(self):
        self.profile_did_manager.terminate()
        self.corresp_mngr.terminate()

    def __del__(self):
        self.terminate()


profiles: list[Profile]
