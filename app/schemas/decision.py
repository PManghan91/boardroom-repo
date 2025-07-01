import uuid
import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

class DecisionBase(BaseModel):
    title: str = Field(..., max_length=200, description="Decision title")
    description: str = Field(..., max_length=2000, description="Decision description")
    status: str = Field("pending", description="Decision status")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and sanitize title."""
        # Remove HTML tags and dangerous content
        v = re.sub(r"<.*?>", "", v)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
            
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate and sanitize description."""
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            raise ValueError("Description cannot be empty")
            
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        allowed_statuses = ["pending", "active", "completed", "cancelled"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

class DecisionCreate(DecisionBase):
    pass

class DecisionRead(DecisionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DecisionRoundBase(BaseModel):
    decision_id: uuid.UUID
    round_number: int = Field(..., ge=1, le=100, description="Round number (1-100)")
    question: str = Field(..., max_length=500, description="Round question")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and sanitize question."""
        # Remove HTML tags and dangerous content
        v = re.sub(r"<.*?>", "", v)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            raise ValueError("Question cannot be empty")
            
        return v.strip()

class DecisionRoundCreate(DecisionRoundBase):
    pass

class DecisionRoundRead(DecisionRoundBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class VoteBase(BaseModel):
    round_id: uuid.UUID
    voter_id: str = Field(..., max_length=100, description="Voter identifier")
    vote: str = Field(..., max_length=50, description="Vote value")
    reasoning: Optional[str] = Field(None, max_length=1000, description="Vote reasoning")

    @field_validator("voter_id")
    @classmethod
    def validate_voter_id(cls, v: str) -> str:
        """Validate voter ID format."""
        # Allow alphanumeric, hyphens, underscores
        if not re.match(r"^[a-zA-Z0-9_-]{1,100}$", v):
            raise ValueError("Voter ID must be alphanumeric with underscores/hyphens, max 100 characters")
        return v

    @field_validator("vote")
    @classmethod
    def validate_vote(cls, v: str) -> str:
        """Validate vote format."""
        # Remove dangerous content
        v = re.sub(r"<.*?>", "", v)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            raise ValueError("Vote cannot be empty")
            
        return v.strip()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize reasoning."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()

class VoteCreate(VoteBase):
    pass

class VoteRead(VoteBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True