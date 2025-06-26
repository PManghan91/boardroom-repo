import uuid
from typing import List

from app.models.boardroom import (
    Decision,
    DecisionRound,
    Vote,
)
from app.models.database import get_db
from app.schemas.boardroom import (
    DecisionCreate,
    Decision as DecisionSchema,
    DecisionRound as DecisionRoundSchema,
    DecisionRoundCreate,
    VoteCreate,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from sqlalchemy.orm import Session, joinedload

router = APIRouter()


@router.post("/decisions", response_model=DecisionSchema, status_code=201)
def create_decision(decision_in: DecisionCreate, db: Session = Depends(get_db)):
    """
    Create a new decision and its initial voting round.
    """
    # Create the main decision object
    db_decision = Decision(
        title=decision_in.title,
        description=decision_in.description,
    )
    db.add(db_decision)
    db.flush()  # Flush to get the generated decision ID

    # Create the initial round for this decision
    initial_round = decision_in.initial_round
    db_round = DecisionRound(
        decision_id=db_decision.id,
        round_number=initial_round.round_number,
        title=initial_round.title or db_decision.title, # Default to decision title
        description=initial_round.description or db_decision.description, # Default to decision desc
        options=initial_round.options,
        opens_at=initial_round.opens_at,
        closes_at=initial_round.closes_at,
    )
    db.add(db_round)
    db.commit()
    db.refresh(db_decision)
    return db_decision


@router.get("/decisions", response_model=List[DecisionSchema])
def list_decisions(db: Session = Depends(get_db)):
    """
    List all decisions.
    """
    return db.query(Decision).options(joinedload(Decision.rounds).joinedload(DecisionRound.votes)).all()


@router.get("/decisions/{decision_id}", response_model=DecisionSchema)
def get_decision(decision_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get a single decision by its ID, including all rounds and votes.
    """
    decision = db.query(Decision).options(
        joinedload(Decision.rounds).joinedload(DecisionRound.votes)
    ).filter(Decision.id == decision_id).first()
    
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/rounds/{round_id}/vote", status_code=201)
def submit_vote(
    round_id: uuid.UUID, vote_in: VoteCreate, request: Request, db: Session = Depends(get_db)
):
    """
    Submit a vote for a specific decision round.
    """
    db_round = db.query(DecisionRound).filter(DecisionRound.id == round_id).first()
    if not db_round:
        raise HTTPException(status_code=404, detail="Decision round not found")

    # Basic validation: check if the selected option is valid for this round
    valid_option_keys = [opt.get("key") for opt in db_round.options if isinstance(opt, dict) and "key" in opt]
    if vote_in.selected_option_key not in valid_option_keys:
        raise HTTPException(status_code=400, detail=f"Invalid option '{vote_in.selected_option_key}'. Valid options are: {valid_option_keys}")

    # Check for existing vote (for idempotency)
    voter_ip = request.client.host
    existing_vote = db.query(Vote).filter(
        Vote.decision_round_id == round_id,
        Vote.voter_ip == voter_ip
    ).first()

    if existing_vote:
        # In a real app, you might allow vote changes. For now, we prevent duplicates.
        raise HTTPException(status_code=409, detail="You have already voted in this round.")

    db_vote = Vote(
        decision_round_id=round_id,
        voter_ip=voter_ip,
        selected_option_key=vote_in.selected_option_key,
        rationale=vote_in.rationale,
    )
    db.add(db_vote)
    db.commit()

    return {"status": "vote recorded"}