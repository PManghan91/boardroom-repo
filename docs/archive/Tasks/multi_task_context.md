# Task: Get api-1 and worker-1 containers running cleanly

This multi-task job aims to resolve two separate issues preventing the `api-1` and `worker-1` containers from running correctly.

## Issue 1: `api-1` container fails to find `uvicorn`

- **File to modify:** `scripts/docker-entrypoint.sh`
- **Change required:** Add `source /app/.venv/bin/activate` before the `exec` line.
- **Status:** Done

## Issue 2: `worker-1` container fails with `ModuleNotFoundError: No module named 'redis'`

- **File to modify:** `pyproject.toml`
- **Change required:** Add `redis = "^5.0.1"` to the `[project.dependencies]` section.
- **Status:** Done

## Verification

- **Commands:**
  - `docker compose down -v`
  - `docker compose build --no-cache`
  - `docker compose up`
- **Checks:**
  - `api-1` serves `GET /docs` on `localhost:8000`.
  - `worker-1` runs without `ModuleNotFoundError`.
- **Status:** Done
