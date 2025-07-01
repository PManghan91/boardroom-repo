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
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.utils.sanitization import (
    sanitize_string,
    validate_ip_address,
    validate_uuid_string,
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
@limiter.limit("10 per minute")
def create_decision(request: Request, decision_in: DecisionCreate, db: Session = Depends(get_db)):
    """
    Create a new decision and its initial voting round.
    """
    try:
        logger.info("create_decision_request", title=decision_in.title[:50])
        
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
        
        logger.info("decision_created", decision_id=str(db_decision.id))
        return db_decision
        
    except ValueError as ve:
        logger.error("decision_creation_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error("decision_creation_failed", error=str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create decision")


@router.get("/decisions", response_model=List[DecisionSchema])
@limiter.limit("50 per minute")
def list_decisions(request: Request, db: Session = Depends(get_db)):
    """
    List all decisions.
    """
    try:
        decisions = db.query(Decision).options(
            joinedload(Decision.rounds).joinedload(DecisionRound.votes)
        ).all()
        logger.info("decisions_listed", count=len(decisions))
        return decisions
    except Exception as e:
        logger.error("list_decisions_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve decisions")


@router.get("/decisions/{decision_id}", response_model=DecisionSchema)
@limiter.limit("100 per minute")
def get_decision(request: Request, decision_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get a single decision by its ID, including all rounds and votes.
    """
    try:
        # Validate UUID
        validate_uuid_string(str(decision_id))
        
        decision = db.query(Decision).options(
            joinedload(Decision.rounds).joinedload(DecisionRound.votes)
        ).filter(Decision.id == decision_id).first()
        
        if not decision:
            logger.warning("decision_not_found", decision_id=str(decision_id))
            raise HTTPException(status_code=404, detail="Decision not found")
        
        logger.info("decision_retrieved", decision_id=str(decision_id))
        return decision
        
    except ValueError as ve:
        logger.error("get_decision_validation_failed", error=str(ve), decision_id=str(decision_id), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_decision_failed", error=str(e), decision_id=str(decision_id), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve decision")


@router.post("/rounds/{round_id}/vote", status_code=201)
@limiter.limit("20 per minute")
def submit_vote(
    request: Request,
    round_id: uuid.UUID,
    vote_in: VoteCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a vote for a specific decision round.
    """
    try:
        # Validate UUID
        validate_uuid_string(str(round_id))
        
        # Get client IP and validate
        voter_ip = request.client.host if request.client else "unknown"
        if voter_ip != "unknown":
            validate_ip_address(voter_ip)
        
        logger.info("vote_submission_attempt", round_id=str(round_id), voter_ip=voter_ip)
        
        db_round = db.query(DecisionRound).filter(DecisionRound.id == round_id).first()
        if not db_round:
            logger.warning("round_not_found_for_vote", round_id=str(round_id))
            raise HTTPException(status_code=404, detail="Decision round not found")

        # Enhanced validation: check if the selected option is valid for this round
        if isinstance(db_round.options, dict):
            valid_option_keys = list(db_round.options.keys())
        elif isinstance(db_round.options, list):
            valid_option_keys = [
                opt.get("key") for opt in db_round.options
                if isinstance(opt, dict) and "key" in opt
            ]
        else:
            logger.error("invalid_round_options_format", round_id=str(round_id), options_type=type(db_round.options))
            raise HTTPException(status_code=500, detail="Invalid round options format")
        
        if vote_in.selected_option_key not in valid_option_keys:
            logger.warning(
                "invalid_vote_option",
                round_id=str(round_id),
                selected_option=vote_in.selected_option_key,
                valid_options=valid_option_keys
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid option '{vote_in.selected_option_key}'. Valid options are: {valid_option_keys}"
            )

        # Check for existing vote (for idempotency)
        existing_vote = db.query(Vote).filter(
            Vote.decision_round_id == round_id,
            Vote.voter_ip == voter_ip
        ).first()

        if existing_vote:
            logger.warning("duplicate_vote_attempt", round_id=str(round_id), voter_ip=voter_ip)
            raise HTTPException(status_code=409, detail="You have already voted in this round.")

        # Create the vote
        db_vote = Vote(
            decision_round_id=round_id,
            voter_ip=voter_ip,
            selected_option_key=vote_in.selected_option_key,
            rationale=vote_in.rationale,
        )
        db.add(db_vote)
        db.commit()

        logger.info(
            "vote_recorded",
            round_id=str(round_id),
            voter_ip=voter_ip,
            selected_option=vote_in.selected_option_key
        )
        
        return {"status": "vote recorded", "vote_id": str(db_vote.id)}
        
    except ValueError as ve:
        logger.error("vote_validation_failed", error=str(ve), round_id=str(round_id), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("vote_submission_failed", error=str(e), round_id=str(round_id), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit vote")