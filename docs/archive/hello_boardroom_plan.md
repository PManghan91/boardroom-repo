# Project Plan: "hello-boardroom" Runtime

This document outlines the sub-tasks required to implement the "hello-boardroom" feature.

## 1. API Route

- **Status:** Done
- **File:** `app/routers/boardroom.py`
- **Requirements:**
  - Create a `POST /boardrooms/{room_id}/message` endpoint.
  - Validate JSON payload: `{ "author":"boss", "content":"..." }`.
  - Persist the message to Redis Stream `br:{room_id}` using `XADD`.
  - Return `202 Accepted`.

## 2. Redis Streams Worker

- **Status:** Done
- **File:** `app/workers/stream_worker.py`
- **Requirements:**
  - Create a consumer group `br_cg` on each stream.
  - Use an `XREADGROUP` loop to pull messages from the stream.
  - For each message, call a stub function `run_boardroom_agents(room_id, message)` located in `app/core/langgraph_runner.py`.
  - Acknowledge message processing with `XACK`.
  - Log all state transitions.
  - Snapshot the combined agent state to the `boardroom_snapshots` Postgres table (columns: `id`, `room_id`, `ts`, `state` JSONB).

## 3. Health & Test

- **Status:** Done
- **Requirements:**
  - Add a `GET /health` endpoint that returns `{ "status": "ok" }`.
  - Write `pytest` tests using `TestClient` to:
    - Assert `GET /health` returns a 200 status code.
    - Assert `POST /boardrooms/{room_id}/message` returns a 202 status code.
  - Write unit tests for the worker using `fakeredis`.

## 4. Docker Updates

- **Status:** Done
- **File:** `docker-compose.yml`
- **Requirements:**
  - Extend the `api` service command to: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - Add a new `worker` service that runs `python -m app.workers.stream_worker`.
  - Mount a Postgres volume named `pgdata`.

## 5. Run Verification

- **Status:** Done
- **Commands:**
  - `docker compose up -d --build`
  - `curl -X POST localhost:8000/boardrooms/demo/message -H 'Content-Type: application/json' -d '{"author":"boss","content":"Kick off"}'`
- **Checks:**
  - The `curl` command should return a 202 status code.
  - A `psql` query `SELECT COUNT(*) FROM boardroom_snapshots;` should return a value greater than 0.

## 6. Branch & PR

- **Status:** Pending
- **Requirements:**
  - Create a new git branch: `feat/hello-boardroom`.
  - Commit all new and modified files.
  - Push the branch and open a pull request titled "feat: hello-boardroom endpoint, worker, snapshots".
  - The PR description must include:
    - `docker-compose ps` output.
    - `pytest -q` test run output.
    - Sample log lines showing agents firing.
    - Clarification on agent output, `XREADGROUP` latency, and snapshot size.
