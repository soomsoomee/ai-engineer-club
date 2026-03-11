from typing import TypedDict
from pydantic import BaseModel
from typing import Optional

class UserAccountContext(BaseModel):

    name: str


class HandoffData(BaseModel):

    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str


class InputGuardRailOutput(BaseModel):

    is_off_topic: bool
    is_inappropriate: bool
    reason: str


class OutputGuardRailOutput(BaseModel):

    is_proffesional: bool
    is_polite: bool
    is_private_information: bool
    reason: str
