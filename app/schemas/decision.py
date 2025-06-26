import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class DecisionBase(BaseModel):
    title: str
    description: str
    status: str = "pending"

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
    round_number: int
    question: str

class DecisionRoundCreate(DecisionRoundBase):
    pass

class DecisionRoundRead(DecisionRoundBase):
    id: uuid.UUID
    created_at: datetime

class VoteBase(BaseModel):
    round_id: uuid.UUID
    voter_id: str
    vote: str
    reasoning: Optional[str] = None

class VoteCreate(VoteBase):
    pass

class VoteRead(VoteBase):
    id: uuid.UUID
    created_at: datetime