You are the senior developer on **PManghan91/boardroom-repo**.  
**Task 02**: add the “hello-boardroom” runtime so we can post a message, see five LangGraph agents run, and store the state in Postgres.

SUB-TASKS
---------

1. **API route**  
   * File: `app/routers/boardroom.py`  
   * `POST /boardrooms/{room_id}/message` → validate JSON `{ "author":"boss", "content":"..." }`,  
     persist to Redis Stream `br:{room_id}` (`XADD`), return `202 Accepted`.

2. **Redis Streams worker**  
   * File: `app/workers/stream_worker.py`  
   * Create consumer-group `br_cg` on each stream; use `XREADGROUP` loop to pull messages.  
   * For each record call `run_boardroom_agents(room_id, message)` (stub in `app/core/langgraph_runner.py`).  
   * Ack with `XACK`.  
   * Log every transition; snapshot combined agent state to Postgres table `boardroom_snapshots` (id, room_id, ts, state JSONB).

3. **Health & Test**  
   * Add `GET /health` returning `{status:"ok"}`.  
   * Write pytest using `TestClient` to assert health==200 and posting a message yields 202.  
   * Unit-test worker via fakeredis.

4. **Docker updates**  
   * Extend `api` service CMD to `uvicorn app.main:app --host 0.0.0.0 --port 8000`.  
   * Add `worker` service running `python -m app.workers.stream_worker`.  
   * Mount a Postgres volume (`pgdata`).

5. **Run verification**  
   * `docker compose up -d --build`  
   * `curl -X POST localhost:8000/boardrooms/demo/message -H 'Content-Type: application/json' -d '{"author":"boss","content":"Kick off"}'` → 202  
   * `psql` check: `SELECT COUNT(*) FROM boardroom_snapshots;` > 0  

6. **Branch & PR**  
   * `git checkout -b feat/hello-boardroom`  
   * Commit new routes, worker, tests, compose tweaks.  
   * Push & open PR titled **“feat: hello-boardroom endpoint, worker, snapshots”** including:  
     * compose ps output,  
     * test run (`pytest -q`),  
     * sample log lines showing agents firing.

CLARIFY IN PR DESCRIPTION
-------------------------

* Did the five hard-coded agents produce expected output?  
* Any latency or errors in XREADGROUP loop?  
* Confirm JSONB snapshot size reasonable (<10 KB per turn).  

# References (quick look-ups for implementation)

# Redis XREADGROUP Python guide :contentReference[oaicite:0]{index=0}

# Redis Streams official cmd docs :contentReference[oaicite:1]{index=1}

# FastAPI TestClient tutorial :contentReference[oaicite:2]{index=2}

# Postgres JSONB usage example :contentReference[oaicite:3]{index=3}

# Browserbase MCP image info :contentReference[oaicite:4]{index=4}

# Fetch MCP image info :contentReference[oaicite:5]{index=5}

# Tauri python side-car example :contentReference[oaicite:6]{index=6}

# Tauri spawn discussion :contentReference[oaicite:7]{index=7}

# Docker secrets/env_file pattern :contentReference[oaicite:8]{index=8}

# GitHub Action build-and-push reference :contentReference[oaicite:9]{index=9}
