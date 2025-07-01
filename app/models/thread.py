"""This file contains the thread model for the application."""

from typing import (
    TYPE_CHECKING,
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
    from app.models.session import Session
    from app.models.user import User


class Thread(BaseModel, table=True):
    """Thread model for storing conversation threads.

    Attributes:
        id: The primary key (UUID)
        session_id: Foreign key to the session
        user_id: Foreign key to the user who created the thread
        title: Title of the thread
        content: Content of the thread
        thread_type: Type of thread (discussion, decision, action_item, note)
        status: Status of the thread (active, closed, archived)
        priority: Priority level (1-5)
        created_at: When the thread was created (inherited from BaseModel)
        updated_at: When the thread was last updated
        session: Relationship to the session
        user: Relationship to the user who created the thread
    """

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=255)
    content: Optional[str] = Field(default=None)
    thread_type: str = Field(default="discussion", max_length=50)
    status: str = Field(default="active", max_length=50)
    priority: int = Field(default=1)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    session: "Session" = Relationship(back_populates="threads")
    user: "User" = Relationship()
