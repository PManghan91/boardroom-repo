import os
import uuid
import httpx
import asyncio
from typing import Dict, Any
from app.core.langgraph.boardroom import BoardroomGraphState, create_boardroom_workflow
from app.core.logging import logger

async def call_llm(messages: list, model: str, temperature: float = 0.7) -> str:
    """Make async LLM API call with retry logic"""
    max_retries = 3
    base_url = os.getenv("LLM_API_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM API call attempt {attempt+1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    return ""

# Initialize the new workflow
# Note: If create_boardroom_workflow requires a checkpointer, this needs to be provided.
# For now, assuming it can be called without arguments as per its current definition.
workflow = create_boardroom_workflow()

def run_boardroom_workflow(initial_state_data: dict):
    """
    Runs the Boardroom LangGraph workflow with the given initial state data.
    The initial_state_data must contain at least 'decision_id' and 'status'.
    Example: {'decision_id': 123, 'current_round_id': 1, 'status': 'pending_votes'}
    """
    logger.info(f"run_boardroom_workflow: Initializing with data: {initial_state_data}")
    try:
        # Ensure required fields for BoardroomGraphState are present
        if 'decision_id' not in initial_state_data or 'status' not in initial_state_data:
            logger.error("run_boardroom_workflow: Missing 'decision_id' or 'status' in initial_state_data.")
            # Or raise an error, or return a specific error state
            return {"error": "Missing 'decision_id' or 'status' in initial_state_data."}

        initial_state = BoardroomGraphState(**initial_state_data)
        
        # The graph nodes are async. LangGraph's .invoke() on a compiled graph
        # can handle async nodes. If workflow.invoke itself becomes a coroutine
        # (e.g. if compiled with an async checkpointer or certain streaming modes),
        # this function would need to be `async` and `await` the invoke call.
        # For now, assuming synchronous invoke that internally handles async nodes.
        final_state = workflow.invoke(initial_state)
        logger.info(f"run_boardroom_workflow: Workflow finished. Final state: {final_state}")
        return final_state
    except Exception as e:
        logger.error(f"run_boardroom_workflow: Error during workflow execution: {e}", exc_info=True)
        # Return an error state or re-raise
        return {"error": f"Workflow execution failed: {str(e)}"}

# For compatibility, if old run_workflow is still called elsewhere, it might need adjustment
# or removal. Renaming to run_boardroom_workflow for clarity.
# If direct replacement is needed:
# def run_workflow(state_data: dict):
#     return run_boardroom_workflow(state_data)