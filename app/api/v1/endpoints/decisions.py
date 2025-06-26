import asyncio
import uuid # Added for UUID type hinting
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional # Added Optional

from app.models.database import get_db
from app.schemas.decision import (
    DecisionCreate,
    DecisionRead,
    DecisionRoundCreate,
    DecisionRoundRead,
    VoteCreate,
    VoteRead
)
from app.services.database import database_service # Using global instance
from app.core.langgraph.boardroom import create_boardroom_workflow, BoardroomGraphState, decision_event_queues
from app.core.config import settings
from app.core.logging import logger
from langgraph.checkpoint.postgres import PostgresSaver

router = APIRouter()

pg_saver = None
boardroom_app = None
if not settings.POSTGRES_URL:
    logger.error("POSTGRES_URL is not set. LangGraph checkpointing will fail.")
else:
    try:
        pg_saver = PostgresSaver.from_conn_string(settings.POSTGRES_URL)
        compiled_workflow = create_boardroom_workflow()
        boardroom_app = compiled_workflow.with_config({"checkpointer": pg_saver})
        logger.info("PostgresSaver and Boardroom LangGraph App initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize PostgresSaver or Boardroom App: {e}", exc_info=True)
        pg_saver = None
        boardroom_app = None

async def run_graph_async(config: Dict[str, Any], graph_input_state_data: Dict[str, Any]):
    """Helper to run graph invocation."""
    if boardroom_app:
        try:
            # Ensure decision_id and current_round_id are UUIDs if they are strings
            raw_decision_id = graph_input_state_data.get("decision_id")
            if isinstance(raw_decision_id, str):
                graph_input_state_data["decision_id"] = uuid.UUID(raw_decision_id)
            elif not isinstance(raw_decision_id, uuid.UUID): # Ensure it's UUID
                 logger.error(f"run_graph_async: decision_id is not a valid UUID string or UUID object: {raw_decision_id}")
                 return


            raw_current_round_id = graph_input_state_data.get("current_round_id")
            if raw_current_round_id is not None: # Allow None
                if isinstance(raw_current_round_id, str):
                    graph_input_state_data["current_round_id"] = uuid.UUID(raw_current_round_id)
                elif not isinstance(raw_current_round_id, uuid.UUID):
                    logger.error(f"run_graph_async: current_round_id is not a valid UUID string or UUID object: {raw_current_round_id}")
                    return
            
            graph_state_obj = BoardroomGraphState(**graph_input_state_data)
            
            decision_id_str_for_queue = str(graph_state_obj.decision_id) # Use string for queue key
            if decision_id_str_for_queue not in decision_event_queues:
                 decision_event_queues[decision_id_str_for_queue] = asyncio.Queue(maxsize=100)
                 logger.info(f"run_graph_async: Created SSE queue for decision_id {decision_id_str_for_queue}")

            logger.info(f"run_graph_async: Invoking graph with config: {config}, state: {graph_state_obj.model_dump_json(indent=2)}")
            boardroom_app.invoke(graph_state_obj.model_dump(), config=config) # Pass the dict representation
            logger.info(f"run_graph_async: Graph invocation completed for config: {config}")
        except Exception as e:
            logger.error(f"run_graph_async: Error invoking graph for config {config}: {e}", exc_info=True)
    else:
        logger.error("run_graph_async: Boardroom app not initialized. Cannot run graph.")


@router.post("/", response_model=DecisionRead)
async def create_decision_endpoint(
    decision_data: DecisionCreate, # Schemas now use UUIDs
    background_tasks: BackgroundTasks,
):
    # create_decision should now return DecisionRead (which now has UUID id)
    created_decision: DecisionRead = await database_service.create_decision(decision_data)
    
    if not created_decision:
        raise HTTPException(status_code=500, detail="Failed to create decision in DB")

    if boardroom_app:
        thread_id = str(created_decision.id) # Convert UUID to string for thread_id
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_round_id_uuid: Optional[uuid.UUID] = None
        # Logic to get initial_round_id if a decision is created with an initial round
        # This depends on how `database_service.create_decision` and `DecisionRead` are structured.
        # If `DecisionRead` includes a list of `DecisionRoundRead` for its rounds:
        if hasattr(created_decision, 'rounds') and created_decision.rounds and len(created_decision.rounds) > 0:
            # Assuming the first round in the list is the initial one
            # And assuming created_decision.rounds[0] is a DecisionRoundRead object with a UUID id
            if isinstance(created_decision.rounds[0], DecisionRoundRead) and hasattr(created_decision.rounds[0], 'id'):
                 initial_round_id_uuid = created_decision.rounds[0].id


        initial_graph_state_data = {
            "decision_id": created_decision.id, # UUID
            "current_round_id": initial_round_id_uuid, # Optional UUID
            "votes": [],
            "results": None,
            "status": "decision_created" if not initial_round_id_uuid else "pending_votes"
        }
        logger.info(f"create_decision_endpoint: Scheduling graph run for new decision_id: {created_decision.id}")
        background_tasks.add_task(run_graph_async, config, initial_graph_state_data)

    return created_decision

@router.get("/{decision_id}", response_model=DecisionRead)
async def get_decision_endpoint(
    decision_id: uuid.UUID, # Path param is now UUID
):
    # get_decision should now expect UUID and return DecisionRead (with UUID id)
    decision_val = await database_service.get_decision(decision_id)
    if not decision_val:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision_val

@router.post("/{decision_id}/rounds", response_model=DecisionRoundRead)
async def create_round_for_decision_endpoint(
    decision_id: uuid.UUID, # Path param is now UUID
    round_data: DecisionRoundCreate, # DecisionRoundCreate.decision_id is UUID
    background_tasks: BackgroundTasks,
):
    if round_data.decision_id != decision_id: # Both are UUIDs now
        raise HTTPException(status_code=400, detail="Path decision_id does not match payload decision_id")

    # create_round should expect UUID and return DecisionRoundRead (with UUID id)
    new_round: DecisionRoundRead = await database_service.create_round(decision_id, round_data)

    if boardroom_app and new_round:
        thread_id = str(decision_id) # Convert UUID to string for thread_id
        config = {"configurable": {"thread_id": thread_id}}
        
        graph_update_state_data = {
            "decision_id": decision_id, # UUID
            "current_round_id": new_round.id, # UUID from DecisionRoundRead
            "votes": [],
            "results": None,
            "status": "pending_votes" 
        }
        logger.info(f"create_round_for_decision_endpoint: Scheduling graph update for new round {new_round.id} in decision {decision_id}")
        background_tasks.add_task(run_graph_async, config, graph_update_state_data)
        
    return new_round


@router.post("/rounds/{round_id}/votes", response_model=VoteRead)
async def create_vote_endpoint(
    round_id: uuid.UUID, # Path param is now UUID
    vote_data: VoteCreate, # VoteCreate.round_id is UUID
    background_tasks: BackgroundTasks,
):
    if vote_data.round_id != round_id: # Both are UUIDs now
         raise HTTPException(status_code=400, detail="Path round_id does not match payload round_id")

    # create_vote should expect UUID and return VoteRead (with UUID id)
    created_vote: VoteRead = await database_service.create_vote(round_id, vote_data)

    if boardroom_app and created_vote:
        # get_round_details should expect UUID and return an object with decision_id (UUID)
        # This method needs to be implemented in DatabaseService
        round_details_obj = await database_service.get_round_details(round_id) 
        
        if not round_details_obj or not hasattr(round_details_obj, 'decision_id') or not isinstance(round_details_obj.decision_id, uuid.UUID):
            logger.error(f"create_vote_endpoint: Could not determine valid decision_id (UUID) for round_id {round_id}. Cannot invoke graph.")
            return created_vote 

        decision_id_for_graph: uuid.UUID = round_details_obj.decision_id
        thread_id = str(decision_id_for_graph) # Convert UUID to string for thread_id
        config = {"configurable": {"thread_id": thread_id}}
        
        graph_trigger_state_data = {
            "decision_id": decision_id_for_graph, # UUID
            "current_round_id": round_id, # UUID
            "votes": [],
            "results": None,
            "status": "new_vote_cast"
        }
        logger.info(f"create_vote_endpoint: Scheduling graph run for new vote in round_id: {round_id}, decision_id: {decision_id_for_graph}")
        background_tasks.add_task(run_graph_async, config, graph_trigger_state_data)
        
    return created_vote