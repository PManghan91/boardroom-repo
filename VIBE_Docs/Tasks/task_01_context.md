# Task 01: Containerize the Runtime Stack

## Goal

The primary objective is to containerize the entire application stack using Docker Compose, providing a single-click bootstrap method for local development.

## Core Requirements

- **`docker-compose.yml`**: Define the full service stack (`api`, `redis`, `db`, `browserbase`, `fetch`).
- **`.env.example`**: Provide a template for required environment variables.
- **Bootstrap Scripts**: Create `boardroom` (Unix) and `boardroom.cmd` (Windows) to start the stack.
- **Redis Worker**: Implement a `worker.py` to consume messages from a Redis Stream.
- **Tauri Integration**: Wire up the Tauri desktop wrapper to the FastAPI backend.
- **Verification**: Ensure all services run correctly and communicate as expected.
- **Pull Request**: Submit all new files in a single PR from the `feat/compose-stack` branch.

## Key Technologies

- Docker & Docker Compose
- Python (FastAPI)
- Redis (Streams)
- PostgreSQL
- Tauri
- PNPM

## Reference Repository

- `PManghan91/boardroom-repo`
