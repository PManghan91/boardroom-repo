import asyncio
import json
import uuid # Added
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Dict # Added Dict

from app.core.langgraph.boardroom import decision_event_queues # Added
from app.core.logging import logger # Added

router = APIRouter()

async def sse_event_generator(decision_id_key: str, request: Request) -> AsyncGenerator[str, None]: # Renamed decision_id_uuid to decision_id_key
    """
    Generates SSE events for a given decision_id (string key) by consuming from its queue.
    """
    queue = decision_event_queues.get(decision_id_key)
    if not queue:
        logger.warning(f"sse_event_generator: No queue found for decision_id_key {decision_id_key} at generator start.")
        error_event = {"error": "Decision event stream not available or decision ID invalid."}
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
        return

    logger.info(f"sse_event_generator: Starting event stream for decision_id_key {decision_id_key}")
    try:
        # Send an initial connected event, using the decision_id_key which is str(UUID)
        yield f"event: connected\ndata: {json.dumps({'decision_id': decision_id_key, 'status': 'monitoring_active'})}\n\n"

        while True:
            if await request.is_disconnected():
                logger.info(f"sse_event_generator: Client disconnected for decision_id_key {decision_id_key}")
                break
            
            try:
                graph_payload: Dict = await asyncio.wait_for(queue.get(), timeout=30.0) # Timeout to check disconnect
                
                event_type = graph_payload.get("status", "state_update") # Default event type
                
                # Ensure all UUIDs in payload are strings for JSON serialization
                def serialize_payload(data):
                    if isinstance(data, dict):
                        return {k: serialize_payload(v) for k, v in data.items()}
                    elif isinstance(data, list):
                        return [serialize_payload(i) for i in data]
                    elif isinstance(data, uuid.UUID):
                        return str(data)
                    return data

                yield f"event: {event_type}\ndata: {json.dumps(serialize_payload(graph_payload))}\n\n"
                queue.task_done()
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n" # Send a keep-alive comment
                continue
            except Exception as e:
                logger.error(f"sse_event_generator: Error processing queue item for {decision_id_key}: {e}", exc_info=True)
                error_event = {"error": "Error processing event from graph."}
                yield f"event: error\ndata: {json.dumps(error_event)}\n\n"

    except asyncio.CancelledError:
        logger.info(f"sse_event_generator: Connection cancelled by client for decision_id_key {decision_id_key}")
    except Exception as e:
        logger.error(f"sse_event_generator: Unhandled exception for {decision_id_key}: {e}", exc_info=True)
        if not await request.is_disconnected():
            error_payload = json.dumps({"error": "Stream error", "detail": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"
    finally:
        logger.info(f"sse_event_generator: Stream ended for decision_id_key {decision_id_key}")
        # Note: Queue is not removed here, as it's shared per decision_id.
        # It should be cleaned up when the decision process itself ends.

@router.get("/events", summary="Subscribe to Boardroom Decision Events (SSE)")
async def stream_boardroom_events(request: Request, decision_id: str): # decision_id from query is a string
    """
    Streams real-time updates for a specific boardroom decision using Server-Sent Events (SSE).

    - **decision_id**: The ID of the decision to monitor (expects a string, typically a UUID).
    """
    if not decision_id:
        raise HTTPException(status_code=400, detail="decision_id query parameter is required.")

    # Validate if the decision_id string is a valid UUID format before using it as a key
    try:
        uuid.UUID(decision_id) # This validates format but doesn't mean it exists
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision_id format. Must be a valid UUID string.")

    decision_id_key = decision_id # Use the validated string UUID as the key

    if decision_id_key not in decision_event_queues:
        logger.info(f"stream_boardroom_events: Creating new event queue for decision_id_key {decision_id_key}")
        decision_event_queues[decision_id_key] = asyncio.Queue(maxsize=100)
    else:
        logger.info(f"stream_boardroom_events: Using existing event queue for decision_id_key {decision_id_key}")
    
    return StreamingResponse(sse_event_generator(decision_id_key, request), media_type="text/event-stream")