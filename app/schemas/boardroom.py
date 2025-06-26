import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# Base Schemas for DB models (for reading/returning from API)
class Vote(BaseModel):
    id: uuid.UUID
    decision_round_id: uuid.UUID
    voter_ip: str  # pydantic doesn't have an INET type, so str is fine
    selected_option_key: str
    voted_at: datetime
    rationale: Optional[str] = None

    class Config:
        orm_mode = True


class DecisionRound(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    round_number: int
    title: Optional[str] = None
    description: Optional[str] = None
    options: Any  # JSONB can be any valid JSON
    opens_at: datetime
    closes_at: Optional[datetime] = None
    round_status: str
    created_at: datetime
    votes: List[Vote] = []

    class Config:
        orm_mode = True


class Decision(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    created_at: datetime
    overall_status: str
    rounds: List[DecisionRound] = []

    class Config:
        from_attributes = True


# Schemas for creating new objects (for receiving in API)
class VoteCreate(BaseModel):
    selected_option_key: str
    rationale: Optional[str] = None


class DecisionRoundCreate(BaseModel):
    round_number: int = 1
    title: Optional[str] = None
    description: Optional[str] = None
    options: Any
    opens_at: datetime
    closes_at: Optional[datetime] = None


class DecisionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    # Allow creating the first round along with the decision
    initial_round: DecisionRoundCreate