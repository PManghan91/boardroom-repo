import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import UniqueConstraint

Base = declarative_base()


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    title = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    overall_status = Column(String, nullable=False, default="draft")
    
    rounds = relationship("DecisionRound", back_populates="decision", cascade="all, delete-orphan")


class DecisionRound(Base):
    __tablename__ = "decision_rounds"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    title = Column(Text)
    description = Column(Text)
    options = Column(JSON, nullable=False)
    opens_at = Column(DateTime, nullable=False)
    closes_at = Column(DateTime)
    round_status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    decision = relationship("Decision", back_populates="rounds")
    votes = relationship("Vote", back_populates="round", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('decision_id', 'round_number', name='_decision_round_uc'),)


class Vote(Base):
    __tablename__ = "votes"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    decision_round_id = Column(UUID(as_uuid=True), ForeignKey("decision_rounds.id"), nullable=False)
    voter_ip = Column(INET, nullable=False)
    selected_option_key = Column(Text, nullable=False)
    voted_at = Column(DateTime, nullable=False, server_default=func.now())
    rationale = Column(Text)

    round = relationship("DecisionRound", back_populates="votes")

    __table_args__ = (UniqueConstraint('decision_round_id', 'voter_ip', name='_round_voter_uc'),)