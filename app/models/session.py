"""This file contains the session model for the application."""

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
    from app.models.boardroom import Boardroom
    from app.models.thread import Thread


class Session(BaseModel, table=True):
    """Session model for storing chat sessions.

    Attributes:
        id: The primary key (UUID)
        boardroom_id: Foreign key to the boardroom
        user_id: Foreign key to the user
        title: Title of the session
        description: Description of the session
        status: Status of the session
        started_at: When the session started
        ended_at: When the session ended
        created_at: When the session was created (inherited from BaseModel)
        updated_at: When the session was last updated
        boardroom: Relationship to the boardroom
        user: Relationship to the session owner
        threads: Relationship to session threads
    """

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    boardroom_id: str = Field(foreign_key="boardroom.id", index=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    status: str = Field(default="active", max_length=50)
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    boardroom: "Boardroom" = Relationship(back_populates="sessions")
    user: "User" = Relationship(back_populates="sessions")
    threads: List["Thread"] = Relationship(back_populates="session")
