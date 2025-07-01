# Task 04: Stabilize the Development Environment

## Goal

The primary objective of this task is to diagnose and resolve the critical issues that are currently blocking all development and verification work. This task will focus on identifying the root causes of the problems with the test suite, database connectivity, and container environment.

## Core Requirements

### 1. Investigate and Fix the Test Suite

* **Problem:** The `pytest` command fails with `ModuleNotFoundError` for both the `app` module and the `fakeredis` dependency.
* **Action:**
  * Determine why the Python `PYTHONPATH` is not correctly configured in the test environment, preventing the `app` module from being found.
  * Verify that `fakeredis` and all other test-specific dependencies are correctly listed in `pyproject.toml` and installed in the development environment.
  * Run the test suite and ensure all existing tests pass.

### 2. Resolve Database Connectivity and Initialization Issues

* **Problem:** The `psql` command fails with a `FATAL: role "boardroom_user" does not exist` error. This indicates that the database initialization script is not being run correctly or is failing.
* **Action:**
  * Review the `docker-entrypoint.sh` script and the `init-db.py` script to understand how the database is initialized.
  * Investigate why the `boardroom_user` is not being created.
  * Ensure the database is correctly initialized on the first run of the `docker compose up` command.
  * Successfully connect to the database using the `boardroom_user` credentials.

### 3. Stabilize the Containerized Environment

* **Problem:** The `alembic` command cannot be executed within the `api` container due to `PATH` and shell execution issues.
* **Action:**
  * Determine the correct way to execute commands within the container's virtual environment.
  * Ensure that the `alembic` command can be run successfully to manage database migrations.
  * Document the correct procedure for running `alembic` and other commands within the containers.

### 4. Update Documentation

* **Action:**
  * Once the environment is stable, update `VIBE_Docs/Checkpoints/Checkpoint_1.md` with the corrected information for the "Database & Migrations" and "Tests & CI" sections.
  * The `README.md` and a new `ARCHITECTURE.md` should be updated as per the recommendations in `Checkpoint_1.md`.

## Acceptance Criteria

* `pytest -q` runs successfully with all tests passing.
* `docker compose exec db psql -U boardroom_user -d boardroom_db -c "\q"` connects successfully.
* `docker compose exec api /app/.venv/bin/alembic current` (or the corrected command) executes successfully and shows the current migration revision.
* `VIBE_Docs/Checkpoints/Checkpoint_1.md` is updated with the correct, verified information.
