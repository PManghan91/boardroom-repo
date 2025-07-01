import uuid
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# Base Schemas for DB models (for reading/returning from API)
class Vote(BaseModel):
    id: uuid.UUID
    decision_round_id: uuid.UUID
    voter_ip: str = Field(..., description="Voter IP address")
    selected_option_key: str = Field(..., description="Selected option key")
    voted_at: datetime
    rationale: Optional[str] = Field(None, max_length=1000, description="Vote reasoning")

    class Config:
        from_attributes = True

    @field_validator("voter_ip")
    @classmethod
    def validate_voter_ip(cls, v: str) -> str:
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")

    @field_validator("selected_option_key")
    @classmethod
    def validate_option_key(cls, v: str) -> str:
        """Validate option key format."""
        if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", v):
            raise ValueError("Option key must be alphanumeric with underscores/hyphens, max 50 characters")
        return v

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize rationale."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v


class DecisionRound(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    round_number: int = Field(..., ge=1, le=100, description="Round number (1-100)")
    title: Optional[str] = Field(None, max_length=200, description="Round title")
    description: Optional[str] = Field(None, max_length=2000, description="Round description")
    options: Dict[str, Any] = Field(..., description="Voting options as JSON")
    opens_at: datetime
    closes_at: Optional[datetime] = None
    round_status: str = Field(..., description="Round status")
    created_at: datetime
    votes: List[Vote] = []

    class Config:
        from_attributes = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize title."""
        if v is None:
            return v
        
        # Sanitize HTML and dangerous content
        v = re.sub(r"<.*?>", "", v)  # Remove HTML tags
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize description."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate options structure."""
        if not isinstance(v, dict):
            raise ValueError("Options must be a dictionary")
        
        if len(v) == 0:
            raise ValueError("At least one option is required")
        
        if len(v) > 20:  # Reasonable limit
            raise ValueError("Maximum 20 options allowed")
        
        # Validate option keys
        for key in v.keys():
            if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", key):
                raise ValueError(f"Invalid option key: {key}")
        
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate date relationships."""
        if self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError("closes_at must be after opens_at")
        return self


class Decision(BaseModel):
    id: uuid.UUID
    title: str = Field(..., max_length=200, description="Decision title")
    description: Optional[str] = Field(None, max_length=2000, description="Decision description")
    created_at: datetime
    overall_status: str = Field(..., description="Overall decision status")
    rounds: List[DecisionRound] = []

    class Config:
        from_attributes = True

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
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize description."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()


# Schemas for creating new objects (for receiving in API)
class VoteCreate(BaseModel):
    selected_option_key: str = Field(..., description="Selected option key")
    rationale: Optional[str] = Field(None, max_length=1000, description="Vote reasoning")

    @field_validator("selected_option_key")
    @classmethod
    def validate_option_key(cls, v: str) -> str:
        """Validate option key format."""
        if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", v):
            raise ValueError("Option key must be alphanumeric with underscores/hyphens, max 50 characters")
        return v

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize rationale."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v


class DecisionRoundCreate(BaseModel):
    round_number: int = Field(1, ge=1, le=100, description="Round number (1-100)")
    title: Optional[str] = Field(None, max_length=200, description="Round title")
    description: Optional[str] = Field(None, max_length=2000, description="Round description")
    options: Dict[str, Any] = Field(..., description="Voting options as JSON")
    opens_at: datetime
    closes_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize title."""
        if v is None:
            return v
        
        # Sanitize HTML and dangerous content
        v = re.sub(r"<.*?>", "", v)  # Remove HTML tags
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize description."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate options structure."""
        if not isinstance(v, dict):
            raise ValueError("Options must be a dictionary")
        
        if len(v) == 0:
            raise ValueError("At least one option is required")
        
        if len(v) > 20:  # Reasonable limit
            raise ValueError("Maximum 20 options allowed")
        
        # Validate option keys
        for key in v.keys():
            if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", key):
                raise ValueError(f"Invalid option key: {key}")
        
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        """Validate date relationships."""
        if self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError("closes_at must be after opens_at")
        return self


class DecisionCreate(BaseModel):
    title: str = Field(..., max_length=200, description="Decision title")
    description: Optional[str] = Field(None, max_length=2000, description="Decision description")
    initial_round: DecisionRoundCreate = Field(..., description="Initial voting round")

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
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize description."""
        if v is None:
            return v
        
        # Basic sanitization
        v = re.sub(r"<script.*?>.*?</script>", "", v, flags=re.IGNORECASE | re.DOTALL)
        v = v.replace("\0", "")  # Remove null bytes
        
        if len(v.strip()) == 0:
            return None
            
        return v.strip()