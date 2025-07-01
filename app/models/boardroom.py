"""Boardroom model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)
import uuid
from datetime import datetime

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.session import Session


class Boardroom(BaseModel, table=True):
    """Boardroom model for storing meeting spaces.

    Attributes:
        id: The primary key (UUID)
        name: Name of the boardroom
        description: Description of the boardroom
        owner_id: Foreign key to the owner user
        is_active: Whether the boardroom is active
        max_participants: Maximum number of participants
        created_at: When the boardroom was created (inherited from BaseModel)
        updated_at: When the boardroom was last updated
        owner: Relationship to the owner user
        sessions: Relationship to boardroom sessions
    """

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(max_length=255, index=True)
    description: Optional[str] = Field(default=None)
    owner_id: str = Field(foreign_key="user.id", index=True)
    is_active: bool = Field(default=True)
    max_participants: Optional[int] = Field(default=10)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    owner: "User" = Relationship(back_populates="owned_boardrooms")
    sessions: List["Session"] = Relationship(back_populates="boardroom")