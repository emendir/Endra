from .models import (ExpectationModelDevice,
ExpectationModelMessage,
ExpectationModelCorrespondence,
ExpectationModelProfile)
from endra_docker import EndraDocker
class SimulationDevice:
    docker_container:EndraDocker
    expectation_model:ExpectationModelDevice
    def __init__(self):
        self.docker_container = EndraDocker()
        self.expectation_model = ExpectationModelDevice()
    @property
    def id(self)->str:
        return self.docker_container.id

    def create_profile(self):
        profile_did = self.docker_container.create_profile()
        self.expectation_model.update({profile_did:ExpectationModelProfile(profile_did)})
