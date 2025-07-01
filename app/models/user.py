"""This file contains the user model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)
import uuid
from datetime import datetime

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.boardroom import Boardroom


class User(BaseModel, table=True):
    """User model for storing user accounts.

    Attributes:
        id: The primary key (UUID)
        email: User's email (unique)
        hashed_password: Bcrypt hashed password
        full_name: User's full name (optional)
        is_active: Whether the user account is active
        is_verified: Whether the user's email is verified
        created_at: When the user was created (inherited from BaseModel)
        updated_at: When the user was last updated
        sessions: Relationship to user's chat sessions
        owned_boardrooms: Relationship to boardrooms owned by user
    """

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    updated_at: Optional[datetime] = Field(default=None)
    
    sessions: List["Session"] = Relationship(back_populates="user")
    owned_boardrooms: List["Boardroom"] = Relationship(back_populates="owner")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Avoid circular imports
from app.models.session import Session  # noqa: E402
