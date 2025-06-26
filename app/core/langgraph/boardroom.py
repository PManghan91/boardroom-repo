import asyncio
import uuid
from typing import Dict, List, Any, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from langgraph.graph import StateGraph, END

from app.schemas.graph import BoardroomGraphState
from app.schemas.decision import VoteRead as VoteSchema # Using VoteRead as VoteSchema
from app.models.boardroom import DecisionRound, Vote as VoteORM # Renamed to avoid clash
from app.models.database import get_db # Assuming this provides an AsyncSession
from app.core.logging import logger

# Global store for SSE queues, keyed by decision_id (string representation of UUID ID)
decision_event_queues: Dict[str, asyncio.Queue] = {}


#region Node Implementations

async def initialize_session_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """Initialize a new decision session with personas and configuration"""
    logger.info(f"Initializing session for decision {state.decision_id}")
    try:
        async with AsyncSession(get_db()) as session:
            decision = await session.get(Decision, state.decision_id)
            if not decision:
                raise ValueError(f"Decision {state.decision_id} not found")
            
            state.personas = [
                PersonaConfig(
                    id=uuid.uuid4(),
                    name=participant.name,
                    system_prompt=participant.prompt,
                    llm_model=os.getenv("LLM_MODEL", "gpt-4")
                ) for participant in decision.participants
            ]
            state.deliberation_history.append(
                DeliberationTurn(
                    persona_id=uuid.uuid4(),  # System message
                    content=f"Session started for decision: {decision.title}",
                )
            )
            state.status = "deliberating"
            logger.info(f"Initialized session with {len(state.personas)} personas")
    except Exception as e:
        state.status = "error"
        state.error = f"Session initialization failed: {str(e)}"
        logger.error(f"initialize_session_node error: {str(e)}")
    return state

async def conduct_deliberation_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """Facilitate LLM-powered discussion between personas"""
    logger.info(f"Starting deliberation round {state.current_round}")
    try:
        for persona in state.personas:
            response = await call_llm(
                messages=[{"role": "system", "content": persona.system_prompt}] +
                         [{"role": "user", "content": turn.content} for turn in state.deliberation_history],
                model=persona.llm_model,
                temperature=persona.temperature
            )
            state.deliberation_history.append(
                DeliberationTurn(
                    persona_id=persona.id,
                    content=response,
                )
            )
        logger.info(f"Completed deliberation round {state.current_round}")
    except Exception as e:
        state.status = "error"
        state.error = f"Deliberation failed: {str(e)}"
        logger.error(f"conduct_deliberation_node error: {str(e)}")
    return state

async def finalize_decision_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """Finalize the decision based on successful voting"""
    logger.info(f"Finalizing decision {state.decision_id}")
    try:
        state.final_decision = state.vote_results.tally.most_common(1)[0][0]
        state.status = "finalized"
        logger.info(f"Decision finalized: {state.final_decision}")
    except Exception as e:
        state.status = "error"
        state.error = f"Decision finalization failed: {str(e)}"
        logger.error(f"finalize_decision_node error: {str(e)}")
    return state

async def escalate_decision_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """Handle escalation when max rounds are reached without consensus"""
    logger.info(f"Escalating decision {state.decision_id}")
    try:
        state.status = "escalated"
        state.final_decision = "Escalated to human review"
        logger.warning("Decision escalated due to max rounds reached")
    except Exception as e:
        state.status = "error"
        state.error = f"Decision escalation failed: {str(e)}"
        logger.error(f"escalate_decision_node error: {str(e)}")
    return state

def should_finalize(state: BoardroomGraphState) -> str:
    """Determine next step based on voting results"""
    if state.vote_results and state.vote_results.passed:
        return "finalize_decision"
    if state.current_round >= state.max_rounds:
        return "escalate_decision"
    return "continue_deliberation"

#endregion

async def collect_votes_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """
    Collects all votes for the current round of a decision.
    Assumes state.decision_id and state.current_round_id are UUIDs.
    """
    logger.info(f"collect_votes_node: Processing decision_id={state.decision_id}, round_id={state.current_round_id}")
    if not isinstance(state.decision_id, uuid.UUID):
        state.status = "error"
        state.error = "decision_id is not a valid UUID."
        logger.error(f"collect_votes_node: Invalid decision_id type: {state.decision_id}")
        return state

    if state.current_round_id is None:
        state.status = "error"
        state.error = "current_round_id is not set"
        logger.error(f"collect_votes_node: Missing current_round_id for decision_id={state.decision_id}")
        return state
    
    if not isinstance(state.current_round_id, uuid.UUID):
        state.status = "error"
        state.error = "current_round_id is not a valid UUID."
        logger.error(f"collect_votes_node: Invalid current_round_id type for decision_id={state.decision_id}: {state.current_round_id}")
        return state

    db_round_id: uuid.UUID = state.current_round_id
    fetched_votes: List[VoteSchema] = []
    try:
        async for session in get_db(): # type: AsyncSession
            try:
                statement = select(VoteORM).where(VoteORM.decision_round_id == db_round_id)
                results = await session.exec(statement)
                db_votes: List[VoteORM] = results.all()

                for db_vote_orm in db_votes:
                    # VoteSchema now expects UUIDs, VoteORM provides them.
                    # Mapping voter_ip to voter_id and selected_option_key to vote.
                    vote_schema_data = {
                        "id": db_vote_orm.id, # UUID
                        "round_id": db_vote_orm.decision_round_id, # UUID
                        "voter_id": db_vote_orm.voter_ip,
                        "vote": db_vote_orm.selected_option_key,
                        "reasoning": db_vote_orm.rationale,
                        "created_at": db_vote_orm.voted_at,
                    }
                    fetched_votes.append(VoteSchema(**vote_schema_data))
                
                state.votes = fetched_votes
                state.status = "votes_collected"
                state.error = None
                logger.info(f"collect_votes_node: Collected {len(fetched_votes)} votes for decision_id={state.decision_id}, round_id={db_round_id}")
            except Exception as e:
                state.status = "error"
                state.error = f"Database error in collect_votes_node: {str(e)}"
                logger.error(f"collect_votes_node: DB error for decision_id={state.decision_id}, round_id={db_round_id}: {e}", exc_info=True)
            finally:
                break
    except Exception as e:
        state.status = "error"
        state.error = f"Failed to get DB session in collect_votes_node: {str(e)}"
        logger.error(f"collect_votes_node: Session error for decision_id={state.decision_id}: {e}", exc_info=True)

    return state


async def compute_results_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """
    Computes results based on collected votes.
    """
    logger.info(f"compute_results_node: Processing decision_id={state.decision_id}")
    if not state.votes:
        state.status = "no_votes_to_compute"
        state.results = {}
        logger.info(f"compute_results_node: No votes found for decision_id={state.decision_id}")
        return state

    tally: Dict[str, int] = {}
    for vote_item in state.votes:
        tally[vote_item.vote] = tally.get(vote_item.vote, 0) + 1
    
    state.results = {"tally": tally}
    state.status = "results_computed"
    state.error = None
    logger.info(f"compute_results_node: Results computed for decision_id={state.decision_id}: {tally}")
    return state


async def notify_clients_node(state: BoardroomGraphState) -> BoardroomGraphState:
    """
    Notifies clients about state changes via SSE queue.
    Assumes state.decision_id is a UUID.
    """
    logger.info(f"notify_clients_node: Preparing notification for decision_id={state.decision_id}")
    
    if not isinstance(state.decision_id, uuid.UUID):
        logger.error(f"notify_clients_node: decision_id is not a UUID: {state.decision_id}. Skipping notification.")
        return state # Cannot proceed without a valid UUID for keying

    queue_key_str = str(state.decision_id) # Convert UUID to string for dict key and SSE payload

    if queue_key_str in decision_event_queues:
        queue = decision_event_queues[queue_key_str]
        
        # Prepare payload, ensuring all UUIDs are converted to strings for JSON
        # Pydantic's model_dump(mode='json') or iterating and converting manually can work.
        # For simplicity, converting known UUID fields to strings here.
        
        votes_payload = []
        for vote in state.votes:
            vote_dict = vote.model_dump()
            vote_dict['id'] = str(vote.id)
            vote_dict['round_id'] = str(vote.round_id)
            votes_payload.append(vote_dict)

        payload = {
            "decision_id": queue_key_str,
            "current_round_id": str(state.current_round_id) if state.current_round_id else None,
            "votes": votes_payload, # Votes now have string UUIDs
            "results": state.results,
            "status": state.status,
            "error": state.error,
        }
        try:
            await queue.put(payload)
            logger.info(f"notify_clients_node: Notification sent for decision_id={queue_key_str}, status={state.status}")
        except Exception as e:
            logger.error(f"notify_clients_node: Failed to put message on queue for decision_id={queue_key_str}: {e}", exc_info=True)
    else:
        logger.warning(f"notify_clients_node: No active SSE queue for decision_id={queue_key_str}")
    
    return state


def should_compute_results(state: BoardroomGraphState) -> str:
    """
    Conditional edge: determines if results should be computed.
    Example: compute if status is 'votes_collected'.
    """
    # This is a placeholder condition. Real logic might depend on voting period ending,
    # or a specific number of votes received, or an explicit trigger.
    if state.status == "votes_collected":
        logger.info(f"should_compute_results: Transitioning to compute_results for decision_id={state.decision_id}")
        return "compute_results"
    elif state.status == "error":
        logger.info(f"should_compute_results: Transitioning to end due to error for decision_id={state.decision_id}")
        return END # Or an error handling node
    logger.info(f"should_compute_results: Staying, current status {state.status} for decision_id={state.decision_id}")
    # This default path means it might loop back to collect_votes or wait for external trigger.
    # For a simple flow: collect -> compute -> notify -> end.
    # If we want to wait for more votes, this logic needs to be more complex.
    # For now, if not "votes_collected", it implies waiting or an issue.
    # Let's assume for now it might go to notify or end.
    return "notify_clients" # Default to notify, then potentially end or loop.


def create_boardroom_workflow():
    """
    Creates the enhanced LangGraph workflow for boardroom decisions.
    """
    workflow = StateGraph(BoardroomGraphState)

    # Add all nodes
    workflow.add_node("initialize_session", initialize_session_node)
    workflow.add_node("conduct_deliberation", conduct_deliberation_node)
    workflow.add_node("collect_votes", collect_votes_node)
    workflow.add_node("compute_results", compute_results_node)
    workflow.add_node("finalize_decision", finalize_decision_node)
    workflow.add_node("escalate_decision", escalate_decision_node)
    workflow.add_node("notify_clients", notify_clients_node)

    # Set initial entry point
    workflow.set_entry_point("initialize_session")

    # Define transitions
    workflow.add_edge("initialize_session", "conduct_deliberation")
    
    workflow.add_conditional_edges(
        "conduct_deliberation",
        lambda state: "collect_votes" if state.deliberation_history else "conduct_deliberation",
    )
    
    # After computing results, notify clients
    workflow.add_conditional_edges(
        "compute_results",
        should_finalize,
        {
            "finalize_decision": "finalize_decision",
            "escalate_decision": "escalate_decision",
            "continue_deliberation": "conduct_deliberation"
        }
    )
    
    workflow.add_edge("finalize_decision", "notify_clients")
    workflow.add_edge("escalate_decision", "notify_clients")
    workflow.add_edge("notify_clients", END)

    # Add persistence using PostgreSQL checkpointer
    checkpointer = PostgresSaver.from_conn_string(
        os.getenv("DB_URI"),
        serializer=lambda obj: json.dumps(obj, default=str),
        deserializer=json.loads
    )

    logger.info("Boardroom workflow compiled with PostgreSQL persistence")
    return workflow.compile(checkpointer=checkpointer)

# Example of how to get a specific graph instance (to be called from API layer)
# compiled_graphs: Dict[uuid.UUID, Any] = {} # Store compiled graphs per decision

# def get_boardroom_graph(decision_id: uuid.UUID, checkpointer): # checkpointer per decision
#     if decision_id not in compiled_graphs:
#         # Each decision might need its own checkpointer config if state is isolated per decision
#         # For now, assuming one workflow definition, checkpointer handles state separation by config.
#         app = create_boardroom_workflow(checkpointer=checkpointer) # Pass appropriate checkpointer
#         compiled_graphs[decision_id] = app
#     return compiled_graphs[decision_id]

# The main workflow instance can be created once and used if the state correctly
# isolates data per decision_id via the checkpointer's config.
# boardroom_workflow_app = create_boardroom_workflow()