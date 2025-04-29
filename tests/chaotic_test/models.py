from dataclasses import dataclass
from dataclasses_json import dataclass_json
class Action:
    device_id:str


class NewProfile(Action):
    profile_did:str
class JoinProfile(Action):
    profile_did:str
class DeleteProfile(Action):
    profile_did:str
class NewProfileInvitation(Action):
    profile_did:str

class NewCorrespondence(Action):
    profile_did:str
    correspondence_did:str
class JoinCorrespondence(Action):
    profile_did:str
    correspondence_did:str
class DeleteCorrespondence(Action):
    profile_did:str
    correspondence_did:str
class NewCorrespondenceInvitation(Action):
    profile_did:str
    correspondence_did:str

    
class NewMessage(Action):
    profile_did:str
    correspondence_did:str
    message_id:str

@dataclass_json
@dataclass
class ExpectationModelMessage:
    content_history:list[str]
    @property
    def current_content(self)->str:
        return self.content_history[-1]
@dataclass_json
@dataclass
class ExpectationModelCorrespondence:
    messages:dict[str|ExpectationModelMessage]
@dataclass_json
@dataclass
class ExpectationModelProfile:
    correspondences:dict[str, ExpectationModelCorrespondence]
@dataclass_json
@dataclass
class ExpectationModelDevice:
    profile_dids:dict[str,ExpectationModelProfile]
    
    
