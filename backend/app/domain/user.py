from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    ADVISOR = "advisor"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"


class CurrentUser(BaseModel):
    user_id: str
    display_name: str
    role: Role


class StoredUser(BaseModel):
    username: str
    display_name: str
    role: Role
    password_hash: str

    def to_current_user(self) -> CurrentUser:
        return CurrentUser(user_id=self.username, display_name=self.display_name, role=self.role)
