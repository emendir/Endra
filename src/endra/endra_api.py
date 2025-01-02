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
                block_received_handler=self._on_block_received
            ),
            block_received_handler=self._on_block_received
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

    def invite(self) -> dict:
        return self.blockchain.base_blockchain.group_blockchain.invite_member()

    @classmethod
    def join(
        cls, invitation: dict | str,
        group_key_store: KeyStore | str,
        member: DidManager
    ) -> 'Correspondence':
        return cls(GroupDidManager.join(invitation, group_key_store, member))

    def _on_block_received(self, block: Block):
        logger.info(f"Endra-Correspondence: Received block: {block.topics}")

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
        cls, correspondence_id: str, active: bool, invitation: dict | None,
    ) -> 'CorrespondenceRegistration':

        info_content = {
            "correspondence_id": correspondence_id,
            "active": active,
            "invitation": invitation,
        }
        return cls.new(info_content)

    @property
    def correspondence_id(self) -> str:
        return self.info_content["correspondence_id"]

    @property
    def active(self) -> bool:
        return self.info_content["active"]

    @property
    def invitation(self) -> dict | None:
        return self.info_content["invitation"]


class CorrespondenceExistsError(Exception):
    pass


class CorrespondenceManager:
    """Manages a collection of correspondences, managing adding archiving them.
    """

    def __init__(self, profile_did_manager: GroupDidManager):
        self.lock = Lock()
        self.profile_did_manager = profile_did_manager
        self.key_store_dir = os.path.dirname(
            self.profile_did_manager.key_store.key_store_path
        )
        self._terminate = False

        # cached list of archived  Correspondence IDs
        self._archived_corresp_ids: set[str] = set()
        self.correspondences: dict[str, Correspondence] = dict()
        self._load_correspondences()  # load Correspondence objects
        self._process_invitations = False
        self.correspondences_to_join: dict[str,
                                           CorrespondenceRegistration | None] = {}

    def process_invitations(self) -> None:
        # logger.debug(
        #     f"Processing invitations: {len(self.correspondences_to_join)}"
        # )
        _correspondences_to_join: dict[str,
                                       CorrespondenceRegistration | None] = {}
        for correspondence_id in self.correspondences_to_join.keys():
            registration = self.correspondences_to_join[correspondence_id]
            if not registration:
                # logger.info("JAJ: finding blockchain invitation...")

                registrations = get_info_blocks(
                    CorrespondenceRegistration,
                    self.profile_did_manager.blockchain
                )
                invitation: CorrespondenceRegistration | None = None
                for registration in registrations.reverse():
                    if registration.active:
                        if registration.correspondence_id == correspondence_id:
                            invitation = registration.invitation
                if not invitation:
                    error_message = (
                        "BUG: "
                        "In trying to join already joined Correspondence, "
                        "couldn't find a matching CorrespondenceRegistration."

                    )
                    logger.warning(error_message)
                    continue
            correspondence = self.join_already_joined(
                correspondence_id, registration)
            if not correspondence:
                _correspondences_to_join.update(
                    {correspondence_id: correspondence})
        self.correspondences_to_join = _correspondences_to_join

        self._process_invitations = True

    def add(self) -> Correspondence:
        with self.lock:
            if self._terminate:
                raise Exception(
                    "CorrespondenceManager.add: we're shutting down"
                )
            # the GroupDidManager keystore file is located in self.key_store_dir
            # and named according to the created GroupDidManager's blockchain ID
            # and its KeyStore's key is automatically added to
            # self.profile_did_manager.key_store
            correspondence = Correspondence.create(
                self.key_store_dir,
                member=self.profile_did_manager
            )
            invitation = correspondence.invite()
            # register Correspondence on blockchain
            self._register_correspondence(
                correspondence.did, True, invitation
            )

            # add to internal collection of Correspondence objects
            self.correspondences.update({correspondence.did: correspondence})
            return correspondence

    def join_from_invitation(self, invitation: dict | str, register=True) -> Correspondence:
        """
        Args:
            register: whether or not the new correspondence still needs to be
                        registered on our Profile's blockchain
        """
        with self.lock:

            if self._terminate:
                raise Exception(
                    "CorrespondenceManager.add: we're shutting down")

            if isinstance(invitation, str):
                invitation_d = json.loads(invitation)
            else:
                invitation_d = invitation
            corresp_id = did_from_blockchain_id(
                invitation_d["blockchain_invitation"]["blockchain_id"]
            )
            if corresp_id in self.correspondences or corresp_id in self._archived_corresp_ids:
                raise CorrespondenceExistsError()

            # the GroupDidManager keystore file is located in self.key_store_dir
            # and named according to the created GroupDidManager's blockchain ID
            # and its KeyStore's key is automatically added to
            # self.profile_did_manager.key_store
            correspondence = Correspondence.join(
                invitation=invitation_d,
                group_key_store=self.key_store_dir,
                member=self.profile_did_manager
            )

            if register:
                # register Correspondence on blockchain
                self._register_correspondence(
                    correspondence.did, True, invitation_d
                )
            # add to internal collection of Correspondence objects
            self.correspondences.update({correspondence.did: correspondence})

            return correspondence

    def join_already_joined(self, correspondence_id: str, registration: CorrespondenceRegistration) -> Correspondence | None:
        """Join a Coresp. which our Profile has joined but member hasn't."""
        with self.lock:
            # logger.info("JAJ: Joining already joined Correspondence...")
            key_store_path = os.path.join(
                self.key_store_dir,
                blockchain_id_from_did(correspondence_id) + ".json"
            )
            key = Key.create(CRYPTO_FAMILY)
            self.profile_did_manager.key_store.add_key(key)
            key_store = KeyStore(key_store_path, key)

            # logger.info("JAJ: Joining blockchain...")
            blockchain_id = blockchain_id_from_did(correspondence_id)
            DidManager.assign_keystore(key_store, blockchain_id)
            try:
                # join blockchain, preprocessing existing blocks
                blockchain = Blockchain.join(
                    registration.invitation["blockchain_invitation"],
                    appdata_dir=DidManager.get_blockchain_appdata_path(
                        key_store
                    ),
                )
                blockchain.terminate()
            except JoinFailureError:
                return None
            # logger.info("Loading correspondence...")
            correspondence = Correspondence(
                group_did_manager=GroupDidManager(
                    group_key_store=key_store,
                    member=self.profile_did_manager
                )
            )

            self.correspondences.update({correspondence.did: correspondence})
            return correspondence

    def archive(self, correspondence_id: str, register=True):
        with self.lock:
            self.correspondences[correspondence_id].terminate()

            if register:
                # register archiving on blockchain
                self._register_correspondence(correspondence_id, False, None)

            # manage internal lists of Correspondences
            self.correspondences.pop(correspondence_id)
            self._archived_corresp_ids.add(correspondence_id)

    def _register_correspondence(
        self, correspondence_id: str, active: bool, invitation: dict | None
    ):
        """Update a correspondence' registration, activating or archiving it.

        Args:
            correspondence_id: the ID of the correspondence to register
            active: whether the correspondence is being activated or archived 
        """
        correspondence_registration = CorrespondenceRegistration.create(
            correspondence_id,
            active,
            invitation
        )
        correspondence_registration.sign(
            self.profile_did_manager.get_control_key()
        )
        self.profile_did_manager.add_block(
            correspondence_registration.generate_block_content(),
            topics=[WALYTIS_BLOCK_TOPIC,
                    correspondence_registration.walytis_block_topic]
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
            correspondence_bc_id = crsp_registration.correspondence_id

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
        with self.lock:
            correspondences = []

            active_correspondence_ds, _archived_corresp_ids = self._read_correspondence_registry()
            new_correspondences = []
            for correspondence_id in active_correspondence_ds:
                # figure out the filepath of this correspondence' KeyStore
                key_store_path = os.path.join(
                    self.key_store_dir,
                    blockchain_id_from_did(correspondence_id) + ".json"
                )
                if not os.path.exists(key_store_path):
                    new_correspondences.append(correspondence_id)
                    continue
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
                        group_key_store=key_store,
                        member=self.profile_did_manager
                    )
                )
                correspondences.append(correspondence)
            self.correspondences = dict([
                (correspondence.did, correspondence)
                for correspondence in correspondences
            ])
            self._archived_corresp_ids = _archived_corresp_ids

            self.correspondences_to_join = dict([
                (cid, None) for cid in new_correspondences
            ])

    def on_correspondence_registration_received(self, block: Block):
        if self._terminate:
            return
        crsp_registration = CorrespondenceRegistration.load_from_block_content(
            block.content
        )
        # logger.info(f"CorrespondenceManager: got registration for {
        #             crsp_registration.correspondence_id}")

        # update lists of active and archived Correspondences
        try:
            if crsp_registration.active:
                if not self._process_invitations:
                    self.correspondences_to_join.update({
                        crsp_registration.correspondence_id: crsp_registration
                    })
                    # logger.info(
                    #     "CorrespondenceManager: not yet joining Correspondence")
                else:
                    self.join_from_invitation(
                        crsp_registration.invitation, register=False)
                    # logger.info(
                    #     "CorrespondenceManager: added new Correspondence")
            else:
                self.archive(
                    crsp_registration.correspondence_id, register=False)
                # logger.info("CorrespondenceManager: archived Correspondence")
        except CorrespondenceExistsError:
            # logger.info(
            #     "CorrespondenceManager: we already have this Correspondence!")
            pass

    def terminate(self):
        if self._terminate:
            return
        with self.lock:
            self._terminate = True
            for correspondence in self.correspondences.values():
                correspondence.terminate()

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
        self.profile_did_manager.block_received_handler = self._on_block_received

        self.corresp_mngr = CorrespondenceManager(
            profile_did_manager=self.profile_did_manager
        )
        self.profile_did_manager.load_missed_blocks()
        # start joining new correspondeces only after loading missed blocks
        self.corresp_mngr.process_invitations()

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

    @classmethod
    def load(cls, config_dir: str, key: Key) -> 'Profile':
        device_keystore_path = os.path.join(config_dir, "device_keystore.json")
        profile_keystore_path = os.path.join(
            config_dir, "profile_keystore.json")

        device_did_keystore = KeyStore(device_keystore_path, key)
        profile_did_keystore = KeyStore(profile_keystore_path, key)

        profile_did_manager = GroupDidManager(
            group_key_store=profile_did_keystore,
            member=device_did_keystore,
            auto_load_missed_blocks=False
        )
        return cls(
            profile_did_manager=profile_did_manager,
        )

    def invite(self) -> dict:
        return self.profile_did_manager.invite_member()

    @classmethod
    def join(cls,
             invitation: str | dict, config_dir: str, key: Key
             ) -> 'Profile':
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

    def _on_block_received(self, block: Block):
        if WALYTIS_BLOCK_TOPIC == block.topics[0]:
            match block.topics[1]:
                case CorrespondenceRegistration.walytis_block_topic:
                    self.corresp_mngr.on_correspondence_registration_received(
                        block
                    )
                case _:
                    logger.warning(
                        "Endra Profile: Received unhandled block with topics: "
                        f"{block.topics}"
                    )
        else:
            logger.warning(
                "Endra Profile: Received unhandled block with topics: "
                f"{block.topics}"
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
