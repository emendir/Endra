from time import sleep
from termcolor import colored as coloured
from brenthy_tools_beta.utils import function_name
from datetime import datetime
import walytis_beta_api as waly
import os
import shutil
import tempfile
from walidentity.utils import logger, LOG_PATH
import json

import _testing_utils
import walidentity
import pytest
import walytis_beta_api as walytis_api
from _testing_utils import mark, test_threads_cleanup
from walidentity.did_objects import Key
import mutablockchain
import private_blocks
import endra
from endra import Profile, MessageContent, Correspondence
from endra_docker.endra_docker import (
    EndraDocker,
    delete_containers,
)
from endra_docker.build_docker import build_docker_image


walytis_api.log.PRINT_DEBUG = False

_testing_utils.assert_is_loaded_from_source(
    source_dir=os.path.dirname(os.path.dirname(__file__)), module=endra
)
REBUILD_DOCKER = True

# automatically remove all docker containers after failed tests
DELETE_ALL_BRENTHY_DOCKERS = True

CONTAINER_NAME_PREFIX = "endra_tests_devices_"

# Boilerplate python code when for running python tests in a docker container
DOCKER_PYTHON_LOAD_TESTING_CODE = '''
import sys
import threading
import json
from time import sleep
sys.path.append('/opt/Endra/tests')
import test_multi_dev
import pytest
from test_multi_dev import logger
logger.info('DOCKER: Preparing tests...')
test_multi_dev.REBUILD_DOCKER=False
test_multi_dev.DELETE_ALL_BRENTHY_DOCKERS=False
test_multi_dev.test_preparations()
logger.info('DOCKER: Ready to test!')
'''
DOCKER_PYTHON_FINISH_TESTING_CODE = '''
'''

N_DOCKER_CONTAINERS = 2

pytest.corresp = None
pytest.profile = None
pytest.profile_config_dir = "/tmp/endra_test_multi_dev"
pytest.containers: list[EndraDocker] = []


def test_preparations():
    if DELETE_ALL_BRENTHY_DOCKERS:
        delete_containers(container_name_substr=CONTAINER_NAME_PREFIX,
                          image="local/walytis_auth_testing")

    if REBUILD_DOCKER:

        build_docker_image(verbose=False)

    if not os.path.exists(pytest.profile_config_dir):
        os.makedirs(pytest.profile_config_dir)

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


def test_create_docker_containers():
    for i in range(N_DOCKER_CONTAINERS):
        pytest.containers.append(
            EndraDocker(container_name=f"{CONTAINER_NAME_PREFIX}{i}")
        )


def test_cleanup():
    if os.path.exists(pytest.profile_config_dir):
        shutil.rmtree(pytest.profile_config_dir)
    for container in pytest.containers:
        container.delete()
    pytest.containers = []
    if pytest.corresp:
        pytest.corresp.delete()
    if pytest.profile:
        pytest.profile.delete()


def docker_create_profile():
    logger.info("DOCKER: Creating Profile...")
    pytest.profile = Profile.create(pytest.profile_config_dir, pytest.KEY)


def docker_load_profile():
    pytest.profile = Profile.load(pytest.profile_config_dir, pytest.KEY)


def test_setup_profile(docker_container:EndraDocker):
    """In a docker container, create an Endra profile."""
    print(coloured(f"\n\nRunning {function_name()}", "blue"))

    python_code = "\n".join([
        DOCKER_PYTHON_LOAD_TESTING_CODE,
        "test_multi_dev.docker_create_profile()",
        "print(f'DOCKER: Created Profile: {type(pytest.profile)}')",
        "pytest.profile.terminate()",
    ])
    print(
        f"docker exec -it {docker_container.docker_id} /bin/tail -f {LOG_PATH}")
    output_lines = docker_container.run_python_code(
        python_code, print_output=False, timeout=60, background=False
    ).split("\n")
    last_line = output_lines[-1] if len(output_lines) > 0 else None
    mark(
        last_line == "DOCKER: Created Profile: <class 'endra.endra_api.Profile'>",
        function_name()
    )


def test_load_profile(docker_container: EndraDocker) -> dict | None:
    """In a docker container, load an Endra profile & create an invitation.

    The docker container must already have had the Endra profile set up.

    Args:
        docker_container: the docker container in which to load the profile
    Returns:
        dict: an invitation to allow another device to join the profile
    """
    print(coloured(f"\n\nRunning {function_name()}", "blue"))
    python_code = "\n".join([
        DOCKER_PYTHON_LOAD_TESTING_CODE,
        "test_multi_dev.docker_load_profile()",
        "invitation=pytest.profile.invite()",
        "print(json.dumps(invitation))",
        "print(f'DOCKER: Loaded Profile: {type(pytest.profile)}')",
        "pytest.profile.terminate()",
    ])

    output_lines = docker_container.run_python_code(
        python_code, print_output=False, timeout=60, background=False
    ).split("\n")
    if len(output_lines) < 2:
        mark(
            False,
            function_name()
        )
        return None
    last_line = output_lines[-1].strip()
    invitation = json.loads(output_lines[-2].strip().replace("'", '"'))
    mark(
        last_line == "DOCKER: Loaded Profile: <class 'endra.endra_api.Profile'>",
        function_name()
    )

    return invitation


def docker_join_profile(invitation: str):
    logger.info("Joining Endra profile...")
    pytest.profile = Profile.join(
        invitation, pytest.profile_config_dir, pytest.KEY
    )
    logger.info("Joined Endra profile, waiting to get control key...")

    sleep(10)
    ctrl_key = pytest.profile.profile_did_manager.get_control_key()
    logger.info(f"Joined: {type(ctrl_key)}")
    if ctrl_key.private_key:
        print("Got control key!")


def test_add_device(
    docker_container_new: EndraDocker,
    docker_container_old: EndraDocker,
    invitation: dict
) -> None:
    """
    Join an existing Endra profile on a new docker container.
    
    Args:
        docker_container_new: the container on which to set up Endra, joining
            the existing Endra profile
        docker_container_old; the container on which the Endra profile is
            already set up
        invitation: the invitation that allows the new docker container to join
            the Endra profile
    """
    print(coloured(f"\n\nRunning {function_name()}", "blue"))

    python_code = "\n".join([
        DOCKER_PYTHON_LOAD_TESTING_CODE,
        "test_multi_dev.docker_load_profile()",
        "logger.info('Waiting to allow new device to join...')",
        "sleep(30)",
        "logger.info('Finished waiting, terminating...')",
        "pytest.profile.terminate()",
        "logger.info('Exiting after waiting.')",
        
    ])
    docker_container_old.run_python_code(
        python_code, print_output=False, background=True
    )
    python_code = "\n".join([
        DOCKER_PYTHON_LOAD_TESTING_CODE,
        f"test_multi_dev.docker_join_profile('{
            json.dumps(invitation)}')",
        "pytest.profile.terminate()",
    ])
    print("Joining...")
    output_lines = docker_container_new.run_python_code(
        python_code, timeout=40, print_output=False, background=False
    ).split("\n")
    last_line = output_lines[-1].strip()
    last_line
    mark(
        last_line == "Got control key!",
        function_name()
    )


def test_create_conversation():
    print(coloured(f"\n\nRunning {function_name()}", "blue"))


def test_conv_add_third_partner():
    print(coloured(f"\n\nRunning {function_name()}", "blue"))


def run_tests():
    print("\nRunning tests for Endra:")
    test_cleanup()
    test_preparations()
    test_create_docker_containers()

    # create first profile with multiple devices
    test_setup_profile(pytest.containers[0])
    invitation = test_load_profile(pytest.containers[0])
    test_add_device(pytest.containers[1], pytest.containers[0], invitation)

    # create second profile with multiple devices
    test_cleanup()
    test_threads_cleanup()


if __name__ == "__main__":
    _testing_utils.PYTEST = False
    _testing_utils.BREAKPOINTS = True
    run_tests()
