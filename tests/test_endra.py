from datetime import datetime
import walytis_beta_api as waly
import os
import shutil
import tempfile

import _testing_utils
import walytis_identities
import pytest
import walytis_beta_api as walytis_api
from _testing_utils import mark, test_threads_cleanup
from walytis_identities.did_objects import Key
import walytis_mutability
import walytis_offchain
import endra
from endra import Profile, MessageContent, Correspondence
from walytis_identities import GroupDidManager
walytis_api.log.PRINT_DEBUG = False

_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=endra
)


REBUILD_DOCKER = True

# automatically remove all docker containers after failed tests
DELETE_ALL_BRENTHY_DOCKERS = True


def test_preparations():
    pytest.corresp = None
    pytest.profile = None
    pytest.profile_config_dir = tempfile.mkdtemp()
    pytest.key_store_path = os.path.join(
        pytest.profile_config_dir, "keystore.json")

    # the cryptographic family to use for the tests
    pytest.CRYPTO_FAMILY = "EC-secp256k1"
    pytest.KEY = Key(
        family=pytest.CRYPTO_FAMILY,
        public_key=b'\x04\xa6#\x1a\xcf\xa7\xbe\xa8\xbf\xd9\x7fd\xa7\xab\xba\xeb{Wj\xe2\x8fH\x08*J\xda\xebS\x94\x06\xc9\x02\x8c9>\xf45\xd3=Zg\x92M\x84\xb3\xc2\xf2\xf4\xe6\xa8\xf9i\x82\xdb\xd8\x82_\xcaIT\x14\x9cA\xd3\xe1',
        private_key=b'\xd9\xd1\\D\x80\xd7\x1a\xe6E\x0bt\xdf\xd0z\x88\xeaQ\xe8\x04\x91\x11\xaf\\%wC\x83~\x0eGP\xd8',
        creation_time=datetime(2024, 11, 6, 19, 17, 45, 713000)
    )


def test_cleanup():
    if pytest.profile:
        pytest.profile.delete()
    shutil.rmtree(pytest.profile_config_dir)


def test_create_profile():
    pytest.profile = Profile.create(pytest.profile_config_dir, pytest.KEY)
    existing_blockchain_ids = waly.list_blockchain_ids()
    mark(
        pytest.profile.did_manager.blockchain.blockchain_id in existing_blockchain_ids,
        "Created profile."
    )


def test_create_correspondence():
    pytest.profile = pytest.profile
    pytest.corresp = pytest.profile.create_correspondence()
    mark(
        isinstance(pytest.corresp, Correspondence),
        "Created correspondence."
    )
    corresp = pytest.profile.get_correspondence(pytest.corresp.id)
    mark(
        isinstance(corresp, Correspondence) and
        corresp.id == pytest.corresp.id,
        "  -> get_correspondence()"
    )
    mark(
        pytest.corresp.id in pytest.profile.get_active_correspondences()
        and pytest.corresp.id not in pytest.profile.get_archived_correspondences(),
        "  -> get_active_correspondences() & get_archived_correspondences()"
    )


def test_archive_correspondence():
    pytest.profile = pytest.profile
    pytest.profile.archive_correspondence(pytest.corresp.id)
    mark(
        isinstance(pytest.corresp, Correspondence),
        "Created correspondence."
    )
    mark(
        pytest.corresp.id not in pytest.profile.get_active_correspondences()
        and pytest.corresp.id in pytest.profile.get_archived_correspondences(),
        "  -> get_active_correspondences() & get_archived_correspondences()"
    )


def test_create_message():
    message_content = MessageContent(
        "Hello there!", None
    )

    print(message_content.to_json())
    pytest.corresp.add_message(message_content)
    mark(
        pytest.corresp.get_messages()[-1].content.text == message_content.text,
        "Created message."
    )


def test_message_edit():
    message_content = MessageContent(
        "hello there", None
    )
    new_message_content = MessageContent(
        "Hello there!!", None
    )
    pytest.corresp.add_message(message_content)

    pytest.corresp.get_messages()[-1].edit(new_message_content)

    mark(
        pytest.corresp.get_messages()[-1].content.text == new_message_content.text,
        "Edit message: content updates"
    )
    versions = pytest.corresp.get_messages()[-1].get_content_versions()
    mark(
        versions[0].text == message_content.text and
        versions[1].text == new_message_content.text,
        "Edit message: content version history"
    )


def test_delete_profile():
    pytest.profile.delete()
    existing_blockchain_ids = waly.list_blockchain_ids()
    mark(
        pytest.profile.did_manager.blockchain.blockchain_id not in existing_blockchain_ids,
        "Deleted profile."
    )


def run_tests():
    print("\nRunning tests for Endra:")
    test_preparations()
    test_create_profile()
    test_create_correspondence()
    test_create_message()
    test_message_edit()
    test_archive_correspondence()

    test_delete_profile()
    test_cleanup()
    test_threads_cleanup()


if __name__ == "__main__":
    _testing_utils.PYTEST = False
    _testing_utils.BREAKPOINTS = True
    run_tests()
