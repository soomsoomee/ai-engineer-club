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
